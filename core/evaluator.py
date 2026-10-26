import time
from decimal import ROUND_FLOOR
from math import lcm

from core.identity import compatible
from core.models import D, Reason, Signal


def common_step(a, b):
    scale = 10 ** max(-a.as_tuple().exponent, -b.as_tuple().exponent, 0)
    return D(lcm(int(a * scale), int(b * scale))) / scale


def vwap(levels, qty):
    left, total = qty, D(0)
    for price, volume in levels:
        fill = min(left, volume)
        total += fill * price
        left -= fill
        if left <= 0:
            return total / qty
    return None


def fresh(source_ms, received, cfg, now_ms, now):
    return 0 <= now_ms - source_ms <= cfg.quote_ttl * 1000 and 0 <= now - received <= cfg.quote_ttl


def evaluate(a, b, qa, qb, ba, bb, fa, fb, cfg, now_ms=None, now=None):
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    now = now if now is not None else time.monotonic()
    raw = (qb.bid / qa.ask - 1) * 100
    s = Signal(
        f"A1:{a.venue}:{a.symbol}:{b.venue}:{b.symbol}",
        a.asset_id or a.base,
        a.venue,
        b.venue,
        float(raw),
        now_ms,
        now_ms + int(cfg.quote_ttl * 1000),
        [],
        size_usd=float(cfg.size),
    )
    s.long_symbol, s.short_symbol = a.symbol, b.symbol
    s.long_bid, s.long_ask = str(qa.bid), str(qa.ask)
    s.short_bid, s.short_ask = str(qb.bid), str(qb.ask)
    s.quote_source_timestamps_ms = [qa.source_ms, qb.source_ms]
    s.orderbook_sequences = [ba.sequence if ba else None, bb.sequence if bb else None]
    reasons = s.rejection_codes
    if not compatible(a, b):
        reasons.append(Reason.IDENTITY if not a.asset_id or not b.asset_id else Reason.CONTRACT)
    if not (qa.valid() and qb.valid()) or not all(
        fresh(q.source_ms, q.received, cfg, now_ms, now) for q in (qa, qb)
    ):
        reasons.append(Reason.STALE)
    s.quote_age_ms = max(
        now_ms - qa.source_ms, now_ms - qb.source_ms, (now - qa.received) * 1000, (now - qb.received) * 1000
    )
    if abs(qa.source_ms - qb.source_ms) > cfg.max_skew_ms:
        reasons.append(Reason.SKEW)
    if not ba or not bb:
        reasons.append(Reason.BOOK)
    elif not ba.valid or not bb.valid:
        reasons.append(Reason.GAP)
    elif not all(fresh(x.source_ms, x.received, cfg, now_ms, now) for x in (ba, bb)):
        reasons.append(Reason.STALE)
    if a.taker_fee is None or b.taker_fee is None:
        reasons.append(Reason.FEES)
    horizon_ms = now_ms + cfg.hold_seconds * 1000
    for f in (fa, fb):
        if (
            f is None
            or now - f.received > 120
            or f.interval_ms <= 0
            or f.next_ms <= now_ms
            or not f.rate.is_finite()
        ):
            reasons.append(Reason.FUNDING)
            break
    s.identity_proof = [x for x in (a.identity_proof, b.identity_proof) if x]
    s.confidence_flags = [
        f"FEES_{a.fee_source}",
        f"FEES_{b.fee_source}",
        "TARGET_BASIS_IS_HYPOTHETICAL",
        "NO_ACCOUNT_MARGIN_VERIFICATION",
        "FUNDING_FORECAST_USES_CURRENT_RATE_AND_OBSERVED_INTERVAL",
        "BINGX_DEPTH_TS_IS_MESSAGE_CONSTRUCTION_NOT_MATCHING_ENGINE",
    ]
    if reasons:
        s.rejection_codes = list(dict.fromkeys(reasons))
        s.stage = "BLOCKED"
        return s
    s.max_symmetric_qty_base = str(
        min(sum(q for _, q in levels) for levels in (ba.bids, ba.asks, bb.bids, bb.asks))
    )
    step = common_step(a.step * a.multiplier, b.step * b.multiplier)
    qty = (cfg.size / max(qa.ask, qb.bid) / step).to_integral_value(rounding=ROUND_FLOOR) * step
    if qty <= 0 or qty < max(a.minimum * a.multiplier, b.minimum * b.multiplier):
        reasons.append(Reason.MINIMUM)
    else:
        buy, sell = vwap(ba.asks, qty), vwap(bb.bids, qty)
        exit_long, exit_short = vwap(ba.bids, qty), vwap(bb.asks, qty)
        if None in (buy, sell, exit_long, exit_short):
            reasons.append(Reason.DEPTH)
        elif qty * max(buy, sell) > cfg.size:
            reasons.append(Reason.SIZE)
        elif qty * buy < a.min_notional or qty * sell < b.min_notional:
            reasons.append(Reason.MINIMUM)
        else:
            opening = qty * (buy * a.taker_fee + sell * b.taker_fee)
            closing = qty * (exit_long * a.taker_fee + exit_short * b.taker_fee)

            def count(f):
                return 0 if f.next_ms > horizon_ms else 1 + (horizon_ms - f.next_ms) // f.interval_ms

            funding = qty * (-buy * fa.rate * count(fa) + sell * fb.rate * count(fb))
            # Future common exit price is unknown: close-fee estimate uses current executable prices.
            scenario = qty * (sell - buy - buy * cfg.target_basis_pct / 100) - opening - closing + funding
            scenario -= cfg.slippage_reserve
            immediate = qty * (exit_long - buy + sell - exit_short) - opening - closing
            s.qty_base, s.buy_vwap, s.sell_vwap = map(str, (qty, buy, sell))
            s.opening_fees_usd, s.estimated_closing_fees_usd = str(opening), str(closing)
            s.funding_expected_usd = str(funding)
            s.immediate_round_trip_net_usd = str(immediate)
            s.scenario_net_at_target_basis_usd = str(scenario)
            if scenario < cfg.min_net:
                reasons.append(Reason.NET)
    s.stage = "BLOCKED" if reasons else "VERIFIED"
    return s
