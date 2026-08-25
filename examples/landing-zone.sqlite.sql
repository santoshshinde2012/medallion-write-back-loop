-- Portable (SQLite) version of the receiving desk — runs anywhere, no Databricks needed.
-- Verified with: sqlite3 :memory: < examples/landing-zone.sqlite.sql
--
-- This is the same shape the Python demo builds in src/medallion_write_back/repository.py.
-- The Databricks-flavoured original is examples/landing-zone.sql.

CREATE TABLE IF NOT EXISTS bronze_agent_writes (
  write_id      TEXT    NOT NULL PRIMARY KEY,  -- idempotency key (agent-generated ULID)
  agent_id      TEXT    NOT NULL,              -- service principal of the writing agent
  ts            TEXT    NOT NULL DEFAULT (datetime('now')),
  target_table  TEXT    NOT NULL,              -- e.g. 'silver_customers'
  target_key    TEXT    NOT NULL,              -- e.g. 'ACME-001'
  column_name   TEXT    NOT NULL,              -- the column being corrected
  old_value     TEXT,                          -- what the agent read (fresh-read check)
  new_value     TEXT    NOT NULL,              -- what the agent proposes
  evidence_ref  TEXT    NOT NULL,              -- ticket/row/file the claim cites
  status        TEXT    NOT NULL DEFAULT 'pending'  -- pending | promoted | held | rejected
);

-- Versioned corrections: the old value is superseded, never overwritten.
CREATE TABLE IF NOT EXISTS silver_customer_corrections (
  correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  write_id      TEXT    NOT NULL,
  customer_id   TEXT    NOT NULL,
  column_name   TEXT    NOT NULL,
  old_value     TEXT,
  new_value     TEXT    NOT NULL,
  agent_id      TEXT    NOT NULL,
  evidence_ref  TEXT    NOT NULL,
  active        INTEGER NOT NULL DEFAULT 1
);

-- Gold rebuilds as the base value overlaid by the latest ACTIVE correction.
-- Rollback is one statement:  UPDATE silver_customer_corrections SET active = 0 WHERE write_id = ?;
