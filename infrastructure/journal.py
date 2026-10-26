import asyncio
import json
import uuid
from collections import deque


class Journal:
    def __init__(self, dsn=None, capacity=5000):
        self.dsn, self.pool = dsn, None
        self.queue = asyncio.Queue(capacity)
        self.recent = deque(maxlen=500)
        self.written = self.dropped = self.failures = 0

    async def connect(self):
        if self.dsn:
            import asyncpg

            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=2, command_timeout=10)
            async with self.pool.acquire() as conn:
                await conn.execute("""CREATE TABLE IF NOT EXISTS signal_events (
                    event_id UUID PRIMARY KEY, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    signal_id TEXT NOT NULL, payload JSONB NOT NULL);
                    CREATE INDEX IF NOT EXISTS signal_time_idx ON signal_events(observed_at);
                    CREATE TABLE IF NOT EXISTS scanner_settings (
                    key TEXT PRIMARY KEY, value JSONB NOT NULL);""")

    def append(self, payload):
        event = (uuid.uuid4(), payload["id"], json.dumps(payload))
        self.recent.append(payload)
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1

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
                    batch.clear()
                except Exception:
                    self.failures += 1
            if stop.is_set() and batch and self.failures:
                # Shutdown must report unsaved records rather than hang indefinitely.
                break
            await asyncio.sleep(0.5)

    async def history(self, limit=50):
        if self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT payload FROM signal_events ORDER BY observed_at DESC LIMIT $1", min(limit, 200)
                )
            return [json.loads(r["payload"]) for r in rows]
        return list(self.recent)[-limit:][::-1]

    async def close(self):
        if self.pool:
            await self.pool.close()
