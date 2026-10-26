"""Explicit reviewed cross-venue registry. Never promote symbol equality to identity."""

import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse


def load_registry(path="configs/identity.json"):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else []


def identify(instrument, registry):
    for row in registry:
        sources = row.get("sources", {})
        reviewed_sources = all(
            urlparse(sources.get(v, "")).hostname in hosts
            for v, hosts in (
                ("bybit", {"www.bybit.com", "bybit.com"}),
                ("bingx", {"www.bingx.com", "bingx.com"}),
            )
        )
        binding = row.get("instruments", {}).get(instrument.venue)
        if (
            binding
            and row.get("review_status") == "REVIEWED"
            and reviewed_sources
            and set(row.get("instruments", {})) == {"bybit", "bingx"}
            and instrument.spec_verified
            and binding["symbol"] == instrument.symbol
            and binding["base"] == instrument.base
            and instrument.quote == instrument.settle == "USDT"
            and str(instrument.multiplier) == binding["multiplier"]
            and row.get("proof")
            and row.get("reviewed_at")
        ):
            return replace(instrument, asset_id=row["asset_id"], identity_proof=row["proof"])
    return instrument


def compatible(a, b):
    return (
        a.venue != b.venue
        and a.asset_id is not None
        and a.asset_id == b.asset_id
        and a.spec_verified
        and b.spec_verified
        and a.multiplier > 0
        and b.multiplier > 0
        and a.quote == b.quote == a.settle == b.settle == "USDT"
    )
