# medallion-write-back-loop

**Where agent-written data lands in a medallion lakehouse.**

The medallion architecture was drawn with one unstated assumption: *the reader never writes.*
AI agents write — corrections, decisions, new records. This repo is the runnable answer:
**treat the agent as a source system.** Its writes land in an append-only receiving desk,
earn trust through a contract, get promoted as *versioned* corrections, and roll back with
one statement. A loop, not a ladder.

Companion code for the series article **The Write-Back Problem: What Agents Add to Your
Lakehouse, and Where It Should Land** ([draft & research](https://github.com/santoshshinde2012/blogs/tree/main/articles/017-medallion-write-path);
this link switches to the Medium URL on publication). The engineered next version of
[medallion-architecture-databrics](https://github.com/santoshshinde2012/medallion-architecture-databrics),
the notebooks behind [Medallion Architecture: Principles and Practical Exploration](https://levelup.gitconnected.com/medallion-architecture-principles-and-practical-exploration-425834ae3bc7) (2025).

## Quick start

Requires Python 3.10+. **No dependencies** — standard library only (`sqlite3`, `unittest`).

```bash
git clone https://github.com/santoshshinde2012/medallion-write-back-loop.git
cd medallion-write-back-loop
./run_demo.sh
```

Or install it:

```bash
pip install git+https://github.com/santoshshinde2012/medallion-write-back-loop.git
medallion-write-back
```

## Expected output (pasted from a real run)

```
=== The Write-Back Problem: one correction, traced twice ===

--- In-place UPDATE against Gold (no loop) ---
  gold.customers segment after write : enterprise
  validation checks run              : 0
  history rows (versioned)           : 0
  old value recoverable              : NO
  rollback                           : IMPOSSIBLE (nothing recorded)

--- Write-back loop (land -> validate -> promote versioned) ---
  gold.customers segment after write : enterprise
  validation checks run              : 3
  history rows (versioned)           : 1
  old value recoverable              : yes
  rollback                           : 1 statement -> segment = SMB
```

## What the demo proves

A support agent finds ACME Corp mislabelled `SMB` in `gold.customers` and proposes `enterprise`.
The same write is traced down two paths on a stand-in lakehouse (in-memory SQLite):

| | In-place UPDATE | Write-back loop |
|---|---|---|
| Validation | none | 3 checks: shape, authority, evidence |
| History | old value overwritten | versioned correction (superseded, never overwritten) |
| Rollback | impossible | one statement, Gold rebuilds to `SMB` |
| Audit answer to "who changed this and why?" | a chat log, long gone | `bronze_agent_writes`: agent id + evidence pointer |

The contract also holds the line in tests: an invalid value, an unauthorized agent, a stale
read, and missing evidence are all **held for review** — never promoted.

## Layout (SOLID)

```
src/medallion_write_back/
├── models.py               # frozen value objects (AgentWrite, CheckResult, PathOutcome…)
├── protocols.py            # seams: GoldRepository, Validator, WritePathStrategy
├── repository.py           # stand-in lakehouse: gold / bronze.agent_writes / silver corrections
├── validators.py           # the 3-check write contract (YAML twin in examples/)
├── strategies/
│   ├── in_place.py         # the wrong way, measured honestly
│   └── write_back_loop.py  # land -> validate -> promote versioned -> roll back
├── comparison_service.py   # orchestration only
├── render.py               # output the article quotes
└── demo.py                 # composition root
tests/                      # 8 tests locking the article's numbers
examples/                   # agent-write-contract.yaml + landing-zone.sql (Databricks-flavoured)
```

## Adapting it to a real platform

`examples/landing-zone.sql` is the Databricks-flavoured DDL for the receiving desk, and
`examples/agent-write-contract.yaml` is the contract as configuration. The article's
*First Steps* section is the adoption checklist: create the landing table, swap agent
permissions (INSERT on landing, no UPDATE on Silver/Gold), one contract for one column,
promotion as a scheduled job, state & memory to your operational store.

## Development

```bash
pip install ruff mypy
ruff check . && ruff format --check . && mypy && ./run_demo.sh
```

MIT — see [LICENSE](LICENSE).
