"""Read-only one-symbol protocol acceptance. Not a trade or a two-venue scanner proof."""

import asyncio
import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiohttp import ClientSession

from adapters.cex.public import stream


async def main():
    stop, metrics, health, snapshots = asyncio.Event(), Counter(), {}, []

    async def emit(venue, symbol, q, f, book, received, **kwargs):
        if book:
            snapshots.append({"symbol": symbol, **asdict(book)})
        if len(snapshots) >= 5:
            stop.set()

    async with ClientSession(trust_env=True) as session:
        task = asyncio.create_task(
            stream(session, "bingx", ["BTC-USDT"], emit, health, metrics, stop, depth=True)
        )
        try:
            await asyncio.wait_for(stop.wait(), 25)
        except TimeoutError:
            pass
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    report = {
        "observed_at_ms": int(time.time() * 1000),
        "health": health,
        "metrics": dict(metrics),
        "snapshots": snapshots,
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/depth-probe.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({"snapshots": len(snapshots), "metrics": dict(metrics), "health": health}))


if __name__ == "__main__":
    asyncio.run(main())
