-- bronze.agent_writes: the receiving desk for agent-proposed corrections (article 017).
-- Append-only in content: a proposed value is never edited — only `status` moves from
-- 'pending' to 'promoted' or 'held'.
--
-- The customer shape matches Databricks' built-in sample, so you can try this on real data:
--   SELECT c_custkey, c_name, c_mktsegment FROM samples.tpch.customer LIMIT 5
--
-- Requirements (Databricks SQL / Delta):
--   * Databricks Runtime 11.3 LTS or above for column DEFAULT values.
--   * TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported') is REQUIRED for the
--     DEFAULT clause below. Without it the CREATE fails with
--     [WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED].
--   * The PRIMARY KEY constraint needs a Unity Catalog table; constraints are not supported in
--     the hive_metastore catalog, and Databricks does not enforce them (they are informational).
--   * Replace `bronze` and `silver` with your own catalog.schema qualifiers.
--
-- Prefer to try this with no Databricks at all? `landing-zone.sqlite.sql` is the portable
-- version, and this article's demo runs the whole loop on in-memory SQLite.

CREATE TABLE IF NOT EXISTS bronze.agent_writes (
  write_id      STRING  NOT NULL,             -- idempotency key: replaying it is a no-op
  agent_id      STRING  NOT NULL,             -- service principal of the writing agent
  ts            TIMESTAMP NOT NULL,
  c_custkey     BIGINT  NOT NULL,             -- the TPC-H customer key being corrected
  column_name   STRING  NOT NULL,             -- e.g. 'c_mktsegment'
  old_value     STRING,                       -- what Gold served when the agent read it
  new_value     STRING  NOT NULL,             -- what the agent proposes
  evidence_ref  STRING  NOT NULL,             -- the query, ticket or file the claim cites
  status        STRING  NOT NULL DEFAULT 'pending',  -- pending | promoted | held
  CONSTRAINT agent_writes_pk PRIMARY KEY (write_id)
)
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

-- Versioned corrections: the old value is superseded, never overwritten.
CREATE TABLE IF NOT EXISTS silver.customer_corrections (
  correction_id BIGINT GENERATED ALWAYS AS IDENTITY,
  write_id      STRING  NOT NULL,
  c_custkey     BIGINT  NOT NULL,
  column_name   STRING  NOT NULL,
  old_value     STRING,
  new_value     STRING  NOT NULL,
  agent_id      STRING  NOT NULL,
  evidence_ref  STRING  NOT NULL,
  active        BOOLEAN NOT NULL DEFAULT true
)
TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

-- Gold as served = the base row overlaid by the latest ACTIVE correction.
--   CREATE OR REPLACE VIEW gold.customers_current AS
--   SELECT c.c_custkey, c.c_name,
--          coalesce(x.new_value, c.c_mktsegment) AS c_mktsegment
--   FROM gold.customers c
--   LEFT JOIN (SELECT c_custkey, max_by(new_value, correction_id) AS new_value
--                FROM silver.customer_corrections
--               WHERE column_name = 'c_mktsegment' AND active
--               GROUP BY c_custkey) x  ON c.c_custkey = x.c_custkey;
--
-- Rollback is one statement against that history — that is the point:
--   UPDATE silver.customer_corrections SET active = false WHERE write_id = '...';
