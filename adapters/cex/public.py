"""Public endpoints only. No signing, account, order or transfer methods exist."""

import asyncio
import json
import random
import time
import uuid
from collections import Counter

from aiohttp import ClientWSTimeout

from core.models import Book, D, Funding, Instrument, Quote

REST = {"bybit": "https://api.bybit.com", "bingx": "https://open-api.bingx.com"}
WS = {
    "bybit": "wss://stream.bybit.com/v5/public/linear",
    "bingx": "wss://open-api-swap.bingx.com/swap-market",
}


class ProviderError(Exception):
    pass


class PublicHTTP:
    def __init__(self, session, venue, metrics):
        self.session, self.venue, self.metrics = session, venue, metrics
        self.lock = asyncio.Lock()
        self.last = 0.0

    async def get(self, path, params=None):
        async with self.lock:
            await asyncio.sleep(max(0, 1.05 - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            async with self.session.get(REST[self.venue] + path, params=params, timeout=15) as r:
                if r.status == 429:
                    self.metrics["http_429"] += 1
                    retry = min(60, max(1, float(r.headers.get("Retry-After", "5"))))
                    await asyncio.sleep(retry)
                    raise ProviderError("HTTP_429")
                if r.status != 200:
                    raise ProviderError(f"HTTP_{r.status}")
                # An HTML access-denial page can have status 200. Never call it an empty catalog.
                try:
                    data = await r.json(content_type=None)
                except (ValueError, UnicodeError):
                    raise ProviderError("NON_JSON_RESPONSE") from None
                code = data.get("retCode", data.get("code", 0))
                if int(code) != 0:
                    if int(code) == 100410:
                        self.metrics["http_429"] += 1
                        await asyncio.sleep(5)
                    raise ProviderError(f"API_CODE_{code}")
                return data


def bybit_instrument(row):
    lot = row["lotSizeFilter"]
    return Instrument(
        "bybit",
        row["symbol"],
        row["baseCoin"],
        row["quoteCoin"],
        row["settleCoin"],
        D(lot["qtyStep"]),
        D(lot["minOrderQty"]),
        D(lot.get("minNotionalValue", "0")),
        D(row["priceFilter"]["tickSize"]),
        spec_verified=True,
        taker_fee=D("0.00055"),
        fee_source="PUBLIC_NON_VIP_SCHEDULE_2026_10_26_NOT_ACCOUNT_SPECIFIC",
    )


def bingx_instrument(row):
    # Public quote sizes / order quantity use base units. Catalog 'size' is retained separately,
    # not incorrectly applied as an extra multiplier to already base-denominated WS quantities.
    return Instrument(
        "bingx",
        row["symbol"],
        row["asset"],
        "USDT",
        row["currency"],
        D(10) ** -int(row["quantityPrecision"]),
        D(str(row["tradeMinQuantity"])),
        D(str(row["tradeMinUSDT"])),
        D(10) ** -int(row["pricePrecision"]),
        spec_verified=True,
        taker_fee=D(str(row["takerFeeRate"])),
        fee_source="PUBLIC_CONTRACT_SCHEDULE",
    )


async def catalog(http):
    output, excluded, native = [], Counter(), []
    if http.venue == "bybit":
        cursor, seen = "", set()
        while True:
            data = await http.get(
                "/v5/market/instruments-info", {"category": "linear", "limit": 1000, "cursor": cursor}
            )
            rows = data["result"]["list"]
            native.extend(rows)
            for r in rows:
                if (
                    r["status"] != "Trading"
                    or r["contractType"] != "LinearPerpetual"
                    or r["quoteCoin"] != "USDT"
                    or r["settleCoin"] != "USDT"
                ):
                    excluded["INACTIVE_OR_UNSUPPORTED"] += 1
                    continue
                try:
                    output.append(bybit_instrument(r))
                except (KeyError, ValueError, ArithmeticError):
                    excluded["CONTRACT_SPEC_UNVERIFIED"] += 1
            cursor = data["result"].get("nextPageCursor", "")
            if not cursor:
                break
            if cursor in seen:
                raise ProviderError("PAGINATION_CURSOR_LOOP")
            seen.add(cursor)
    else:
        native = (await http.get("/openApi/swap/v2/quote/contracts"))["data"]
        for r in native:
            if (
                r.get("status") != 1
                or r.get("currency") != "USDT"
                or not r["symbol"].endswith("-USDT")
                or r.get("offTime", 0)
                or r.get("launchTime", 0) > time.time() * 1000
                or r.get("maintainTime", 0)
            ):
                excluded["INACTIVE_OR_UNSUPPORTED"] += 1
                continue
            try:
                output.append(bingx_instrument(r))
            except (KeyError, ValueError, ArithmeticError):
                excluded["CONTRACT_SPEC_UNVERIFIED"] += 1
    if len({x.key for x in output}) != len(output):
        raise ProviderError("DUPLICATE_INSTRUMENT")
    return output, excluded, native


def decode(payload):
    if isinstance(payload, bytes):
        if payload.startswith(b"\x1f\x8b"):
            # Bounded output protects event-loop memory from oversized compressed messages.
            import zlib

            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            payload = decoder.decompress(payload, 4 * 1024 * 1024)
            if decoder.unconsumed_tail:
                raise ProviderError("FRAME_TOO_LARGE")
        payload = payload.decode("utf-8")
    if payload in ("Ping", "Pong"):
        return payload
    return json.loads(payload)


class BybitParser:
    def __init__(self):
        self.cache = {}
        self.field_times = {}
        self.funding_intervals = {}

    def parse(self, msg):
        if not msg.get("topic", "").startswith("tickers."):
            return None
        row = msg["data"]
        symbol = row["symbol"]
        if msg.get("type") == "snapshot":
            self.cache[symbol] = {}
            self.field_times[symbol] = {}
        state = self.cache.setdefault(symbol, {})
        state.update(row)
        stamps = self.field_times.setdefault(symbol, {})
        for key in row:
            stamps[key] = int(msg["ts"])
        fields = ("bid1Price", "ask1Price", "bid1Size", "ask1Size")
        # Funding/mark-only deltas must not refresh the timestamp of an old bid/ask.
        quote = None
        if any(k in row for k in fields) and all(k in state for k in fields):
            quote = Quote(*(D(state[k]) for k in fields), min(stamps[k] for k in fields))
        funding = None
        if "fundingRate" in row and state.get("nextFundingTime"):
            funding = Funding(
                D(state["fundingRate"]), int(state["nextFundingTime"]), self.funding_intervals.get(symbol, 0)
            )
        return symbol, quote, funding


class IncrementalBook:
    """Bybit u is monotonic, not guaranteed consecutive; BingX IDs are consecutive."""

    def __init__(self, venue):
        self.venue, self.seq, self.bids, self.asks = venue, None, {}, {}

    def apply(self, msg):
        data = msg["data"]
        snapshot = msg.get("type") == "snapshot" if self.venue == "bybit" else data.get("action") == "all"
        seq = int(data["u"] if self.venue == "bybit" else data["lastUpdateId"])
        if self.venue == "bybit" and seq == 1:
            snapshot = True
        if snapshot:
            self.bids.clear()
            self.asks.clear()
        elif (
            self.seq is None
            or (self.venue == "bingx" and seq != self.seq + 1)
            or (self.venue == "bybit" and seq <= self.seq)
        ):
            self.seq = None
            return Book([], [], int(msg.get("ts", data.get("T", 0))), valid=False)
        for side, key in (
            (self.bids, "b" if self.venue == "bybit" else "bids"),
            (self.asks, "a" if self.venue == "bybit" else "asks"),
        ):
            for p, q in data.get(key, []):
                p, q = D(p), D(q)
                if not p.is_finite() or not q.is_finite() or p <= 0 or q < 0:
                    raise ProviderError("INVALID_BOOK_LEVEL")
                if q == 0:
                    side.pop(p, None)
                else:
                    side[p] = q
        if len(self.bids) + len(self.asks) > 2000:
            raise ProviderError("BOOK_TOO_LARGE")
        self.seq = seq
        return Book(
            sorted(self.bids.items(), reverse=True),
            sorted(self.asks.items()),
            int(msg.get("ts", data.get("T", 0))),
            sequence=seq,
        )


async def heartbeat(ws, venue):
    while True:
        await asyncio.sleep(20)
        if venue == "bybit":
            await ws.send_json({"op": "ping"})
        # BingX application Ping is answered by the receiver, not synthesized here.


async def stream(session, venue, symbols, emit, health, metrics, stop, depth=False, intervals=None):
    backoff = 1
    while not stop.is_set():
        parser = BybitParser()
        parser.funding_intervals = intervals or {}
        books = {s: IncrementalBook(venue) for s in symbols}
        heartbeat_task = None
        try:
            async with session.ws_connect(
                WS[venue],
                heartbeat=20,
                max_msg_size=4 * 1024 * 1024,
                timeout=ClientWSTimeout(ws_receive=45, ws_close=10),
            ) as ws:
                health["connections"] = health.get("connections", 0) + 1
                if venue == "bybit":
                    for i in range(0, len(symbols), 10):
                        await ws.send_json(
                            {
                                "op": "subscribe",
                                "args": [
                                    f"orderbook.50.{s}" if depth else f"tickers.{s}"
                                    for s in symbols[i : i + 10]
                                ],
                            }
                        )
                        await asyncio.sleep(0.2)
                else:
                    for s in symbols:
                        await ws.send_json(
                            {
                                "id": str(uuid.uuid4()),
                                "reqType": "sub",
                                "dataType": s + ("@depth50@500ms" if depth else "@bookTicker"),
                            }
                        )
                        await asyncio.sleep(0.15)
                heartbeat_task = asyncio.create_task(heartbeat(ws, venue))
                async for frame in ws:
                    if frame.type.name not in ("TEXT", "BINARY"):
                        if frame.type.name in ("CLOSED", "ERROR", "CLOSE"):
                            break
                        continue
                    received = time.monotonic()
                    msg = decode(frame.data)
                    if msg == "Ping":
                        await ws.send_str("Pong")
                        metrics["ping_pong"] += 1
                        continue
                    if msg == "Pong":
                        continue
                    if msg.get("success") is False or int(msg.get("code", 0)) != 0:
                        metrics["subscription_errors"] += 1
                        raise ProviderError("SUBSCRIPTION_REJECTED")
                    if depth:
                        channel = msg.get("topic", msg.get("dataType", ""))
                        symbol = channel.split(".")[-1] if venue == "bybit" else channel.split("@")[0]
                        if symbol not in books or "data" not in msg:
                            continue
                        if venue == "bingx":
                            data = msg["data"]
                            if not isinstance(data, dict):
                                continue
                            bids = [(D(p), D(q)) for p, q in data["bids"]]
                            asks = [(D(p), D(q)) for p, q in data["asks"]]
                            if len(bids) > 50 or len(asks) > 50:
                                raise ProviderError("LIMITED_DEPTH_EXCEEDS_BUDGET")
                            if any(
                                not p.is_finite() or not q.is_finite() or p <= 0 or q <= 0
                                for p, q in bids + asks
                            ):
                                raise ProviderError("INVALID_BOOK_LEVEL")
                            book = Book(sorted(bids, reverse=True), sorted(asks), int(msg["ts"]))
                        else:
                            book = books[symbol].apply(msg)
                        if not book.valid:
                            metrics["orderbook_gaps"] += 1
                            await emit(venue, symbol, None, None, book, received)
                            raise ProviderError("ORDERBOOK_GAP")
                        await emit(venue, symbol, None, None, book, received)
                    elif venue == "bybit":
                        parsed = parser.parse(msg)
                        if parsed:
                            s, quote, funding = parsed
                            await emit(venue, s, quote, funding, None, received)
                    elif "@bookTicker" in msg.get("dataType", ""):
                        r = msg["data"]
                        s = r.get("s", msg["dataType"].split("@")[0])
                        q = Quote(*(D(str(r[k])) for k in ("b", "a", "B", "A")), int(r["T"]))
                        await emit(venue, s, q, None, None, received)
                    else:
                        continue
                    health["last_event_ms"] = int(time.time() * 1000)
                    metrics["ws_frames"] += 1
                    backoff = 1
                    if stop.is_set():
                        break
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            metrics["provider_errors"] += 1
            health["last_error"] = type(exc).__name__ + ":" + str(exc)[:120]
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            health["connections"] = max(0, health.get("connections", 1) - 1)
            # Invalidate on disconnect immediately rather than waiting for TTL.
            await emit(venue, "*", None, None, None, time.monotonic(), invalidate=symbols, depth=depth)
        metrics["ws_reconnects"] += 1
        try:
            await asyncio.wait_for(stop.wait(), timeout=backoff + random.random())
        except TimeoutError:
            pass
        backoff = min(60, backoff * 2)
