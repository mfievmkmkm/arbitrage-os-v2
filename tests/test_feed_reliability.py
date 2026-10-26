import asyncio
import json
import time
from collections import Counter
from dataclasses import replace

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer
from tests_support import instrument, market

from adapters.cex import public
from adapters.cex.public import BybitTopParser, ProviderError
from apps.scanner.service import Scanner
from core.evaluator import funding_rejections
from core.identity import identify, load_registry
from core.models import D, Reason


def top(ts=2000, update=100, bids=None):
    return {
        "topic": "orderbook.1.BTCUSDT",
        "type": "snapshot",
        "ts": ts,
        "cts": 1000,
        "data": {
            "s": "BTCUSDT",
            "u": update,
            "seq": 1000,
            "b": [["100", "2"]] if bids is None else bids,
            "a": [["101", "3"]],
        },
    }


def test_repeated_full_snapshot_confirms_quote_without_rewriting_matching_engine_time():
    parser = BybitTopParser()
    parser.parse(top())
    _, quote = parser.parse(top(ts=5000))
    assert quote.source_ms == 5000 and quote.matching_engine_ms == 1000
    assert quote.sequence == 100 and quote.source == "BYBIT_ORDERBOOK_1_SNAPSHOT"
    assert parser.parse({"topic": "tickers.BTCUSDT", "ts": 6000}) is None
    with pytest.raises(ProviderError, match="INVALID_MARKET_TIME"):
        parser.parse(top(ts=3000))
    _, empty = parser.parse(top(ts=7000, bids=[]))
    assert not empty.valid()


@pytest.mark.asyncio
async def test_bybit_real_websocket_boundary_uses_only_orderbook1_for_broad_quotes(monkeypatch):
    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        request = await ws.receive_json()
        assert request["args"] == ["orderbook.1.BTCUSDT"]
        await ws.send_json(top(ts=int(time.time() * 1000)))
        await ws.receive()
        return ws

    app = web.Application()
    app.router.add_get("/ws", handler)
    async with TestServer(app) as server, ClientSession() as session:
        monkeypatch.setitem(public.WS, "bybit", str(server.make_url("/ws")).replace("http:", "ws:"))
        stop, events, health, metrics = asyncio.Event(), [], {}, Counter()

        async def emit(venue, symbol, q, f, book, received, **kwargs):
            if q:
                events.append(q)
                stop.set()

        await asyncio.wait_for(public.stream(session, "bybit", ["BTCUSDT"], emit, health, metrics, stop), 3)
        assert events[0].ask == 101 and events[0].bid_qty == 2
        assert health["quotes_connections"] == health["connections"] == 0
        assert metrics["bybit_quotes_ws_connected"] == 1


def test_depth_hysteresis_keeps_warm_verified_pairs_and_respects_budget():
    scanner = Scanner()
    a, b = instrument(), instrument("bingx")
    scanner.instruments = {a.key: a, b.key: b}
    scanner.by_asset[a.asset_id] = [a, b]
    assert scanner.select_depth(int(time.time() * 1000), 100) == {a.key, b.key}
    unreviewed = replace(a, symbol="OTHERUSDT", base="OTHER", asset_id=None)
    scanner.instruments[unreviewed.key] = unreviewed
    scanner.depth_tasks[unreviewed.key] = object()
    scanner.depth_selected_at[unreviewed.key] = 95
    assert unreviewed.key in scanner.select_depth(0, 100)
    assert unreviewed.key not in scanner.select_depth(0, 126)


def test_registry_native_bindings_do_not_promote_wrappers_or_unreviewed_sources():
    registry = load_registry()
    btc = identify(instrument(asset_id=None), registry)
    assert btc.asset_id == "native:bitcoin"
    assert identify(instrument("bingx", asset_id=None), registry).asset_id == btc.asset_id
    assert identify(instrument(symbol="1000BTCUSDT", asset_id=None), registry).asset_id is None
    assert identify(instrument(base="WBTC", asset_id=None), registry).asset_id is None
    assert identify(instrument(multiplier=D(1000), asset_id=None), registry).asset_id is None
    row = dict(registry[0], sources={"bybit": "https://not-bybit.com/", "bingx": "https://bingx.com/"})
    assert identify(instrument(asset_id=None), [row]).asset_id is None


def test_funding_failures_are_specific_and_never_silently_assume_interval():
    funding = market()[-1]
    now, ms = time.monotonic(), int(time.time() * 1000)
    assert funding_rejections(None, ms, now) == [Reason.FUNDING_MISSING]
    assert Reason.FUNDING_INTERVAL in funding_rejections(replace(funding, interval_ms=0), ms, now)
    assert Reason.FUNDING_STALE in funding_rejections(replace(funding, received=now - 121), ms, now)
    assert Reason.FUNDING_TIME in funding_rejections(replace(funding, next_ms=ms), ms, now)
    assert Reason.FUNDING_INVALID in funding_rejections(replace(funding, rate=D("NaN")), ms, now)


@pytest.mark.asyncio
async def test_rest_funding_refresh_does_not_change_ws_quote_age(monkeypatch):
    scanner = Scanner()
    a = instrument()
    scanner.instruments[a.key] = a
    quote = market()[0]
    scanner.quotes[a.key] = quote

    class HTTP:
        async def get(self, path, params):
            assert path == "/v5/market/tickers" and params == {"category": "linear"}
            return {
                "result": {
                    "list": [
                        {
                            "symbol": a.symbol,
                            "fundingRate": ".0001",
                            "nextFundingTime": str(int(time.time() * 1000) + 3600000),
                            "fundingIntervalHour": "1",
                        }
                    ]
                }
            }

    scanner.http = {"bybit": HTTP()}

    async def stop_after_iteration(seconds):
        scanner.stop.set()

    monkeypatch.setattr("apps.scanner.service.asyncio.sleep", stop_after_iteration)
    await scanner.funding_loop()
    assert scanner.quotes[a.key] is quote
    assert scanner.funding[a.key].interval_ms == 3600000
    assert scanner.status()["coverage"]["bybit"]["funding_usable"] == 1
    assert scanner.metrics["bybit_funding_refreshes"] == 1


@pytest.mark.asyncio
async def test_planned_depth_change_does_not_claim_provider_outage():
    scanner = Scanner()
    a, b = instrument(), instrument("bingx")
    from core.evaluator import evaluate

    qa, qb, ba, bb, f = market()
    signal = evaluate(a, b, qa, qb, ba, bb, f, f, scanner.cfg)
    scanner.signals[signal.id] = signal
    await scanner.emit(
        "bybit",
        "*",
        None,
        None,
        None,
        time.monotonic(),
        invalidate=[a.symbol],
        depth=True,
        invalidate_reason=Reason.BOOK,
    )
    assert Reason.BOOK in signal.rejection_codes and Reason.OUTAGE not in signal.rejection_codes
    assert signal.expires_at_ms <= int(time.time() * 1000)


def test_quote_extra_metadata_remains_json_serializable():
    # HTTP status and saved reports must still encode the new quote provenance.
    from dataclasses import asdict

    from apps.scanner.main import json_safe

    q = BybitTopParser().parse(top())[1]
    assert json.loads(json.dumps(json_safe(asdict(q))))["matching_engine_ms"] == 1000


def test_rejected_update_windows_preserve_counts_extremes_and_terminal_order():
    from core.evaluator import evaluate

    scanner = Scanner()
    a, b = instrument(asset_id=None), instrument("bingx", asset_id=None)
    qa, qb, ba, bb, f = market()
    first = evaluate(a, b, qa, qb, ba, bb, f, f, scanner.cfg)
    scanner.record_signal(first, None)
    previous = first
    for i in range(1000):
        signal = replace(
            first,
            raw_spread_pct=float(i) / 100,
            rejection_codes=[Reason.IDENTITY, Reason.BOOK] if i % 2 else [Reason.IDENTITY],
        )
        scanner.record_signal(signal, previous)
        previous = signal
    # One full start plus one aggregate, rather than 1000 alternating-reason rows.
    scanner.flush_rejection_window(first.id)
    rows = list(scanner.journal.recent)
    assert len(rows) == 2
    window = rows[1]["aggregation"]
    assert window["observations"] == 1000
    assert window["rejection_counts"][Reason.IDENTITY] == 1000
    assert window["rejection_counts"][Reason.BOOK] == 500
    assert window["raw_spread_min_pct"] == 0 and window["raw_spread_max_pct"] == 9.99
    verified = replace(previous, stage="VERIFIED", rejection_codes=[])
    scanner.record_signal(verified, previous)
    assert scanner.journal.recent[-1]["stage"] == "VERIFIED"


def test_stale_book_blocks_verification_without_hiding_fresh_raw_candidate():
    from core.evaluator import evaluate

    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    ba.source_ms -= 10000
    signal = evaluate(a, b, qa, qb, ba, bb, f, f, Scanner().cfg)
    assert signal.stage == "BLOCKED" and Reason.STALE in signal.rejection_codes
    assert signal.expires_at_ms > int(time.time() * 1000)
    assert signal.immediate_round_trip_net_usd is None


def test_verified_signal_expires_with_its_oldest_executable_book():
    from core.evaluator import evaluate

    a, b = instrument(), instrument("bingx")
    qa, qb, ba, bb, f = market()
    ba.source_ms -= 500
    signal = evaluate(a, b, qa, qb, ba, bb, f, f, Scanner().cfg)
    assert signal.stage == "VERIFIED"
    assert signal.expires_at_ms <= ba.source_ms + 2000


@pytest.mark.asyncio
async def test_health_history_query_is_scoped_and_parameterized():
    from aiohttp.test_utils import TestClient

    from apps.scanner.main import api

    scanner = Scanner()
    scanner.journal.append({"id": "A1:other", "stage": "BLOCKED"})
    scanner.journal.append({"id": "INFRA:observation-health", "stage": "OBSERVE"})
    async with TestClient(TestServer(api(scanner))) as client:
        response = await client.get("/history?signal_id=INFRA:observation-health&limit=200")
        assert [r["id"] for r in await response.json()] == ["INFRA:observation-health"]
        assert (await client.get("/history?limit=not-a-number")).status == 400
