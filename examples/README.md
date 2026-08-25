# Examples — the write-back loop artifacts

| File | Appears in the article | What it shows |
|------|------------------------|---------------|
| `agent-write-contract.yaml` | Practical Walk-through (trimmed in the draft) | The validation contract: shape / authority / evidence, and `promote_versioned` on pass |
| `landing-zone.sql` | Practical Walk-through | `bronze.agent_writes` receiving-desk DDL for **Databricks SQL / Delta** |
| `landing-zone.sqlite.sql` | — | Portable version of the same tables — runs anywhere, no Databricks needed |

## Running them

**Portable (no Databricks):**

```bash
sqlite3 demo.db < examples/landing-zone.sqlite.sql
```

The Python demo in this repo builds the same shape in memory and runs the whole loop:

```bash
./run_demo.sh
```

**On Databricks:** open `examples/landing-zone.sql` and replace `bronze` with your own
`catalog.schema`. Two requirements, both called out in the file's header comment:

- Databricks Runtime **11.3 LTS or above** for column `DEFAULT` values, and the table property
  `delta.feature.allowColumnDefaults = 'supported'` (already set in the DDL). Without it the
  CREATE fails with `[WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED]`.
- The `PRIMARY KEY` constraint requires a **Unity Catalog** table. Constraints are not supported
  in `hive_metastore`, and Databricks does not enforce them — they are informational.

`notebooks/write_back_loop_databricks.py` runs the full loop (land → validate → promote →
roll back) against Delta tables in a workspace.

## A note on the numbers

The walk-through figures in the article (3 checks, 1 versioned history row, a 1-statement
rollback) are produced by the demo and locked by its tests. The 14-minute promotion lag is a
labelled synthetic stand-in for a scheduled job, not a benchmark.
