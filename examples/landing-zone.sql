-- bronze.agent_writes: the receiving desk for agent-proposed changes (article 017 walk-through)
-- Append-only. Agents INSERT here and nowhere else. Promotion is a separate, governed job.
--
-- Requirements (Databricks SQL / Delta):
--   * Databricks Runtime 11.3 LTS or above for column DEFAULT values.
--   * TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported') is REQUIRED for the
--     DEFAULT clause below. Without it the CREATE fails with
--     [WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED].
--   * The PRIMARY KEY constraint needs a Unity Catalog table; constraints are not supported in
--     the hive_metastore catalog, and Databricks does not enforce them (they are informational).
--   * Replace `bronze` with your own catalog.schema qualifier.
--
-- Prefer to try this without Databricks? `examples/landing-zone.sqlite.sql` is the portable
-- version, and the Python demo in this repo runs the whole loop on in-memory SQLite.

CREATE TABLE IF NOT EXISTS bronze.agent_writes (
  write_id      STRING  NOT NULL,             -- idempotency key (agent-generated ULID)
  agent_id      STRING  NOT NULL,             -- service principal of the writing agent
  ts            TIMESTAMP NOT NULL,
  target_table  STRING  NOT NULL,             -- e.g. 'silver.customers'
  target_key    STRING  NOT NULL,             -- e.g. 'customer_id=ACME-001'
  old_value     STRING,                       -- what the agent read (fresh-read check)
  new_value     STRING  NOT NULL,             -- what the agent proposes
  evidence_ref  STRING  NOT NULL,             -- ticket/row/file the claim cites
  status        STRING  NOT NULL DEFAULT 'pending',  -- pending | promoted | held | rejected
  CONSTRAINT agent_writes_pk PRIMARY KEY (write_id)
)
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

-- Promotion writes a VERSIONED correction into Silver (supersede, never overwrite):
--   INSERT INTO silver.customer_corrections
--   SELECT write_id, target_key, 'segment', old_value, new_value, agent_id, evidence_ref, ts
--   FROM bronze.agent_writes WHERE status = 'promoted';
-- Rollback is one statement against the versioned history — that is the point.
