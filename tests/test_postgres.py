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
    await recovered.close()
