"""Synthetic load only: indexed scanner, 1200 common assets, both directions."""

import asyncio
import json
import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.scanner.service import Scanner
from core.config import Config
from core.models import D, Instrument, Quote


async def run():
    scanner = Scanner(Config(min_spread_pct=D(0)))
    total = 40000
    scanner.latencies = deque(maxlen=total)
    scanner.detection_latencies = deque(maxlen=total)
    scanner.queue_lags = deque(maxlen=total)
    for i in range(1200):
        for venue in ("bybit", "bingx"):
            x = Instrument(venue, f"TEST{i}", f"TEST{i}", "USDT", "USDT", D(".01"), D(".01"), D(1), D(".01"))
            scanner.instruments[x.key] = x
            scanner.by_base[x.base].append(x)
    task = asyncio.create_task(scanner.consume())
    start = time.monotonic()
    for i in range(total):
        symbol = f"TEST{(i // 2) % 1200}"
        venue = "bybit" if i % 2 == 0 else "bingx"
        price = D(100) if venue == "bybit" else D(105)
        q = Quote(price, price + D(".1"), D(10), D(10), int(time.time() * 1000))
        await scanner.emit(venue, symbol, q, None, None, time.monotonic())
        if i % 50 == 0:
            await asyncio.sleep(0)
        while scanner.queue.qsize() > 1000:
            await asyncio.sleep(0.001)
    while scanner.metrics["quote_events"] < total:
        await asyncio.sleep(0.001)
    elapsed = time.monotonic() - start
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    report = {
        "type": "SYNTHETIC_LOAD_NOT_REAL_MARKET",
        "assets": 1200,
        "events": total,
        "seconds": elapsed,
        "events_per_second": total / elapsed,
        "status": scanner.status(),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/load.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "status"}))
    print(json.dumps({"latency": report["status"]["latency_ms"], "metrics": dict(scanner.metrics)}))


if __name__ == "__main__":
    asyncio.run(run())
