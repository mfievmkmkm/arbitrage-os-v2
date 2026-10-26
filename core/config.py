import os
from dataclasses import dataclass
from decimal import Decimal

ALLOWED_VENUES = ("bybit", "bingx")


@dataclass(frozen=True)
class Config:
    venues: tuple[str, ...] = ALLOWED_VENUES
    mode: str = "OBSERVE"
    size: Decimal = Decimal("100")
    min_spread_pct: Decimal = Decimal("0.1")
    min_net: Decimal = Decimal("0.1")
    target_basis_pct: Decimal = Decimal("0")
    slippage_reserve: Decimal = Decimal("0.2")
    quote_ttl: float = 2.0
    max_skew_ms: int = 1000
    hold_seconds: int = 3600
    shard_size: int = 40
    shortlist: int = 12
    catalog_interval: int = 3600
    queue_size: int = 5000
    port: int = 8080

    def __post_init__(self):
        if self.mode != "OBSERVE" or set(self.venues) - set(ALLOWED_VENUES) or not self.venues:
            raise ValueError("Only OBSERVE on bybit/bingx is implemented")
        for x in (self.size, self.min_spread_pct, self.min_net, self.target_basis_pct, self.slippage_reserve):
            if not x.is_finite() or x < 0:
                raise ValueError("Finite nonnegative settings required")
        if not 0 < self.size <= 100000 or not 0 < self.quote_ttl <= 60:
            raise ValueError("Settings out of range")
        if not 1 <= self.queue_size <= 100000 or not 1 <= self.catalog_interval <= 86400:
            raise ValueError("Queue or refresh budget out of range")
        if not 0 <= self.hold_seconds <= 604800 or not 0 <= self.max_skew_ms <= 60000:
            raise ValueError("Timing budget out of range")
        if len(set(self.venues)) != len(self.venues):
            raise ValueError("Duplicate venues")
        if not 1 <= self.shard_size <= 40 or not 1 <= self.shortlist <= 50:
            raise ValueError("Feed budget out of range")

    @classmethod
    def env(cls):
        return cls(
            venues=tuple(os.getenv("ENABLED_CEX_VENUES", "bybit,bingx").split(",")),
            mode=os.getenv("MODE", "OBSERVE"),
            port=int(os.getenv("PORT", "8080")),
            size=Decimal(os.getenv("SIZE_USD", "100")),
            min_spread_pct=Decimal(os.getenv("MIN_SPREAD_PCT", "0.1")),
        )
