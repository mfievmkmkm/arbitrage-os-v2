import asyncio
import os
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict

from adapters.cex.public import PublicHTTP, catalog, stream
from core.config import Config
from core.evaluator import evaluate_sizes, fresh
from core.identity import compatible, identify, load_registry
from core.models import D, Funding, Reason
from infrastructure.journal import Journal


def memory_rss():
    try:
        from pathlib import Path

        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return None


def percentile(items, pct):
    if not items:
        return None
    x = sorted(items)
    return x[min(len(x) - 1, int((len(x) - 1) * pct))]


class Scanner:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config.env()
        self.stop = asyncio.Event()
        self.instruments, self.quotes, self.books, self.funding = {}, {}, {}, {}
        self.invalid_before = {}
        self.funding_intervals_bingx = {}
        self.funding_intervals_checked = {}
        self.by_base = defaultdict(list)
        self.by_asset = defaultdict(list)
        self.signals = {}
        self.metrics = Counter()
        self.latencies = deque(maxlen=20000)
        self.detection_latencies = deque(maxlen=20000)
        self.started_cpu = time.process_time()
        self.queue_lags = deque(maxlen=20000)
        self.rejections = Counter()
        self.health = {
            v: {"status": "NOT_CONNECTED", "discovered": 0, "active": 0, "connections": 0, "exclusions": {}}
            for v in self.cfg.venues
        }
        self.queue = asyncio.Queue(self.cfg.queue_size)
        self.registry = load_registry()
        self.journal = Journal(os.getenv("DATABASE_URL"))
        self.http = {}
        self.tasks = []
        self.feed_tasks = {}
        self.depth_tasks = {}
        self.intervals = {}
        self.last_journal = {}
        self.started = time.time()

    def revoke(self, venue, symbols, reason):
        symbols = set(symbols)
        now_ms = int(time.time() * 1000)
        for s in self.signals.values():
            if (s.cheap == venue and s.long_symbol in symbols) or (
                s.expensive == venue and s.short_symbol in symbols
            ):
                s.stage = "BLOCKED"
                s.expires_at_ms = min(s.expires_at_ms, now_ms)
                if reason not in s.rejection_codes:
                    s.rejection_codes.append(reason)
                    self.rejections[reason] += 1
                    self.journal.append(asdict(s))

    async def emit(self, venue, symbol, quote, funding, book, received, invalidate=None, depth=False):
        if invalidate:
            for s in invalidate:
                (self.books if depth else self.quotes).pop((venue, s), None)
                self.invalid_before[(venue, s, depth)] = received
            self.revoke(venue, invalidate, Reason.OUTAGE)
            return
        try:
            self.queue.put_nowait((venue, symbol, quote, funding, book, received))
        except asyncio.QueueFull:
            self.metrics["dropped_events"] += 1
            # A dropped delta must not leave a supposedly current book in circulation.
            self.books.pop((venue, symbol), None)
            self.quotes.pop((venue, symbol), None)
            self.invalid_before[(venue, symbol, False)] = received
            self.invalid_before[(venue, symbol, True)] = received
            self.revoke(venue, [symbol], Reason.OUTAGE)

    async def consume(self):
        while not self.stop.is_set():
            try:
                venue, symbol, q, f, book, received = await asyncio.wait_for(self.queue.get(), 1)
            except TimeoutError:
                continue
            key = venue, symbol
            instrument = self.instruments.get(key)
            if not instrument:
                self.queue.task_done()
                continue
            if received <= self.invalid_before.get((venue, symbol, book is not None), 0):
                self.metrics["discarded_pre_disconnect_events"] += 1
                self.queue.task_done()
                continue
            if q and not q.valid():
                self.metrics["invalid_quotes"] += 1
                self.quotes.pop(key, None)
                self.revoke(venue, [symbol], Reason.STALE)
                self.queue.task_done()
                continue
            if q and q.valid():
                old = self.quotes.get(key)
                if old is None or q.source_ms >= old.source_ms:
                    self.quotes[key] = q
                    self.metrics["quote_events"] += 1
                else:
                    self.metrics["out_of_order_quotes"] += 1
                    self.queue.task_done()
                    continue
            if f:
                self.funding[key] = f
            if book:
                self.books[key] = book
            self.queue.task_done()
            self.queue_lags.append((time.monotonic() - received) * 1000)
            compared = False
            related = {x.key: x for x in self.by_base[instrument.base]}
            if instrument.asset_id:
                related.update({x.key: x for x in self.by_asset[instrument.asset_id]})
            for other in related.values():
                if other.venue == venue:
                    continue
                if key not in self.quotes or other.key not in self.quotes:
                    continue
                for a, b in ((instrument, other), (other, instrument)):
                    qa, qb = self.quotes[a.key], self.quotes[b.key]
                    self.metrics["pair_comparisons"] += 1
                    compared = True
                    raw = (qb.bid / qa.ask - 1) * 100
                    sid = f"A1:{a.venue}:{a.symbol}:{b.venue}:{b.symbol}"
                    if raw < self.cfg.min_spread_pct:
                        if sid in self.signals:
                            old_signal = self.signals.pop(sid)
                            old_signal.stage = "EXPIRED"
                            self.journal.append(asdict(old_signal))
                            self.last_journal.pop(sid, None)
                        continue
                    s = evaluate_sizes(
                        a,
                        b,
                        qa,
                        qb,
                        self.books.get(a.key),
                        self.books.get(b.key),
                        self.funding.get(a.key),
                        self.funding.get(b.key),
                        self.cfg,
                    )
                    prior = self.signals.get(s.id)
                    s.first_seen_at_ms = prior.first_seen_at_ms if prior else s.observed_at_ms
                    s.peak_spread_pct = max(
                        prior.peak_spread_pct if prior else s.raw_spread_pct, s.raw_spread_pct
                    )
                    self.signals[s.id] = s
                    self.metrics["candidate_updates"] += 1
                    if prior is None:
                        self.metrics["raw_discoveries"] += 1
                    if s.stage == "VERIFIED":
                        self.metrics["verified_updates"] += 1
                    fingerprint = (s.stage, tuple(s.rejection_codes))
                    previous = self.last_journal.get(s.id)
                    if previous is None or previous[0] != fingerprint or time.monotonic() - previous[1] > 10:
                        self.rejections.update(s.rejection_codes)
                        self.journal.append(asdict(s))
                        self.last_journal[s.id] = fingerprint, time.monotonic()
            elapsed = (time.monotonic() - received) * 1000
            self.latencies.append(elapsed)
            if compared:
                self.detection_latencies.append(elapsed)

    async def refresh_venue(self, venue):
        h = self.health[venue]
        try:
            rows, excluded, native = await catalog(self.http[venue])
            keys = {x.key for x in rows}
            for key in [k for k in self.instruments if k[0] == venue]:
                self.instruments.pop(key)
                if key not in keys:
                    self.quotes.pop(key, None)
                    self.books.pop(key, None)
                    self.funding.pop(key, None)
            for x in rows:
                self.instruments[x.key] = identify(x, self.registry)
            self.by_base.clear()
            self.by_asset.clear()
            for x in self.instruments.values():
                self.by_base[x.base].append(x)
                if x.asset_id:
                    self.by_asset[x.asset_id].append(x)
            if venue == "bybit":
                self.intervals = {r["symbol"]: int(r.get("fundingInterval", 0)) * 60000 for r in native}
            h.update(
                status="CATALOG_READY",
                discovered=len(native),
                active=len(rows),
                exclusions=dict(excluded),
                catalog_at_ms=int(time.time() * 1000),
            )
            previous_symbols = self.feed_tasks.get(venue, ([], []))[0]
            symbols = sorted(x.symbol for x in rows)
            if symbols != previous_symbols:
                old_tasks = self.feed_tasks.get(venue, ([], []))[1]
                for t in old_tasks:
                    t.cancel()
                await asyncio.gather(*old_tasks, return_exceptions=True)
                tasks = []
                for i in range(0, len(symbols), self.cfg.shard_size):
                    tasks.append(
                        asyncio.create_task(
                            stream(
                                self.session,
                                venue,
                                symbols[i : i + self.cfg.shard_size],
                                self.emit,
                                h,
                                self.metrics,
                                self.stop,
                                intervals=self.intervals,
                            )
                        )
                    )
                    await asyncio.sleep(0.2)
                self.feed_tasks[venue] = symbols, tasks
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            h.update(status="UNAVAILABLE", last_error=type(exc).__name__ + ":" + str(exc)[:150])
            h["last_error_code"] = getattr(exc, "code", type(exc).__name__)
            h["last_error_evidence"] = getattr(exc, "evidence", {})
            self.metrics["catalog_errors"] += 1
            self.rejections[h["last_error_code"]] += 1
            self.journal.append(
                {
                    "id": f"INFRA:{venue}:catalog",
                    "asset": venue,
                    "stage": "BLOCKED",
                    "event_type": "PROVIDER_HEALTH",
                    "data_mode": "REAL_LIVE_MARKET_OBSERVE",
                    "observed_at_ms": int(time.time() * 1000),
                    "rejection_codes": [h["last_error_code"]],
                    "evidence": h["last_error_evidence"],
                }
            )

    async def catalogs(self, venue):
        while not self.stop.is_set():
            await self.refresh_venue(venue)
            delay = self.cfg.catalog_interval if self.health[venue]["status"] != "UNAVAILABLE" else 30
            try:
                await asyncio.wait_for(self.stop.wait(), delay)
            except TimeoutError:
                pass

    async def funding_loop(self):
        while not self.stop.is_set():
            if "bingx" in self.http:
                try:
                    data = await self.http["bingx"].get("/openApi/swap/v2/quote/premiumIndex")
                    # Interval must be explicit or evidenced by historical funding settlements.
                    # Do not assume every market settles each eight hours.
                    for r in data["data"]:
                        interval = int(r.get("fundingInterval", 0)) * 3600000
                        interval = interval or (
                            self.funding_intervals_bingx.get(r["symbol"], 0)
                            if time.monotonic() - self.funding_intervals_checked.get(r["symbol"], 0) < 3600
                            else 0
                        )
                        self.funding[("bingx", r["symbol"])] = Funding(
                            D(str(r["lastFundingRate"])), int(r["nextFundingTime"]), interval
                        )
                except Exception:
                    self.metrics["funding_errors"] += 1
            await asyncio.sleep(30)

    async def clock_loop(self):
        async def sample(venue):
            before = time.time() * 1000
            started = time.monotonic()
            try:
                path = "/v5/market/time" if venue == "bybit" else "/openApi/swap/v2/server/time"
                data = await self.http[venue].get(path)
                timing = self.http[venue].request_timings.get(path)
                if timing:
                    before = timing["sent_ms"]
                server_ms = int(data["time"]) if venue == "bybit" else int(data["data"]["serverTime"])
                after = time.time() * 1000
                if timing:
                    after = timing["received_ms"]
                self.health[venue]["clock"] = {
                    "offset_ms": server_ms - (before + after) / 2,
                    "rtt_ms": after - before,
                    "request_including_rate_limit_ms": (time.monotonic() - started) * 1000,
                    "uncertainty_ms": (after - before) / 2,
                    "usable_for_freshness": (after - before) <= 500,
                    "sampled_at_ms": int(after),
                    "policy": "DIAGNOSTIC_ONLY_NO_SILENT_TIMESTAMP_REWRITE",
                }
            except Exception as exc:
                self.health[venue]["clock"] = {
                    "offset_ms": None,
                    "error_code": getattr(exc, "code", type(exc).__name__),
                }
                self.metrics["clock_errors"] += 1

        while not self.stop.is_set():
            await asyncio.gather(*(sample(v) for v in self.cfg.venues))
            await asyncio.sleep(60)

    async def funding_interval_loop(self):
        while not self.stop.is_set():
            symbols = {symbol for venue, symbol in self.depth_tasks if venue == "bingx"}
            for symbol in symbols:
                if (
                    symbol in self.funding_intervals_checked
                    and time.monotonic() - self.funding_intervals_checked[symbol] < 3600
                ):
                    continue
                try:
                    response = await self.http["bingx"].get(
                        "/openApi/swap/v2/quote/fundingRate", {"symbol": symbol, "limit": 3}
                    )
                    times = sorted({int(r["fundingTime"]) for r in response["data"]}, reverse=True)
                    if len(times) >= 3 and times[0] - times[1] == times[1] - times[2] > 0:
                        self.funding_intervals_bingx[symbol] = times[0] - times[1]
                        self.funding_intervals_checked[symbol] = time.monotonic()
                        self.metrics["funding_intervals_observed"] += 1
                except Exception:
                    self.metrics["funding_interval_errors"] += 1
            await asyncio.sleep(60)

    async def depth_loop(self):
        while not self.stop.is_set():
            now_ms = int(time.time() * 1000)
            ranked = sorted(
                (s for s in self.signals.values() if s.expires_at_ms > now_ms),
                key=lambda s: s.raw_spread_pct,
                reverse=True,
            )[: self.cfg.shortlist]
            wanted = set()
            for s in ranked:
                for x in self.instruments.values():
                    if x.base == s.asset or x.asset_id == s.asset:
                        if x.venue in (s.cheap, s.expensive):
                            wanted.add(x.key)
            for key in set(self.depth_tasks) - wanted:
                self.depth_tasks[key].cancel()
                await asyncio.gather(self.depth_tasks.pop(key), return_exceptions=True)
                self.books.pop(key, None)
            for venue, symbol in wanted - set(self.depth_tasks):
                self.depth_tasks[(venue, symbol)] = asyncio.create_task(
                    stream(
                        self.session,
                        venue,
                        [symbol],
                        self.emit,
                        self.health[venue],
                        self.metrics,
                        self.stop,
                        depth=True,
                    )
                )
            for sid, s in list(self.signals.items()):
                if s.expires_at_ms <= now_ms:
                    s.stage = "EXPIRED"
                    self.journal.append(asdict(s))
                    del self.signals[sid]
                    self.last_journal.pop(sid, None)
            await asyncio.sleep(3)

    def status(self):
        now, now_ms = time.monotonic(), int(time.time() * 1000)
        coverage = {}
        for v, h in self.health.items():
            instruments = [x for x in self.instruments.values() if x.venue == v]
            count = sum(
                k[0] == v and fresh(q.source_ms, q.received, self.cfg, now_ms, now)
                for k, q in self.quotes.items()
            )
            identified = sum(x.asset_id is not None for x in instruments)
            counterpart = sum(any(y.venue != v for y in self.by_base[x.base]) for x in instruments)
            state = "PUBLIC_READY" if count else ("DEGRADED" if h["connections"] else h["status"])
            ages = [
                max(now_ms - q.source_ms, (now - q.received) * 1000)
                for k, q in self.quotes.items()
                if k[0] == v
            ]
            coverage[v] = {
                **h,
                "quote_age_p95_ms": percentile(ages, 0.95),
                "status": state,
                "identified": identified,
                "fresh_quotes": count,
                "received_quotes": sum(k[0] == v for k in self.quotes),
                "symbol_counterparts_unverified": counterpart,
                "no_counterpart": len(instruments) - counterpart,
                "depth_books": sum(
                    k[0] == v and b.valid and fresh(b.source_ms, b.received, self.cfg, now_ms, now)
                    for k, b in self.books.items()
                ),
            }
        current = [s for s in self.signals.values() if s.expires_at_ms > now_ms]
        pair_keys = set()
        for a in self.instruments.values():
            if not a.asset_id:
                continue
            for b in self.by_asset[a.asset_id]:
                if compatible(a, b):
                    pair_keys.add(tuple(sorted((a.key, b.key))))
        return {
            "requirements_version": "1.3",
            "data_mode": "REAL_LIVE_MARKET_OBSERVE",
            "compatible_pairs": len(pair_keys),
            "compatible_directed_routes": len(pair_keys) * 2,
            "outbound_public_requests": {
                v: dict(h.request_paths) for v, h in self.http.items() if hasattr(h, "request_paths")
            },
            "mode": "OBSERVE",
            "live_enabled": False,
            "active_venues": list(self.cfg.venues),
            "uptime_seconds": round(time.time() - self.started),
            "coverage": coverage,
            "dex_pools": 0,
            "raw_current": len(current),
            "verified_current": sum(s.stage == "VERIFIED" for s in current),
            "executable": 0,
            "paper_opened": 0,
            "paper_closed": 0,
            "event_processing_latency_ms": {
                "p50": percentile(self.latencies, 0.5),
                "p95": percentile(self.latencies, 0.95),
                "samples": len(self.latencies),
                "meaning": "WS receive to event processed (not necessarily a comparison)",
            },
            "latency_ms": {
                "p50": percentile(self.detection_latencies, 0.5),
                "p95": percentile(self.detection_latencies, 0.95),
                "samples": len(self.detection_latencies),
                "meaning": "WS receive to related route comparisons complete",
            },
            "process_cpu_seconds": time.process_time() - self.started_cpu,
            "rss_bytes": memory_rss(),
            "queue_lag_p95_ms": percentile(self.queue_lags, 0.95),
            "queue_depth": self.queue.qsize(),
            "metrics": dict(self.metrics),
            "rejections_journal_events": dict(self.rejections),
            "journal": {
                "durable": bool(self.journal.pool),
                "written": self.journal.written,
                "persisted": self.journal.written if self.journal.pool else 0,
                "dropped": self.journal.dropped,
                "failures": self.journal.failures,
                "pending": self.journal.queue.qsize(),
            },
            "readiness": "OBSERVATION_ONLY"
            if len(coverage) == 2 and all(coverage[v]["fresh_quotes"] for v in coverage)
            else "DEGRADED_NO_TWO_VENUE_COMPARISON",
        }

    async def start(self, session):
        self.session = session
        await self.journal.connect()
        if self.journal.pool:
            async with self.journal.pool.acquire() as conn:
                settings = await conn.fetch("SELECT key,value FROM scanner_settings")
            allowed = {
                "size",
                "min_spread_pct",
                "min_net",
                "target_basis_pct",
                "slippage_reserve",
                "max_slippage_bps",
            }
            updates = {
                r["key"]: D(__import__("json").loads(r["value"])) for r in settings if r["key"] in allowed
            }
            self.cfg = Config(**{**asdict(self.cfg), **updates})
        self.http = {v: PublicHTTP(session, v, self.metrics) for v in self.cfg.venues}
        self.journal.append(
            {
                "id": "CONFIG:BOOT",
                "asset": "CONFIG",
                "stage": "OBSERVE",
                "event_type": "ACTIVE_CONFIGURATION",
                "observed_at_ms": int(time.time() * 1000),
                "requirements_version": "1.3",
                "configuration": asdict(self.cfg),
                "rejection_codes": [],
            }
        )
        self.tasks = [
            asyncio.create_task(self.consume()),
            asyncio.create_task(self.depth_loop()),
            asyncio.create_task(self.funding_loop()),
            asyncio.create_task(self.journal.run(self.stop)),
        ]
        self.tasks.append(asyncio.create_task(self.funding_interval_loop()))
        self.tasks.append(asyncio.create_task(self.clock_loop()))
        self.tasks += [asyncio.create_task(self.catalogs(v)) for v in self.cfg.venues]

    async def close(self):
        self.stop.set()
        tasks = self.tasks + [t for _, ts in self.feed_tasks.values() for t in ts]
        tasks += list(self.depth_tasks.values())
        # Drain journal after all producers stop.
        journal_task = self.tasks[3] if self.tasks else None
        for t in tasks:
            if t is not journal_task:
                t.cancel()
        await asyncio.gather(*(t for t in tasks if t is not journal_task), return_exceptions=True)
        if journal_task:
            await journal_task
        await self.journal.close()
