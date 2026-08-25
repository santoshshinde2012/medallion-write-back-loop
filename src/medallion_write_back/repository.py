"""Stand-in lakehouse: three tables in SQLite (in-memory by default)."""

from __future__ import annotations

import sqlite3

SEED_CUSTOMERS = [
    ("ACME-001", "ACME Corp", "SMB", 480),
    ("GLOBEX-002", "Globex Ltd", "mid-market", 130),
    ("INITECH-003", "Initech LLC", "SMB", 45),
]


class SqliteGoldRepository:
    """Creates gold.customers, bronze.agent_writes and silver.customer_corrections."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or ":memory:"

    def connect_and_seed(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.executescript(
            """
            CREATE TABLE gold_customers (
              customer_id TEXT PRIMARY KEY,
              name        TEXT NOT NULL,
              segment     TEXT NOT NULL,
              seats       INTEGER NOT NULL
            );
            CREATE TABLE bronze_agent_writes (
              write_id     TEXT PRIMARY KEY,
              agent_id     TEXT NOT NULL,
              ts           TEXT NOT NULL DEFAULT (datetime('now')),
              target_table TEXT NOT NULL,
              target_key   TEXT NOT NULL,
              column_name  TEXT NOT NULL,
              old_value    TEXT,
              new_value    TEXT NOT NULL,
              evidence_ref TEXT NOT NULL,
              status       TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE silver_customer_corrections (
              correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
              write_id      TEXT NOT NULL,
              customer_id   TEXT NOT NULL,
              column_name   TEXT NOT NULL,
              old_value     TEXT,
              new_value     TEXT NOT NULL,
              agent_id      TEXT NOT NULL,
              evidence_ref  TEXT NOT NULL,
              active        INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        conn.executemany("INSERT INTO gold_customers VALUES (?, ?, ?, ?)", SEED_CUSTOMERS)
        conn.commit()
        return conn


def rebuild_gold_segment(conn: sqlite3.Connection, customer_id: str) -> str:
    """Gold = base value overlaid by the latest ACTIVE correction (the loop's rebuild)."""
    row = conn.execute(
        """
        SELECT COALESCE(
          (SELECT new_value FROM silver_customer_corrections
            WHERE customer_id = ? AND column_name = 'segment' AND active = 1
            ORDER BY correction_id DESC LIMIT 1),
          (SELECT segment FROM gold_customers WHERE customer_id = ?)
        )
        """,
        (customer_id, customer_id),
    ).fetchone()
    return str(row[0])
