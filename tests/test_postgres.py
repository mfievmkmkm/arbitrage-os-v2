import asyncio
import os

import pytest

from infrastructure.journal import Journal


@pytest.mark.asyncio
async def test_postgres_persists_after_reconnect():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not configured")
    j = Journal(dsn)
    await j.connect()
    j.append({"id": "integration-restart", "stage": "BLOCKED"})
    stop = asyncio.Event()
    stop.set()
    await j.run(stop)
    await j.close()
    recovered = Journal(dsn)
    await recovered.connect()
    assert any(r["id"] == "integration-restart" for r in await recovered.history())
    storage_stop = asyncio.Event()
    monitor = asyncio.create_task(recovered.monitor_storage(storage_stop))
    try:
        for _ in range(100):
            if recovered.storage["state"] != "NOT_MEASURED":
                break
            await asyncio.sleep(0.01)
        assert recovered.storage["database_bytes"] > 0
        assert recovered.storage["signal_events_bytes"] > 0
        assert recovered.storage["state"] == "MEASURED"
    finally:
        storage_stop.set()
        await monitor
    await recovered.close()
