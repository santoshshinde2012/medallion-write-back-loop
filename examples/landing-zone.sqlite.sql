-- Portable (SQLite) version of the receiving desk — runs anywhere, no Databricks needed.
-- Verified with: sqlite3 :memory: < landing-zone.sqlite.sql
-- The Databricks-flavoured original is landing-zone.sql; this is the same shape the demo builds.

CREATE TABLE IF NOT EXISTS gold_customers (
  c_custkey     INTEGER PRIMARY KEY,
  c_name        TEXT    NOT NULL,          -- TPC-H format: Customer#000412445
  c_mktsegment  TEXT    NOT NULL,          -- AUTOMOBILE | BUILDING | FURNITURE | HOUSEHOLD | MACHINERY
  c_acctbal     REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS bronze_agent_writes (
  write_id      TEXT    NOT NULL PRIMARY KEY,  -- replaying it is a no-op
  agent_id      TEXT    NOT NULL,
  ts            TEXT    NOT NULL DEFAULT (datetime('now')),
  c_custkey     INTEGER NOT NULL,
  column_name   TEXT    NOT NULL,
  old_value     TEXT,
  new_value     TEXT    NOT NULL,
  evidence_ref  TEXT    NOT NULL,
  status        TEXT    NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS silver_customer_corrections (
  correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  write_id      TEXT    NOT NULL,
  c_custkey     INTEGER NOT NULL,
  column_name   TEXT    NOT NULL,
  old_value     TEXT,
  new_value     TEXT    NOT NULL,
  agent_id      TEXT    NOT NULL,
  evidence_ref  TEXT    NOT NULL,
  active        INTEGER NOT NULL DEFAULT 1
);

-- Gold as served = base row overlaid by the latest ACTIVE correction.
-- Rollback is one statement:
--   UPDATE silver_customer_corrections SET active = 0 WHERE write_id = ?;
