"""Public-only network evidence. Never rotates hosts or changes proxies to evade access controls."""

import asyncio
import hashlib
import json
import ssl
import time
import urllib.request
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout, ClientWSTimeout


def certificate_issuer():
    try:
        with urllib.request.urlopen("https://api.bybit.com/v5/market/time", timeout=12) as r:
            cert = r.fp.raw._sock.getpeercert()
            return [dict(group) for group in cert.get("issuer", ())]
    except (OSError, ssl.SSLError) as exc:
        return {"error": type(exc).__name__}


async def run():
    rows = []
    async with ClientSession(trust_env=True, timeout=ClientTimeout(total=15, connect=10)) as session:
        for url in (
            "https://api.bybit.com/v5/market/time",
            "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000",
            "https://api.bybit.com/v5/not-a-real-endpoint",
            "https://open-api.bingx.com/openApi/swap/v2/server/time",
        ):
            try:
                async with session.get(url) as response:
                    body = await response.content.read(4096)
                    rows.append(
                        {
                            "url": url,
                            "status": response.status,
                            "content_type": response.headers.get("Content-Type"),
                            "server": response.headers.get("Server"),
                            "sample_bytes": len(body),
                            "sample_sha256": hashlib.sha256(body).hexdigest(),
                            "preview": body[:220].decode(errors="replace"),
                        }
                    )
            except Exception as exc:
                rows.append({"url": url, "error": type(exc).__name__})
        try:
            async with session.ws_connect(
                "wss://stream.bybit.com/v5/public/linear", timeout=ClientWSTimeout(ws_receive=10, ws_close=3)
            ) as ws:
                await ws.send_json({"op": "subscribe", "args": ["tickers.BTCUSDT"]})
                message = await ws.receive()
                rows.append({"bybit_ws": message.type.name, "preview": str(message.data)[:200]})
        except Exception as exc:
            rows.append({"bybit_ws_error": type(exc).__name__, "status": getattr(exc, "status", None)})
    report = {
        "observed_at_ms": int(time.time() * 1000),
        "requests": rows,
        "bybit_tls_issuer": await asyncio.to_thread(certificate_issuer),
        "limitations": "Interception is observable; original origin-side cause needs gateway/origin logs",
    }
    path = Path("reports/network-diagnostics.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
