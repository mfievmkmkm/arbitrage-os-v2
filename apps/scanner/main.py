import argparse
import asyncio
import json
import os
import signal
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from aiohttp import ClientSession, web

from apps.scanner.service import Scanner
from core.config import Config
from core.reasons import REASONS


def json_safe(value):
    return json.loads(json.dumps(value, default=str))


def api(scanner):
    app = web.Application()

    async def health(request):
        failed = any(t.done() and not t.cancelled() and t.exception() for t in scanner.tasks)
        alive = not scanner.stop.is_set() and not failed
        return web.json_response({"alive": alive, "mode": "OBSERVE"}, status=200 if alive else 503)

    async def ready(request):
        status = scanner.status()
        ok = status["readiness"] == "OBSERVATION_ONLY" and status["journal"]["durable"]
        return web.json_response({"ready": ok, "readiness": status["readiness"]}, status=200 if ok else 503)

    async def status(request):
        return web.json_response(scanner.status())

    async def signals(request):
        stage = request.query.get("stage")
        now = int(time.time() * 1000)
        rows = [
            asdict(s)
            for s in scanner.signals.values()
            if s.expires_at_ms > now and (not stage or s.stage == stage)
        ]
        return web.json_response(sorted(rows, key=lambda x: x["raw_spread_pct"], reverse=True)[:100])

    async def markets(request):
        return web.json_response(json_safe([asdict(x) for x in scanner.instruments.values()]))

    async def quotes(request):
        return web.json_response(
            json_safe([{"venue": v, "symbol": s, **asdict(q)} for (v, s), q in scanner.quotes.items()])
        )

    async def history(request):
        return web.json_response(await scanner.journal.history())

    async def reasons(request):
        return web.json_response(
            {code: {"stage": stage, "explanation_ru": text} for code, (stage, text) in REASONS.items()}
        )

    async def metrics(request):
        s = scanner.status()
        text = [f"arbitrage_{k} {v}" for k, v in scanner.metrics.items()]
        for v, h in s["coverage"].items():
            text.append(f'arbitrage_fresh_quotes{{venue="{v}"}} {h["fresh_quotes"]}')
        if s["latency_ms"]["p95"] is not None:
            text.append(f"arbitrage_detection_p95_ms {s['latency_ms']['p95']}")
        text.append(f"arbitrage_journal_dropped {scanner.journal.dropped}")
        return web.Response(text="\n".join(text) + "\n", content_type="text/plain")

    async def settings(request):
        # Internal API only; optional owner bearer credential for settings mutation.
        token = os.getenv("CONTROL_TOKEN")
        if not token or request.headers.get("Authorization") != "Bearer " + token:
            raise web.HTTPForbidden()
        row = await request.json()
        permitted = {"size", "min_spread_pct", "min_net", "target_basis_pct", "slippage_reserve"}
        if set(row) - permitted:
            raise web.HTTPBadRequest(text="Unsupported settings")
        try:
            cfg = Config(**{**asdict(scanner.cfg), **{k: Decimal(str(v)) for k, v in row.items()}})
        except (ValueError, ArithmeticError, TypeError):
            raise web.HTTPBadRequest(text="Invalid numeric setting") from None
        if not scanner.journal.pool:
            raise web.HTTPServiceUnavailable(text="Durable settings require PostgreSQL")
        async with scanner.journal.pool.acquire() as conn:
            async with conn.transaction():
                for k in permitted:
                    await conn.execute(
                        "INSERT INTO scanner_settings(key,value) VALUES($1,$2) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        k,
                        json.dumps(str(getattr(cfg, k))),
                    )
        scanner.cfg = cfg
        scanner.signals.clear()
        return web.json_response({"saved": True})

    for path, handler in (
        ("/health", health),
        ("/ready", ready),
        ("/status", status),
        ("/signals", signals),
        ("/markets", markets),
        ("/quotes", quotes),
        ("/history", history),
        ("/metrics", metrics),
        ("/reason-codes", reasons),
    ):
        app.router.add_get(path, handler)
    app.router.add_patch("/settings", settings)
    return app


async def run(seconds=None, report=None):
    scanner = Scanner()
    async with ClientSession(trust_env=True) as session:
        await scanner.start(session)
        runner = web.AppRunner(api(scanner))
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", scanner.cfg.port).start()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, scanner.stop.set)
            except (NotImplementedError, RuntimeError):
                pass
        try:
            if seconds:
                try:
                    await asyncio.wait_for(scanner.stop.wait(), seconds)
                except TimeoutError:
                    pass
            else:
                await scanner.stop.wait()
        finally:
            snapshot = scanner.status()
            if report:
                path = Path(report)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        {
                            "status": snapshot,
                            "markets": json_safe([asdict(x) for x in scanner.instruments.values()]),
                            "quotes": json_safe(
                                [
                                    {"venue": k[0], "symbol": k[1], **asdict(v)}
                                    for k, v in scanner.quotes.items()
                                ]
                            ),
                            "signals": [asdict(s) for s in scanner.signals.values()],
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            print(json.dumps(snapshot, ensure_ascii=False, indent=2), flush=True)
            await scanner.close()
            await runner.cleanup()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=int)
    p.add_argument("--report")
    args = p.parse_args()
    asyncio.run(run(args.seconds, args.report))


if __name__ == "__main__":
    main()
