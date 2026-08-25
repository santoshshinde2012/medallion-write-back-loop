# Changelog

## 0.1.0 — 2026-08-25

First release: the runnable companion to the series article **The Write-Back Problem: What
Agents Add to Your Lakehouse, and Where It Should Land** (link will switch to the published
Medium URL on publication; draft lives in the
[blogs repo](https://github.com/santoshshinde2012/blogs/tree/main/articles/017-medallion-write-path)).

The engineered next version of
[medallion-architecture-databrics](https://github.com/santoshshinde2012/medallion-architecture-databrics)
(the 2025 notebooks): same medallion, new direction — agents as *writers*.

- Zero-dependency demo (`./run_demo.sh` / `medallion-write-back`): the ACME correction traced
  through an in-place UPDATE vs the write-back loop (land -> validate -> promote versioned -> roll back)
- Three-check write contract (shape / authority / evidence) with a YAML twin in `examples/`
- 8 tests locking the article's numbers; ruff + mypy --strict clean; CI on Python 3.10-3.13
