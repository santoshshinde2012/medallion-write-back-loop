# Changelog

## 1.0.0 — 2026-08-26

The article is live: **[Medallion Architecture Has a Write-Back Problem](https://medium.com/@santosh-shinde/medallion-architecture-has-a-write-back-problem-525d088eeb0f)**. This release marks the code that ships with it.

- Rebuilt on the TPC-H customer shape (`samples.tpch.customer`, present in every Databricks
  workspace), so the column names in the demo are the ones a reader sees in their own workspace
- Correctness: the fresh-read check now compares against the value Gold *serves* (base row
  overlaid by active corrections); landing is idempotent, so replaying a `write_id` is a no-op;
  receipts are derived rather than asserted, so a held write no longer reports a rollback that
  never happened; an empty validator list fails closed; an unknown customer fails with a named
  error instead of a `TypeError`
- Rollback moved from the strategy into the orchestrator
- Tests 8 → 15, covering replay, held writes, stale reads after a prior correction, fail-closed
  contract and unknown customers
- Databricks notebook rebuilt against `samples.tpch.customer`, cells ordered and self-consistent
- Docs: LICENSE corrected to MIT (it was Apache-2.0 while the README and package metadata both
  said MIT), every back-link now resolves, and `pip install` shows a virtual environment first
  (a system Python on macOS/Homebrew, Debian or Fedora refuses a bare install under PEP 668)

## 0.1.0 — 2026-08-25

First public release: the runnable companion to the article, and the engineered next version of
[medallion-architecture-databrics](https://github.com/santoshshinde2012/medallion-architecture-databrics)
(the 2025 notebooks) — same medallion, new direction: agents as *writers*.

- Zero-dependency demo (`./run_demo.sh` / `medallion-write-back`): one proposed correction traced
  through an in-place UPDATE vs the write-back loop (land → validate → promote versioned → roll back)
- Three-check write contract (shape / authority / evidence) with a YAML twin in `examples/`
- ruff + mypy --strict clean; CI on Python 3.10–3.13 plus a packaging job
