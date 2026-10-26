"""Canonical units: price USDT/base, quantity base; UTC ms and monotonic receive clocks."""

import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

D = Decimal


class Reason(StrEnum):
    IDENTITY = "ASSET_IDENTITY_UNVERIFIED"
    CONTRACT = "CONTRACT_SPEC_UNVERIFIED"
    STALE = "QUOTE_STALE"
    SKEW = "QUOTE_TIMESTAMP_SKEW"
    DEPTH = "BOOK_DEPTH_TOO_LOW"
    BOOK = "ORDERBOOK_UNAVAILABLE"
    GAP = "ORDERBOOK_GAP"
    MINIMUM = "MIN_ORDER_NOT_MET"
    SIZE = "NOTIONAL_CAP_EXCEEDED"
    FEES = "FEE_UNAVAILABLE"
    FUNDING = "FUNDING_UNAVAILABLE"
    NET = "NET_TARGET_NOT_REACHABLE"
    COUNTERPART = "NO_COUNTERPART"
    EMPTY = "ORDERBOOK_EMPTY"
    CROSSED = "ORDERBOOK_CROSSED"
    INVALID_BOOK = "ORDERBOOK_INVALID_LEVELS"
    BOOK_SKEW = "ORDERBOOK_TIMESTAMP_SKEW"
    INVALID_TIME = "INVALID_MARKET_TIME"
    OUTAGE = "DATA_PROVIDER_OUTAGE"
    SLIPPAGE = "SLIPPAGE_LIMIT_EXCEEDED"


@dataclass(frozen=True, slots=True)
class Instrument:
    venue: str
    symbol: str
    base: str
    quote: str
    settle: str
    step: Decimal
    minimum: Decimal
    min_notional: Decimal
    tick: Decimal
    multiplier: Decimal = D(1)
    spec_verified: bool = False
    asset_id: str | None = None
    identity_proof: str | None = None
    taker_fee: Decimal | None = None
    fee_source: str = "UNKNOWN"

    def __post_init__(self):
        from core.config import ALLOWED_VENUES

        if self.venue not in ALLOWED_VENUES:
            raise ValueError("Unsupported venue")
        for x in (self.step, self.minimum, self.tick, self.multiplier):
            if not x.is_finite() or x <= 0:
                raise ValueError("Invalid contract units")
        if not self.min_notional.is_finite() or self.min_notional < 0:
            raise ValueError("Invalid minimum notional")
        if self.taker_fee is not None and (not self.taker_fee.is_finite() or self.taker_fee < 0):
            raise ValueError("Invalid fee rate")

    @property
    def key(self):
        return self.venue, self.symbol


@dataclass(slots=True)
class Quote:
    bid: Decimal
    ask: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    source_ms: int
    received: float = field(default_factory=time.monotonic)

    def valid(self):
        return (
            all(x.is_finite() and x > 0 for x in (self.bid, self.ask, self.bid_qty, self.ask_qty))
            and self.bid <= self.ask
        )


@dataclass(slots=True)
class Book:
    bids: list[tuple[Decimal, Decimal]]
    asks: list[tuple[Decimal, Decimal]]
    source_ms: int
    received: float = field(default_factory=time.monotonic)
    sequence: int | None = None
    valid: bool = True
    cross_sequence: int | None = None

    def rejection(self):
        if not self.valid:
            return Reason.GAP
        if not self.bids or not self.asks:
            return Reason.EMPTY
        if any(not p.is_finite() or not q.is_finite() or p <= 0 or q <= 0 for p, q in self.bids + self.asks):
            return Reason.INVALID_BOOK
        if (
            self.bids != sorted(self.bids, reverse=True)
            or self.asks != sorted(self.asks)
            or len({p for p, _ in self.bids}) != len(self.bids)
            or len({p for p, _ in self.asks}) != len(self.asks)
        ):
            return Reason.INVALID_BOOK
        if self.bids[0][0] > self.asks[0][0]:
            return Reason.CROSSED
        return None


@dataclass(slots=True)
class Funding:
    rate: Decimal
    next_ms: int
    interval_ms: int
    received: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class Signal:
    id: str
    asset: str
    cheap: str
    expensive: str
    raw_spread_pct: float
    observed_at_ms: int
    expires_at_ms: int
    rejection_codes: list[str]
    stage: str = "RAW"
    strategy: str = "A1"
    schema_version: int = 1
    source: str = "INTERNAL_SCANNER"
    route_tradeability: str = "MODE_OBSERVE"
    size_usd: float = 100
    qty_base: str | None = None
    buy_vwap: str | None = None
    sell_vwap: str | None = None
    opening_fees_usd: str | None = None
    estimated_closing_fees_usd: str | None = None
    funding_expected_usd: str | None = None
    immediate_round_trip_net_usd: str | None = None
    scenario_net_at_target_basis_usd: str | None = None
    quote_age_ms: float = 0
    identity_proof: list[str] = field(default_factory=list)
    confidence_flags: list[str] = field(default_factory=list)
    long_symbol: str = ""
    short_symbol: str = ""
    long_bid: str = ""
    long_ask: str = ""
    short_bid: str = ""
    short_ask: str = ""
    quote_source_timestamps_ms: list[int] = field(default_factory=list)
    orderbook_sequences: list[int | None] = field(default_factory=list)
    max_symmetric_qty_base: str | None = None
    max_executable_notional_usd: str | None = None
    first_seen_at_ms: int = 0
    peak_spread_pct: float = 0
    size_checks: list[dict] = field(default_factory=list)
