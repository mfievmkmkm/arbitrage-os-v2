import asyncio
import gzip
import time
from dataclasses import replace

import pytest

from adapters.cex.public import BybitParser, IncrementalBook, ProviderError, catalog, decode
from apps.scanner.service import Scanner
from core.config import Config
from core.evaluator import common_step, evaluate, vwap
from core.identity import compatible, identify
from core.models import Book, D, Funding, Instrument, Quote, Reason
from infrastructure.journal import Journal


def instrument(venue="bybit", **kw):
    x = Instrument(
        venue,
        "BTCUSDT" if venue == "bybit" else "BTC-USDT",
        "BTC",
        "USDT",
        "USDT",
        D("0.001"),
        D("0.001"),
        D(1),
        D("0.01"),
        spec_verified=True,
        asset_id="bitcoin",
        identity_proof="fixture-only-proof",
        taker_fee=D("0.0005"),
    )
    return replace(x, **kw)


def market():
    now = int(time.time() * 1000)
    qa = Quote(D("99.9"), D(100), D(10), D(10), now)
    qb = Quote(D(105), D("105.1"), D(10), D(10), now)
    ba = Book([(qa.bid, D(10))], [(qa.ask, D(10))], now)
    bb = Book([(qb.bid, D(10))], [(qb.ask, D(10))], now)
    f = Funding(D("0.0001"), now + 10000, 8 * 3600000)
    return qa, qb, ba, bb, f


def ev(**kwargs):
    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    args = dict(a=a, b=b, qa=qa, qb=qb, ba=ba, bb=bb, fa=f, fb=f, cfg=Config())
    args.update(kwargs)
    return evaluate(**args)


@pytest.mark.parametrize("venue", ["binance", "mexc", "okx", "bitget", "unknown"])
def test_forbidden_venues(venue):
    with pytest.raises(ValueError):
        Config(venues=(venue,))


@pytest.mark.parametrize("mode", ["LIVE_AUTO", "LIVE_MANUAL", "PAPER_AUTO", "PAPER_MANUAL"])
def test_only_observe(mode):
    with pytest.raises(ValueError):
        Config(mode=mode)


@pytest.mark.parametrize("size", ["NaN", "Infinity", "-1", "0", "100001"])
def test_invalid_size(size):
    with pytest.raises(ValueError):
        Config(size=D(size))


def test_round_trip_not_convergence_profit():
    s = ev()
    assert s.stage == "VERIFIED"
    assert D(s.immediate_round_trip_net_usd) < 0
    assert D(s.scenario_net_at_target_basis_usd) > 0
    assert s.route_tradeability == "MODE_OBSERVE"
    assert D(s.opening_fees_usd) > 0 and D(s.estimated_closing_fees_usd) > 0


def test_funding_sign():
    qa, qb, ba, bb, f = market()
    s = ev(fa=replace(f, rate=D("0.1")), fb=replace(f, rate=D(0)))
    assert D(s.funding_expected_usd) < 0
    assert Reason.NET in s.rejection_codes


def test_unknown_identity_cannot_verify():
    s = ev(a=instrument(asset_id=None))
    assert Reason.IDENTITY in s.rejection_codes


def test_same_ticker_different_underlying():
    assert not compatible(instrument(), instrument("bingx", asset_id="fake-bitcoin"))


def test_registry_requires_evidence():
    x = instrument(asset_id=None)
    assert identify(x, [{"asset_id": "bitcoin", "instruments": {}}]).asset_id is None


def test_registry_binding():
    row = {
        "asset_id": "bitcoin",
        "proof": "test evidence",
        "reviewed_at": "2026-10-26",
        "review_status": "REVIEWED",
        "sources": {"bybit": "https://www.bybit.com/evidence", "bingx": "https://bingx.com/evidence"},
        "instruments": {
            "bybit": {"symbol": "BTCUSDT", "base": "BTC", "multiplier": "1"},
            "bingx": {"symbol": "BTC-USDT", "base": "BTC", "multiplier": "1"},
        },
    }
    assert identify(instrument(asset_id=None), [row]).asset_id == "bitcoin"


def test_contract_and_settlement():
    assert not compatible(instrument(), instrument("bingx", settle="USDC"))
    assert not compatible(instrument(), instrument("bingx", spec_verified=False))


def test_common_qty_not_independent_rounding():
    assert common_step(D("0.003"), D("0.005")) == D("0.015")
    s = ev(a=instrument(step=D("0.003")), b=instrument("bingx", step=D("0.005")))
    assert D(s.qty_base) % D("0.015") == 0


def test_vwap_depth():
    assert vwap([(D(10), D(1)), (D(12), D(1))], D(2)) == D(11)
    assert vwap([(D(10), D(1))], D(2)) is None


def test_low_depth():
    _, _, ba, _, _ = market()
    assert Reason.DEPTH in ev(ba=replace(ba, asks=[(D(100), D("0.001"))])).rejection_codes


def test_stale_and_gap():
    qa, _, ba, _, _ = market()
    assert Reason.STALE in ev(qa=replace(qa, source_ms=1)).rejection_codes
    assert Reason.GAP in ev(ba=replace(ba, valid=False)).rejection_codes


def test_future_clock_rejected():
    qa, *_ = market()
    assert Reason.STALE in ev(qa=replace(qa, source_ms=qa.source_ms + 10000)).rejection_codes


def test_unknown_funding_fee():
    assert Reason.FUNDING in ev(fa=None).rejection_codes
    assert Reason.FEES in ev(a=instrument(taker_fee=None)).rejection_codes


def test_minimum_notional():
    assert Reason.MINIMUM in ev(a=instrument(min_notional=D(10000))).rejection_codes


def test_funding_interval_unknown():
    *_, f = market()
    assert Reason.FUNDING in ev(fa=replace(f, interval_ms=0)).rejection_codes


def test_gzip_ping():
    assert decode(gzip.compress(b"Ping")) == "Ping"
    assert decode(gzip.compress(b'{"code":0}')) == {"code": 0}


def test_gzip_oversized():
    with pytest.raises(ProviderError):
        decode(gzip.compress(b"x" * (4 * 1024 * 1024 + 1)))


def test_bybit_delta_merge_without_false_refresh():
    p = BybitParser()
    s, q, _ = p.parse(
        {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "ts": 10,
            "data": {
                "symbol": "BTCUSDT",
                "bid1Price": "1",
                "ask1Price": "2",
                "bid1Size": "3",
                "ask1Size": "4",
            },
        }
    )
    assert q.bid == 1
    _, q, _ = p.parse(
        {"topic": "tickers.BTCUSDT", "type": "delta", "ts": 20, "data": {"symbol": s, "markPrice": "1.5"}}
    )
    assert q is None


def test_bingx_gap_invalid_until_snapshot():
    book = IncrementalBook("bingx")

    def msg(action, seq, bids):
        return {"data": {"action": action, "lastUpdateId": seq, "bids": bids, "asks": [["2", "1"]], "T": 10}}

    assert book.apply(msg("all", 10, [["1", "1"]])).valid
    assert not book.apply(msg("update", 12, [])).valid
    assert not book.apply(msg("update", 13, [])).valid
    assert book.apply(msg("all", 20, [["1", "3"]])).valid
    assert book.apply(msg("update", 21, [["1", "0"]])).bids == []


def test_bybit_noncontiguous_update_ids_are_legal():
    book = IncrementalBook("bybit")
    assert book.apply(
        {"type": "snapshot", "ts": 10, "data": {"u": 100, "b": [["1", "1"]], "a": [["2", "1"]]}}
    ).valid
    assert book.apply({"type": "delta", "ts": 11, "data": {"u": 110, "b": [], "a": []}}).valid
    assert not book.apply({"type": "delta", "ts": 11, "data": {"u": 109, "b": [], "a": []}}).valid


@pytest.mark.asyncio
async def test_bybit_pagination_and_filter():
    row = {
        "symbol": "BTCUSDT",
        "baseCoin": "BTC",
        "quoteCoin": "USDT",
        "settleCoin": "USDT",
        "status": "Trading",
        "contractType": "LinearPerpetual",
        "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001"},
        "priceFilter": {"tickSize": "0.1"},
    }

    class HTTP:
        venue = "bybit"

        def __init__(self):
            self.calls = []

        async def get(self, path, params):
            self.calls.append(params["cursor"])
            return {
                "result": {
                    "list": [row] if not params["cursor"] else [dict(row, status="PreLaunch")],
                    "nextPageCursor": "page2" if not params["cursor"] else "",
                }
            }

    http = HTTP()
    rows, excluded, native = await catalog(http)
    assert len(rows) == 1 and len(native) == 2
    assert http.calls == ["", "page2"]
    assert excluded["INACTIVE_OR_UNSUPPORTED"] == 1


@pytest.mark.asyncio
async def test_queue_backpressure_and_disconnect_invalidation():
    scanner = Scanner(Config(queue_size=1))
    qa, *_ = market()
    await scanner.emit("bybit", "BTCUSDT", qa, None, None, time.monotonic())
    await scanner.emit("bybit", "BTCUSDT", qa, None, None, time.monotonic())
    assert scanner.metrics["dropped_events"] == 1
    scanner.quotes[("bybit", "BTCUSDT")] = qa
    await scanner.emit("bybit", "*", None, None, None, time.monotonic(), invalidate=["BTCUSDT"])
    assert not scanner.quotes


@pytest.mark.asyncio
async def test_real_consumer_both_directions_and_journal():
    scanner = Scanner(Config(min_spread_pct=D(0)))
    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    scanner.instruments = {a.key: a, b.key: b}
    scanner.by_base["BTC"] = [a, b]
    scanner.books = {a.key: ba, b.key: bb}
    scanner.funding = {a.key: f, b.key: f}
    task = asyncio.create_task(scanner.consume())
    await scanner.emit(a.venue, a.symbol, qa, None, None, time.monotonic())
    await scanner.emit(b.venue, b.symbol, qb, None, None, time.monotonic())
    for _ in range(100):
        if scanner.metrics["pair_comparisons"] >= 2:
            break
        await asyncio.sleep(0.001)
    assert scanner.metrics["pair_comparisons"] == 2
    assert any(s.cheap == "bybit" for s in scanner.signals.values())
    # Reverse the market and verify opposite direction is discovered.
    await scanner.emit(b.venue, b.symbol, replace(qb, bid=D(94), ask=D(95)), None, None, time.monotonic())
    for _ in range(100):
        if any(s.cheap == "bingx" for s in scanner.signals.values()):
            break
        await asyncio.sleep(0.001)
    assert any(s.cheap == "bingx" for s in scanner.signals.values())
    assert scanner.journal.recent
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_journal_bounded_and_batch():
    j = Journal(capacity=1)
    j.append({"id": "a"})
    j.append({"id": "b"})
    assert j.dropped == 1
    stop = asyncio.Event()
    stop.set()
    await j.run(stop)
    assert j.written == 1


@pytest.mark.asyncio
async def test_journal_overflow_latches_failure_and_stops_producer():
    j = Journal(capacity=1)
    j.stop = asyncio.Event()
    j.append({"id": "first"})
    j.append({"id": "overflow"})
    assert j.stop.is_set()
    assert j.fatal_error == "JOURNAL_QUEUE_FULL"
    await j.run(j.stop)
    assert j.written == 1
    assert j.dropped == 1
    assert j.fatal_error == "JOURNAL_QUEUE_FULL"
