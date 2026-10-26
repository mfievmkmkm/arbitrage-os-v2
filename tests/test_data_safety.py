import asyncio
import time
from dataclasses import replace

import pytest
from tests_support import instrument, market

from apps.scanner.service import Scanner
from core.evaluator import evaluate, evaluate_sizes
from core.models import D, Reason


def fixture():
    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    return a, b, qa, qb, ba, bb, f, f


@pytest.mark.parametrize(
    "kind,code",
    [
        ("empty", Reason.EMPTY),
        ("crossed", Reason.CROSSED),
        ("zero", Reason.INVALID_BOOK),
        ("unsorted", Reason.INVALID_BOOK),
        ("duplicate", Reason.INVALID_BOOK),
    ],
)
def test_bad_books_never_verified(kind, code):
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    if kind == "empty":
        ba.asks = []
    if kind == "crossed":
        ba.bids = [(D(200), D(10))]
    if kind == "zero":
        ba.asks = [(D(100), D(0))]
    if kind == "unsorted":
        ba.asks = [(D(102), D(10)), (D(101), D(10))]
    if kind == "duplicate":
        ba.asks = [(D(100), D(10)), (D(100), D(2))]
    s = evaluate(a, b, qa, qb, ba, bb, fa, fb, Scanner().cfg)
    assert s.stage == "BLOCKED" and code in s.rejection_codes
    assert s.immediate_round_trip_net_usd is None


def test_three_sizes_are_evaluated_independently():
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    bb.bids = [(D(105), D("1.5"))]
    s = evaluate_sizes(a, b, qa, qb, ba, bb, fa, fb, Scanner().cfg)
    assert {r["size_usd"] for r in s.size_checks} == {50, 100, 250}
    assert next(r for r in s.size_checks if r["size_usd"] == 250)["stage"] == "BLOCKED"
    assert next(r for r in s.size_checks if r["size_usd"] == 50)["stage"] == "VERIFIED"


def test_signal_cannot_outlive_quote_ttl():
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    qa.source_ms -= 1500
    cfg = Scanner().cfg
    s = evaluate(a, b, qa, qb, ba, bb, fa, fb, cfg)
    assert s.expires_at_ms <= qa.source_ms + int(cfg.quote_ttl * 1000)


def test_timestamp_skew_between_books_is_not_an_opportunity():
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    ba.source_ms -= 1500
    s = evaluate(a, b, qa, qb, ba, bb, fa, fb, Scanner().cfg)
    assert Reason.BOOK_SKEW in s.rejection_codes


@pytest.mark.asyncio
async def test_disconnect_revokes_verified_immediately():
    scanner = Scanner()
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    s = evaluate(a, b, qa, qb, ba, bb, fa, fb, scanner.cfg)
    assert s.stage == "VERIFIED"
    scanner.signals[s.id] = s
    await scanner.emit("bybit", "*", None, None, None, time.monotonic(), invalidate=[a.symbol])
    assert s.stage == "BLOCKED" and Reason.OUTAGE in s.rejection_codes
    assert scanner.status()["verified_current"] == 0
    assert scanner.journal.recent[-1]["stage"] == "BLOCKED"


@pytest.mark.asyncio
async def test_empty_quote_clears_previous_valid_state_and_drains_queue():
    scanner = Scanner()
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    scanner.instruments = {a.key: a}
    scanner.quotes[a.key] = qa
    await scanner.emit(*a.key, replace(qa, bid_qty=D(0)), None, None, time.monotonic())
    task = asyncio.create_task(scanner.consume())
    try:
        await asyncio.wait_for(scanner.queue.join(), 1)
        assert a.key not in scanner.quotes
        assert scanner.metrics["invalid_quotes"] == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_bybit_ticker_delta_refreshes_only_actual_top_of_book():
    from adapters.cex.public import BybitParser

    parser = BybitParser()
    parser.parse(
        {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "ts": 1000,
            "data": {
                "symbol": "BTCUSDT",
                "bid1Price": "100",
                "ask1Price": "101",
                "bid1Size": "2",
                "ask1Size": "2",
            },
        }
    )
    _, q, _ = parser.parse(
        {
            "topic": "tickers.BTCUSDT",
            "type": "delta",
            "ts": 2000,
            "data": {"symbol": "BTCUSDT", "bid1Size": "3"},
        }
    )
    assert q.bid_qty == 3 and q.ask == 101 and q.source_ms == 2000
    _, q, _ = parser.parse(
        {
            "topic": "tickers.BTCUSDT",
            "type": "delta",
            "ts": 3000,
            "data": {"symbol": "BTCUSDT", "markPrice": "100.5"},
        }
    )
    assert q is None


def test_bybit_matching_engine_time_and_cross_sequence():
    from adapters.cex.public import IncrementalBook

    parser = IncrementalBook("bybit")
    b = parser.apply(
        {
            "type": "snapshot",
            "ts": 1000,
            "cts": 990,
            "data": {"u": 100, "seq": 1000, "b": [["100", "1"]], "a": [["101", "1"]]},
        }
    )
    assert b.source_ms == 990 and b.sequence == 100 and b.cross_sequence == 1000
    b = parser.apply(
        {"type": "delta", "ts": 1010, "cts": 1005, "data": {"u": 105, "seq": 900, "b": [], "a": []}}
    )
    assert not b.valid


def test_large_depth_does_not_hide_unacceptable_price_impact():
    a, b, qa, qb, ba, bb, fa, fb = fixture()
    ba.asks = [(D(100), D(".01")), (D(102), D(100))]
    s = evaluate(a, b, qa, qb, ba, bb, fa, fb, Scanner().cfg)
    assert s.stage == "BLOCKED" and Reason.SLIPPAGE in s.rejection_codes
    assert D(s.max_symmetric_qty_base) == D(".01")
    assert s.max_executable_notional_usd is not None


@pytest.mark.asyncio
async def test_clock_estimate_excludes_wait_for_shared_rate_limiter(monkeypatch):
    scanner = Scanner()

    class HTTP:
        request_timings = {}

        async def get(self, path):
            self.request_timings[path] = {"sent_ms": 1000, "received_ms": 1100}
            return {"time": 1050, "data": {"serverTime": 1050}}

    scanner.http = {venue: HTTP() for venue in scanner.cfg.venues}

    async def end_iteration(seconds):
        scanner.stop.set()

    monkeypatch.setattr("apps.scanner.service.asyncio.sleep", end_iteration)
    await scanner.clock_loop()
    assert scanner.health["bingx"]["clock"]["offset_ms"] == 0
    assert scanner.health["bingx"]["clock"]["rtt_ms"] == 100
    assert scanner.health["bingx"]["clock"]["usable_for_freshness"]
