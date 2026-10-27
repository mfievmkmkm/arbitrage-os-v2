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
    async with recovered.pool.acquire() as conn:
        assert await conn.fetchval("SELECT max(version) FROM scanner_schema_versions") == 1
        assert await conn.fetchval("SELECT count(*) FROM scanner_schema_versions WHERE version=1") == 1
        assert await conn.fetchval("SELECT to_regclass('signal_events')") is not None
    assert any(r["id"] == "integration-restart" for r in await recovered.history())
    assert all(r["id"] == "integration-restart" for r in await recovered.history(200, "integration-restart"))
    assert await recovered.history(200, "non-existent-health-probe") == []
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
