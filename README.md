# medallion-write-back-loop

**Where agent-written data lands in a medallion lakehouse.**

The medallion architecture was drawn with one unstated assumption: *the reader never writes.*
AI agents write — corrections, decisions, new records. This repo is the runnable answer:
**treat the agent as a source system.** Its writes land in an append-only receiving desk, earn
trust through a contract, get promoted as *versioned* corrections, and roll back with one
statement. A loop, not a ladder.

Companion code for the article **[Medallion Architecture Has a Write-Back Problem](https://medium.com/@santosh-shinde/medallion-architecture-has-a-write-back-problem-525d088eeb0f)**
(*Agents now write to your lakehouse, and nothing in Bronze, Silver, or Gold says where those
writes belong. Four kinds, four homes.*).

The engineered next version of
[medallion-architecture-databrics](https://github.com/santoshshinde2012/medallion-architecture-databrics),
the notebooks behind [Medallion Architecture: Principles and Practical Exploration](https://levelup.gitconnected.com/medallion-architecture-principles-and-practical-exploration-425834ae3bc7).

## The data is one you already have

The customer table matches Databricks' built-in sample, so nothing here is invented:

```sql
SELECT c_custkey, c_name, c_mktsegment FROM samples.tpch.customer LIMIT 5
```

Every row carries a `c_mktsegment` — AUTOMOBILE, BUILDING, FURNITURE, HOUSEHOLD, MACHINERY.
The demo's scenario: an agent reads customer 412445, sees `FURNITURE`, checks the account's order
history, and proposes `BUILDING`. Where should that proposal land?

## Quick start

Requires Python 3.10+ available as `python3` (set `PYTHON=python` if yours is named differently).
**No dependencies** — standard library only (`sqlite3`, `unittest`).

```bash
git clone https://github.com/santoshshinde2012/medallion-write-back-loop.git
cd medallion-write-back-loop
./run_demo.sh
```

Or install it. Use a virtual environment — a system Python on macOS/Homebrew, Debian or Fedora
refuses a bare `pip install` with `error: externally-managed-environment` (PEP 668):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install git+https://github.com/santoshshinde2012/medallion-write-back-loop.git
medallion-write-back
```

## Expected output

From `medallion-write-back` (`./run_demo.sh` prints the same block wrapped in `== Demo ==`, then
a `== Tests ==` footer with `Ran 15 tests` and `OK`):

```
=== The write-back problem: one proposed correction, traced twice ===
    gold_customers is the TPC-H customer shape (samples.tpch.customer)

--- In-place UPDATE against Gold (no loop) ---
  c_mktsegment Gold serves after write : BUILDING
  validation checks run                : 0
  landing-zone status                  : applied
  versioned history rows               : 0
  old value recoverable                : NO
  rollback                             : IMPOSSIBLE (nothing recorded)

--- Write-back loop (land -> validate -> promote versioned) ---
  c_mktsegment Gold serves after write : BUILDING
  validation checks run                : 3
  landing-zone status                  : promoted
  versioned history rows               : 1
  old value recoverable                : yes
  rollback                             : 1 statement -> c_mktsegment = FURNITURE
```

## What the demo proves

The same proposed correction is traced down two paths on a stand-in lakehouse (in-memory SQLite):

| | In-place UPDATE | Write-back loop |
|---|---|---|
| Validation | none | 3 checks: shape, authority, evidence |
| History | old value overwritten | versioned correction (superseded, never overwritten) |
| Rollback | impossible | one statement; Gold serves `FURNITURE` again |
| "Who changed this, and why?" | a chat log, long gone | `bronze_agent_writes`: agent id + evidence pointer |

The contract also holds the line, and each of these is a test: an invalid segment, an
unauthorized agent, missing evidence, an unknown customer, a **stale read** taken before an
earlier correction, a **replayed write** (a no-op, not a crash), and an **empty contract**
(fails closed, holds everything).

## Layout (SOLID)

```
src/medallion_write_back/
├── models.py               # frozen value objects (AgentWrite, CheckResult, PathOutcome…)
├── protocols.py            # seams: GoldRepository, Validator, WritePathStrategy
├── repository.py           # the TPC-H customer shape + the two loop tables
├── validators.py           # the 3-check write contract (YAML twin in examples/)
├── strategies/
│   ├── in_place.py         # the wrong way, traced honestly
│   └── write_back_loop.py  # land -> validate -> promote versioned
├── comparison_service.py   # orchestration only; proves the rollback
├── render.py               # the output this README quotes
└── demo.py                 # composition root
tests/                      # 15 tests: the article's receipts + the contract's promises
examples/                   # contract YAML + Databricks and portable DDL
notebooks/                  # the same loop against Delta tables built from samples.tpch
```

## Adapting it to a real platform

`examples/landing-zone.sql` is the Databricks DDL for the receiving desk (it documents its own
requirements: DBR 11.3 LTS+ and `delta.feature.allowColumnDefaults` for the `DEFAULT` clause,
Unity Catalog for the `PRIMARY KEY` constraint). `examples/landing-zone.sqlite.sql` is the
portable version. `examples/agent-write-contract.yaml` is the contract as configuration, and
`notebooks/write_back_loop_databricks.py` runs the whole loop in a workspace.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install ruff mypy
ruff check . && ruff format --check . && mypy && ./run_demo.sh
```

MIT — see [LICENSE](LICENSE).
