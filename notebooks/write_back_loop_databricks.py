# Databricks notebook source
# MAGIC %md
# MAGIC # The Write-Back Loop on Databricks
# MAGIC
# MAGIC The same loop the Python demo proves, against Delta tables built from the sample data
# MAGIC every workspace already has: `samples.tpch.customer`.
# MAGIC
# MAGIC Land in `bronze_agent_writes` → validate (shape / authority / evidence) → promote a
# MAGIC **versioned** correction → rebuild Gold → roll back with one statement.
# MAGIC
# MAGIC **Requirements:** Databricks Runtime 11.3 LTS+ for column `DEFAULT` values, and the
# MAGIC `delta.feature.allowColumnDefaults` table property (set below) — without it the CREATE
# MAGIC fails with `[WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED]`. Run the cells in order.

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Look at the source data first. This table exists in every Databricks workspace.
# MAGIC SELECT c_custkey, c_name, c_mktsegment, c_acctbal
# MAGIC FROM samples.tpch.customer
# MAGIC LIMIT 5;

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS demo_write_back;
# MAGIC USE demo_write_back;
# MAGIC
# MAGIC -- Gold: a small slice of the sample, so the notebook runs in seconds.
# MAGIC CREATE OR REPLACE TABLE gold_customers AS
# MAGIC SELECT c_custkey, c_name, c_mktsegment, c_acctbal
# MAGIC FROM samples.tpch.customer
# MAGIC WHERE c_custkey BETWEEN 412440 AND 412450;
# MAGIC
# MAGIC -- The receiving desk. Append-only in content: only `status` moves.
# MAGIC CREATE OR REPLACE TABLE bronze_agent_writes (
# MAGIC   write_id STRING, agent_id STRING, ts TIMESTAMP,
# MAGIC   c_custkey BIGINT, column_name STRING,
# MAGIC   old_value STRING, new_value STRING, evidence_ref STRING,
# MAGIC   status STRING DEFAULT 'pending')
# MAGIC TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');
# MAGIC
# MAGIC -- Versioned corrections: the old value is superseded, never overwritten.
# MAGIC CREATE OR REPLACE TABLE silver_customer_corrections (
# MAGIC   correction_id BIGINT GENERATED ALWAYS AS IDENTITY,
# MAGIC   write_id STRING, c_custkey BIGINT, column_name STRING,
# MAGIC   old_value STRING, new_value STRING, agent_id STRING, evidence_ref STRING,
# MAGIC   active BOOLEAN DEFAULT true)
# MAGIC TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported');

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. LAND — the agent proposes; it never touches Silver or Gold directly
# MAGIC
# MAGIC Pick a customer that exists in the slice above and use its real current segment as
# MAGIC `old_value`, so the fresh-read check has something true to compare against.

# COMMAND ----------
# MAGIC %sql
# MAGIC INSERT INTO bronze_agent_writes
# MAGIC   (write_id, agent_id, ts, c_custkey, column_name, old_value, new_value, evidence_ref, status)
# MAGIC SELECT 'w-2026-08-26-0001', 'segment-agent', current_timestamp(),
# MAGIC        c_custkey, 'c_mktsegment', c_mktsegment, 'BUILDING',
# MAGIC        'query:orders_by_part_category', 'pending'
# MAGIC FROM gold_customers
# MAGIC ORDER BY c_custkey
# MAGIC LIMIT 1;
# MAGIC
# MAGIC SELECT * FROM bronze_agent_writes;

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. VALIDATE — shape, authority, evidence (including the fresh read)

# COMMAND ----------
# MAGIC %sql
# MAGIC MERGE INTO bronze_agent_writes AS w
# MAGIC USING (SELECT c_custkey, c_mktsegment FROM gold_customers) AS g
# MAGIC   ON w.c_custkey = g.c_custkey AND w.status = 'pending'
# MAGIC WHEN MATCHED THEN UPDATE SET w.status = CASE WHEN
# MAGIC     w.new_value IN ('AUTOMOBILE','BUILDING','FURNITURE','HOUSEHOLD','MACHINERY')  -- shape
# MAGIC     AND w.agent_id IN ('segment-agent')                                           -- authority
# MAGIC     AND w.evidence_ref IS NOT NULL AND length(trim(w.evidence_ref)) > 0           -- evidence
# MAGIC     AND w.old_value = g.c_mktsegment                                              -- fresh read
# MAGIC   THEN 'promoted' ELSE 'held' END;
# MAGIC
# MAGIC SELECT write_id, c_custkey, old_value, new_value, status FROM bronze_agent_writes;

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. PROMOTE — a versioned correction, and Gold rebuilt as a view

# COMMAND ----------
# MAGIC %sql
# MAGIC INSERT INTO silver_customer_corrections
# MAGIC   (write_id, c_custkey, column_name, old_value, new_value, agent_id, evidence_ref, active)
# MAGIC SELECT w.write_id, w.c_custkey, w.column_name, w.old_value, w.new_value,
# MAGIC        w.agent_id, w.evidence_ref, true
# MAGIC FROM bronze_agent_writes w
# MAGIC LEFT ANTI JOIN silver_customer_corrections c ON w.write_id = c.write_id
# MAGIC WHERE w.status = 'promoted';
# MAGIC
# MAGIC CREATE OR REPLACE VIEW gold_customers_current AS
# MAGIC SELECT g.c_custkey, g.c_name,
# MAGIC        coalesce(x.new_value, g.c_mktsegment) AS c_mktsegment, g.c_acctbal
# MAGIC FROM gold_customers g
# MAGIC LEFT JOIN (SELECT c_custkey, max_by(new_value, correction_id) AS new_value
# MAGIC              FROM silver_customer_corrections
# MAGIC             WHERE column_name = 'c_mktsegment' AND active
# MAGIC             GROUP BY c_custkey) x
# MAGIC   ON g.c_custkey = x.c_custkey;
# MAGIC
# MAGIC SELECT * FROM gold_customers_current ORDER BY c_custkey LIMIT 3;  -- the correction is live

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. ROLL BACK — one statement against the versioned history

# COMMAND ----------
# MAGIC %sql
# MAGIC UPDATE silver_customer_corrections SET active = false
# MAGIC  WHERE write_id = 'w-2026-08-26-0001';
# MAGIC
# MAGIC SELECT * FROM gold_customers_current ORDER BY c_custkey LIMIT 3;  -- back to the original
