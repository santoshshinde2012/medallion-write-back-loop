-- bronze.agent_writes: the receiving desk for agent-proposed changes (017 walk-through)
-- Append-only. Agents INSERT here and nowhere else. Promotion is a separate, governed job.
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
);
-- Promotion writes a VERSIONED correction into Silver (supersede, never overwrite):
--   INSERT INTO silver.customer_corrections
--   SELECT write_id, target_key, 'segment', old_value, new_value, agent_id, evidence_ref, ts
--   FROM bronze.agent_writes WHERE status = 'promoted';
-- Rollback is one statement against the versioned history — that is the point.
