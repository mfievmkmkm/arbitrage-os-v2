CREATE TABLE IF NOT EXISTS signal_events (
  event_id UUID PRIMARY KEY,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  signal_id TEXT NOT NULL,
  payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS signal_time_idx ON signal_events(observed_at);
CREATE TABLE IF NOT EXISTS scanner_settings (key TEXT PRIMARY KEY, value JSONB NOT NULL);
-- Signal/audit events are not automatically deleted. Back up before archival.
