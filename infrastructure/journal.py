import asyncio
import json
import os
import time
import uuid
from collections import deque


class Journal:
    def __init__(self, dsn=None, capacity=5000):
        self.dsn, self.pool = dsn, None
        self.queue = asyncio.Queue(capacity)
        self.recent = deque(maxlen=500)
        self.written = self.dropped = self.failures = 0
        self.last_write_error = None
        self.fatal_error = None
        self.stop = None
        self.storage = {"state": "NOT_MEASURED"}

    async def monitor_storage(self, stop):
        previous = None
        while not stop.is_set():
            if self.pool:
                try:
                    async with self.pool.acquire() as conn:
                        size = await conn.fetchval("SELECT pg_database_size(current_database())")
                        table = await conn.fetchval("SELECT pg_total_relation_size('signal_events')")
                    now = time.monotonic()
                    capacity = int(os.getenv("POSTGRES_VOLUME_MB", "0")) * 1000000
                    ratio = size / capacity if capacity else None
                    self.storage = {
                        "database_bytes": size,
                        "signal_events_bytes": table,
                        "declared_volume_bytes": capacity or None,
                        "state": "CRITICAL"
                        if ratio and ratio >= 0.85
                        else ("WARNING" if ratio and ratio >= 0.7 else "MEASURED"),
                        "sampled_at_ms": int(time.time() * 1000),
                        "meaning": "Database bytes only; excludes WAL/other volume files. Not free disk space.",
                        "growth_bytes_per_second": max(0, (size - previous[0]) / (now - previous[1]))
                        if previous
                        else None,
                    }
                    previous = size, now
                except Exception as exc:
                    self.storage = {
                        **self.storage,
                        "state": "MEASUREMENT_FAILED",
                        "error": type(exc).__name__,
                    }
            try:
                await asyncio.wait_for(stop.wait(), 60)
            except TimeoutError:
                pass

    async def connect(self):
        if self.dsn:
            import asyncpg

            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=2, command_timeout=10)
            try:
                async with self.pool.acquire() as conn, conn.transaction():
                    await conn.execute("SELECT pg_advisory_xact_lock(743291001)")
                    await conn.execute("""CREATE TABLE IF NOT EXISTS scanner_schema_versions (
                        version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());""")
                    version = await conn.fetchval("SELECT COALESCE(MAX(version), 0) FROM scanner_schema_versions")
                    if version > 1:
                        raise RuntimeError("database schema is newer than this scanner")
                    await conn.execute("""CREATE TABLE IF NOT EXISTS signal_events (
                    event_id UUID PRIMARY KEY, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    signal_id TEXT NOT NULL, payload JSONB NOT NULL);
                    CREATE INDEX IF NOT EXISTS signal_time_idx ON signal_events(observed_at);
                    CREATE INDEX IF NOT EXISTS signal_id_time_idx ON signal_events(signal_id, observed_at);
                    CREATE TABLE IF NOT EXISTS scanner_settings (
                    key TEXT PRIMARY KEY, value JSONB NOT NULL);""")
                    await conn.execute("INSERT INTO scanner_schema_versions(version) VALUES(1) ON CONFLICT DO NOTHING")
                    for name in ("signal_events", "scanner_settings", "signal_time_idx", "signal_id_time_idx"):
                        if not await conn.fetchval("SELECT to_regclass($1)", name):
                            raise RuntimeError(f"missing database object: {name}")
                    probe_id = uuid.uuid4()
                    await conn.execute(
                        "INSERT INTO signal_events(event_id,signal_id,payload) VALUES($1,$2,$3)",
                        probe_id, "INFRA:schema-probe", '{"id":"INFRA:schema-probe"}',
                    )
                    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM signal_events WHERE event_id=$1)", probe_id):
                        raise RuntimeError("journal probe was not readable")
            except BaseException:
                await self.pool.close()
                self.pool = None
                raise

    def append(self, payload):
        serialized = json.dumps(payload, default=str)
        event = (uuid.uuid4(), payload["id"], serialized)
        self.recent.append(json.loads(serialized))
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1
            self.fail_closed("JOURNAL_QUEUE_FULL")

    def fail_closed(self, reason):
        self.fatal_error = self.fatal_error or reason
        if self.stop is not None:
            self.stop.set()

    async def run(self, stop):
        batch = []
        while not stop.is_set() or not self.queue.empty() or batch:
            while len(batch) < 200:
                try:
                    batch.append(self.queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            if batch:
                try:
                    if self.pool:
                        async with self.pool.acquire() as conn:
                            await conn.executemany(
                                "INSERT INTO signal_events(event_id,signal_id,payload) "
                                "VALUES($1,$2,$3) ON CONFLICT DO NOTHING",
                                batch,
                            )
                    self.written += len(batch)
                    self.last_write_error = None
                    batch.clear()
                except Exception as exc:
                    self.failures += 1
                    self.last_write_error = type(exc).__name__
                    self.fail_closed("JOURNAL_WRITE_FAILED")
            if stop.is_set() and batch and self.failures:
                # Shutdown must report unsaved records rather than hang indefinitely.
                break
            await asyncio.sleep(0.5)

    async def history(self, limit=50, signal_id=None):
        limit = min(200, max(1, limit))
        if self.pool:
            async with self.pool.acquire() as conn:
                if signal_id:
                    rows = await conn.fetch(
                        "SELECT payload FROM signal_events WHERE signal_id=$1 "
                        "ORDER BY observed_at DESC LIMIT $2",
                        signal_id,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT payload FROM signal_events ORDER BY observed_at DESC LIMIT $1",
                        limit,
                    )
            return [json.loads(r["payload"]) for r in rows]
        rows = [r for r in self.recent if not signal_id or r["id"] == signal_id]
        return rows[-limit:][::-1]

    async def close(self):
        if self.pool:
            await self.pool.close()
