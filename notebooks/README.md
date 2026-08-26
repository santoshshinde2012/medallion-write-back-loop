# Notebooks

`write_back_loop_databricks.py` — the write-back loop against Delta tables in a Databricks
workspace, built from `samples.tpch.customer` (present in every workspace). Import it as a
notebook and run the cells in order: look at the source data, create the three tables, land a
proposed correction, validate it, promote it as a versioned row, then roll it back.

**Requirements:** Databricks Runtime 11.3 LTS+ and the `delta.feature.allowColumnDefaults` table
property (set in the notebook) for the `DEFAULT` clauses; Unity Catalog if you add the
`PRIMARY KEY` constraint from `examples/landing-zone.sql`.

It is illustrative and not executed by CI — the tested implementation is
`src/medallion_write_back/`, which runs the same loop on in-memory SQLite.

This continues the notebooks-first heritage of the previous version of this repo,
[medallion-architecture-databrics](https://github.com/santoshshinde2012/medallion-architecture-databrics).
