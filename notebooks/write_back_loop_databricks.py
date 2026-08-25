# Databricks notebook source
# MAGIC %md
# MAGIC # The Write-Back Loop on Databricks (illustrative)
# MAGIC The same loop the Python demo proves, expressed against Delta tables:
# MAGIC land in `bronze_agent_writes` → validate (shape / authority / evidence) →
# MAGIC promote as a **versioned** correction → rebuild Gold → roll back with one statement.
# MAGIC
# MAGIC Illustrative companion to the repo's demo — adapt catalog/schema names to your workspace.
# MAGIC Not executed by CI; the runnable, tested version is `src/medallion_write_back/`.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS demo_write_back;
# MAGIC USE demo_write_back;
# MAGIC
# MAGIC CREATE OR REPLACE TABLE gold_customers (customer_id STRING, name STRING, segment STRING, seats INT);
# MAGIC INSERT INTO gold_customers VALUES
# MAGIC   ('ACME-001', 'ACME Corp', 'SMB', 480),
# MAGIC   ('GLOBEX-002', 'Globex Ltd', 'mid-market', 130),
# MAGIC   ('INITECH-003', 'Initech LLC', 'SMB', 45);
# MAGIC
# MAGIC -- The receiving desk: append-only, attributed, replayable
# MAGIC CREATE OR REPLACE TABLE bronze_agent_writes (
# MAGIC   write_id STRING, agent_id STRING, ts TIMESTAMP,
# MAGIC   target_table STRING, target_key STRING, column_name STRING,
# MAGIC   old_value STRING, new_value STRING, evidence_ref STRING,
# MAGIC   status STRING DEFAULT 'pending');
# MAGIC
# MAGIC CREATE OR REPLACE TABLE silver_customer_corrections (
# MAGIC   correction_id BIGINT GENERATED ALWAYS AS IDENTITY,
# MAGIC   write_id STRING, customer_id STRING, column_name STRING,
# MAGIC   old_value STRING, new_value STRING, agent_id STRING, evidence_ref STRING,
# MAGIC   active BOOLEAN DEFAULT true);

# COMMAND ----------
# MAGIC %sql
# MAGIC -- 1. LAND: the agent proposes; it never touches Silver or Gold directly
# MAGIC INSERT INTO bronze_agent_writes
# MAGIC   (write_id, agent_id, ts, target_table, target_key, column_name, old_value, new_value, evidence_ref, status)
# MAGIC VALUES
# MAGIC   ('w-5203-001', 'support-agent', current_timestamp(), 'gold_customers', 'ACME-001', 'segment', 'SMB', 'enterprise', 'ticket:5203', 'pending');

# COMMAND ----------
# MAGIC %sql
# MAGIC -- 2. VALIDATE: the three-check contract (shape / authority / evidence+fresh-read) as one pass
# MAGIC UPDATE bronze_agent_writes w
# MAGIC SET status = CASE WHEN
# MAGIC     w.new_value IN ('SMB', 'mid-market', 'enterprise')                       -- shape
# MAGIC     AND w.agent_id IN ('support-agent')                                      -- authority: propose
# MAGIC     AND w.evidence_ref IS NOT NULL AND length(trim(w.evidence_ref)) > 0      -- evidence cited
# MAGIC     AND EXISTS (SELECT 1 FROM gold_customers g                               -- fresh read
# MAGIC                 WHERE g.customer_id = w.target_key AND g.segment = w.old_value)
# MAGIC   THEN 'promoted' ELSE 'held' END
# MAGIC WHERE w.status = 'pending';

# COMMAND ----------
# MAGIC %sql
# MAGIC -- 3. PROMOTE: versioned correction — the old value is superseded, never overwritten
# MAGIC INSERT INTO silver_customer_corrections
# MAGIC   (write_id, customer_id, column_name, old_value, new_value, agent_id, evidence_ref, active)
# MAGIC SELECT write_id, target_key, column_name, old_value, new_value, agent_id, evidence_ref, true
# MAGIC FROM bronze_agent_writes WHERE status = 'promoted'
# MAGIC   AND write_id NOT IN (SELECT write_id FROM silver_customer_corrections);
# MAGIC
# MAGIC -- Gold rebuild = base value overlaid by the latest active correction
# MAGIC CREATE OR REPLACE VIEW gold_customers_current AS
# MAGIC SELECT g.customer_id, g.name,
# MAGIC        coalesce(c.new_value, g.segment) AS segment, g.seats
# MAGIC FROM gold_customers g
# MAGIC LEFT JOIN (SELECT customer_id, max_by(new_value, correction_id) AS new_value
# MAGIC            FROM silver_customer_corrections
# MAGIC            WHERE column_name = 'segment' AND active GROUP BY customer_id) c
# MAGIC   ON g.customer_id = c.customer_id;
# MAGIC
# MAGIC SELECT * FROM gold_customers_current WHERE customer_id = 'ACME-001';  -- segment = enterprise

# COMMAND ----------
# MAGIC %sql
# MAGIC -- 4. ROLL BACK: one statement against the versioned history; Gold rebuilds to SMB
# MAGIC UPDATE silver_customer_corrections SET active = false WHERE write_id = 'w-5203-001';
# MAGIC SELECT * FROM gold_customers_current WHERE customer_id = 'ACME-001';  -- segment = SMB again
