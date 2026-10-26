import asyncio
import gzip
import json
import time
from collections import Counter
from dataclasses import asdict

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer
from tests_support import instrument, market

from adapters.cex import public
from apps.scanner.main import api
from apps.scanner.service import Scanner
from core.models import D


@pytest.mark.asyncio
async def test_real_http_and_gzip_websocket_boundary(monkeypatch):
    received = []

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        subscription = await ws.receive_json()
        received.append(subscription)
        await ws.send_bytes(gzip.compress(b"Ping"))
        pong = await ws.receive_str()
        assert pong == "Pong"
        await ws.send_bytes(
            gzip.compress(
                json.dumps(
                    {
                        "code": 0,
                        "dataType": "BTC-USDT@bookTicker",
                        "data": {
                            "s": "BTC-USDT",
                            "b": "100",
                            "a": "101",
                            "B": "2",
                            "A": "3",
                            "T": int(time.time() * 1000),
                        },
                    }
                ).encode()
            )
        )
        await ws.receive()
        return ws

    app = web.Application()
    app.router.add_get("/ws", ws_handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.WS, "bingx", str(server.make_url("/ws")).replace("http:", "ws:"))
        stop, health, metrics, events = asyncio.Event(), {}, Counter(), []

        async def emit(v, symbol, q, f, book, received, **kw):
            if q:
                events.append(q)
                stop.set()

        await asyncio.wait_for(public.stream(session, "bingx", ["BTC-USDT"], emit, health, metrics, stop), 3)
        assert events[0].bid == D(100) and metrics["ping_pong"] == 1
        assert received[0]["dataType"] == "BTC-USDT@bookTicker"


@pytest.mark.asyncio
async def test_depth50_snapshot_protocol(monkeypatch):
    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        subscription = await ws.receive_json()
        assert subscription["dataType"] == "BTC-USDT@depth50@500ms"
        await ws.send_bytes(
            gzip.compress(
                json.dumps(
                    {
                        "code": 0,
                        "dataType": subscription["dataType"],
                        "ts": int(time.time() * 1000),
                        "data": {"bids": [["100", "2"]], "asks": [["101", "3"]]},
                    }
                ).encode()
            )
        )
        await ws.receive()
        return ws

    app = web.Application()
    app.router.add_get("/ws", ws_handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.WS, "bingx", str(server.make_url("/ws")).replace("http:", "ws:"))
        stop, events = asyncio.Event(), []

        async def emit(v, symbol, q, f, book, received, **kw):
            if book:
                events.append(book)
                stop.set()

        await asyncio.wait_for(
            public.stream(session, "bingx", ["BTC-USDT"], emit, {}, Counter(), stop, depth=True), 3
        )
        assert events[0].bids == [(D(100), D(2))]


@pytest.mark.asyncio
async def test_non_json_200_never_means_empty_universe(monkeypatch):
    app = web.Application()

    async def handler(request):
        return web.Response(text="<html>Site Unavailable</html>")

    app.router.add_get("/v5/market/instruments-info", handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.REST, "bybit", str(server.make_url("")).rstrip("/"))
        http = public.PublicHTTP(session, "bybit", Counter())
        with pytest.raises(public.ProviderError, match="NON_JSON"):
            await public.catalog(http)


@pytest.mark.asyncio
async def test_api_modes_expiration_and_auth(monkeypatch):
    scanner = Scanner()
    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    scanner.instruments = {a.key: a, b.key: b}
    scanner.quotes = {a.key: qa, b.key: qb}
    from core.evaluator import evaluate

    s = evaluate(a, b, qa, qb, ba, bb, f, f, scanner.cfg)
    scanner.signals[s.id] = s
    async with TestClient(TestServer(api(scanner))) as client:
        assert (await (await client.get("/health")).json())["mode"] == "OBSERVE"
        status = await (await client.get("/status")).json()
        assert status["active_venues"] == ["bybit", "bingx"]
        assert status["executable"] == status["paper_opened"] == 0
        assert len(await (await client.get("/markets")).json()) == 2
        assert len(await (await client.get("/quotes")).json()) == 2
        assert len(await (await client.get("/signals")).json()) == 1
        s.expires_at_ms = 0
        assert await (await client.get("/signals")).json() == []
        assert (await client.patch("/settings", json={"size": "1"})).status == 403
        monkeypatch.setenv("CONTROL_TOKEN", "test-only")
        headers = {"Authorization": "Bearer test-only"}
        assert (await client.patch("/settings", json={"mode": "LIVE"}, headers=headers)).status == 400
        assert (await client.patch("/settings", json={"size": "NaN"}, headers=headers)).status == 400
        assert (await client.patch("/settings", json={"size": "12"}, headers=headers)).status == 503
        assert "arbitrage_fresh_quotes" in await (await client.get("/metrics")).text()


@pytest.mark.asyncio
async def test_delayed_queued_event_cannot_revive_disconnected_feed():
    scanner = Scanner()
    a = instrument()
    scanner.instruments[a.key] = a
    qa, *_ = market()
    await scanner.emit(*a.key, qa, None, None, time.monotonic())
    await scanner.emit("bybit", "*", None, None, None, time.monotonic(), invalidate=["BTCUSDT"])
    consumer = asyncio.create_task(scanner.consume())
    await asyncio.sleep(0.01)
    assert not scanner.quotes
    assert scanner.metrics["discarded_pre_disconnect_events"] == 1
    consumer.cancel()
    await asyncio.gather(consumer, return_exceptions=True)


@pytest.mark.asyncio
async def test_429_is_counted_and_not_treated_as_catalog(monkeypatch):
    async def handler(request):
        return web.Response(status=429, headers={"Retry-After": "1"})

    app = web.Application()
    app.router.add_get("/v5/market/instruments-info", handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.REST, "bybit", str(server.make_url("")).rstrip("/"))
        metrics = Counter()
        http = public.PublicHTTP(session, "bybit", metrics)
        with pytest.raises(public.ProviderError, match="HTTP_429"):
            await http.get("/v5/market/instruments-info")
        assert metrics["http_429"] == 1


@pytest.mark.asyncio
async def test_catalog_outage_does_not_erase_other_venue(monkeypatch):
    scanner = Scanner()
    a, b = instrument(), instrument("bingx")
    scanner.instruments = {a.key: a, b.key: b}
    scanner.http["bybit"] = object()

    async def broken(http):
        raise public.ProviderError("OUTAGE")

    monkeypatch.setattr("apps.scanner.service.catalog", broken)
    await scanner.refresh_venue("bybit")
    assert scanner.instruments[b.key] == b
    assert scanner.health["bybit"]["status"] == "UNAVAILABLE"


def test_telegram_russian_observe_and_rejection():
    from apps.telegram_bot.main import keyboard, render
    from core.evaluator import evaluate

    scanner = Scanner()
    a, b = instrument(asset_id=None), instrument("bingx")
    qa, qb, ba, bb, f = market()
    signal = evaluate(a, b, qa, qb, ba, bb, f, f, scanner.cfg)
    text = render("raw", scanner.status(), [asdict(signal)])
    assert "Не подтверждено" in text
    assert "LONG bybit" in text
    assert "Назад" in str(keyboard(True))
    assert "LIVE OFF" in render("home", scanner.status())


@pytest.mark.asyncio
async def test_funding_interval_cold_start_uses_evidence(monkeypatch):
    scanner = Scanner()
    scanner.depth_tasks[("bingx", "BTC-USDT")] = None

    class HTTP:
        async def get(self, path, params):
            return {"data": [{"fundingTime": t} for t in (30000, 20000, 10000)]}

    scanner.http["bingx"] = HTTP()

    async def end_iteration(seconds):
        scanner.stop.set()

    monkeypatch.setattr("apps.scanner.service.asyncio.sleep", end_iteration)
    await scanner.funding_interval_loop()
    assert scanner.funding_intervals_bingx["BTC-USDT"] == 10000


@pytest.mark.asyncio
async def test_websocket_disconnect_resubscribes_and_resets(monkeypatch):
    calls = []

    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        calls.append(await ws.receive_json())
        await ws.send_bytes(
            gzip.compress(
                json.dumps(
                    {
                        "code": 0,
                        "dataType": "BTC-USDT@bookTicker",
                        "data": {
                            "s": "BTC-USDT",
                            "b": "100",
                            "a": "101",
                            "B": "1",
                            "A": "2",
                            "T": int(time.time() * 1000),
                        },
                    }
                ).encode()
            )
        )
        if len(calls) == 1:
            await ws.close()
        else:
            await ws.receive()
        return ws

    app = web.Application()
    app.router.add_get("/ws", handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.WS, "bingx", str(server.make_url("/ws")).replace("http:", "ws:"))
        monkeypatch.setattr(public.random, "random", lambda: 0)
        stop, events, metrics = asyncio.Event(), [], Counter()

        async def emit(v, s, q, f, book, received, **kw):
            if q:
                events.append("quote")
                if events.count("quote") == 2:
                    stop.set()
            if kw.get("invalidate"):
                events.append("invalidated")

        await asyncio.wait_for(public.stream(session, "bingx", ["BTC-USDT"], emit, {}, metrics, stop), 5)
        assert len(calls) == 2 and calls[0]["dataType"] == calls[1]["dataType"]
        assert events[:3] == ["quote", "invalidated", "quote"]
        assert metrics["ws_reconnects"] >= 1
