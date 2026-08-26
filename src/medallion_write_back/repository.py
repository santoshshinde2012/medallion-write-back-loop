"""Stand-in lakehouse: the TPC-H customer shape in SQLite (in-memory by default).

The columns match Databricks\' built-in `samples.tpch.customer`, so the same query
you read here runs in any workspace:

    SELECT c_custkey, c_name, c_mktsegment FROM samples.tpch.customer LIMIT 5
"""

from __future__ import annotations

import sqlite3

# A handful of rows in the shape TPC-H generates (c_name is always Customer#%09d).
SEED_CUSTOMERS = [
    (412_445, "Customer#000412445", "FURNITURE", 7_284.11),
    (39_136, "Customer#000039136", "BUILDING", 2_470.90),
    (77_310, "Customer#000077310", "MACHINERY", 5_003.42),
]

VALID_SEGMENTS = ("AUTOMOBILE", "BUILDING", "FURNITURE", "HOUSEHOLD", "MACHINERY")


class SqliteGoldRepository:
    """Creates gold_customers, bronze_agent_writes and silver_customer_corrections."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or ":memory:"

    def connect_and_seed(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS gold_customers (
                  c_custkey     INTEGER PRIMARY KEY,
                  c_name        TEXT NOT NULL,
                  c_mktsegment  TEXT NOT NULL,
                  c_acctbal     REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bronze_agent_writes (
                  write_id        TEXT PRIMARY KEY,
                  agent_id        TEXT NOT NULL,
                  ts              TEXT NOT NULL DEFAULT (datetime('now')),
                  c_custkey       INTEGER NOT NULL,
                  column_name     TEXT NOT NULL,
                  old_value       TEXT,
                  new_value       TEXT NOT NULL,
                  evidence_ref    TEXT NOT NULL,
                  status          TEXT NOT NULL DEFAULT 'pending'
                );
                CREATE TABLE IF NOT EXISTS silver_customer_corrections (
                  correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  write_id      TEXT NOT NULL,
                  c_custkey     INTEGER NOT NULL,
                  column_name   TEXT NOT NULL,
                  old_value     TEXT,
                  new_value     TEXT NOT NULL,
                  agent_id      TEXT NOT NULL,
                  evidence_ref  TEXT NOT NULL,
                  active        INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            # Idempotent seed so a file-backed db can be re-opened safely.
            conn.executemany(
                "INSERT OR REPLACE INTO gold_customers VALUES (?, ?, ?, ?)", SEED_CUSTOMERS
            )
            conn.commit()
        except Exception:
            conn.close()
            raise
        return conn


def rebuild_gold_segment(conn: sqlite3.Connection, c_custkey: int) -> str | None:
    """Gold as served = base value overlaid by the latest ACTIVE correction.

    Returns None when the customer does not exist, so callers can fail explicitly.
    """
    base = conn.execute(
        "SELECT c_mktsegment FROM gold_customers WHERE c_custkey = ?", (c_custkey,)
    ).fetchone()
    if base is None:
        return None
    override = conn.execute(
        """
        SELECT new_value FROM silver_customer_corrections
         WHERE c_custkey = ? AND column_name = 'c_mktsegment' AND active = 1
         ORDER BY correction_id DESC LIMIT 1
        """,
        (c_custkey,),
    ).fetchone()
    return str(override[0]) if override else str(base[0])
