"""The wrong way: the agent UPDATEs Gold directly."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..models import AgentWrite, PathOutcome


@dataclass(frozen=True)
class InPlaceUpdateStrategy:
    """No landing zone, no checks, no history — and nothing to roll back to."""

    label: str = "In-place UPDATE against Gold (no loop)"

    def apply(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome:
        conn.execute(
            "UPDATE gold_customers SET segment = ? WHERE customer_id = ?",
            (write.new_value, write.target_key),
        )
        conn.commit()
        after = conn.execute(
            "SELECT segment FROM gold_customers WHERE customer_id = ?",
            (write.target_key,),
        ).fetchone()[0]
        history = conn.execute(
            "SELECT COUNT(*) FROM silver_customer_corrections WHERE customer_id = ?",
            (write.target_key,),
        ).fetchone()[0]
        return PathOutcome(
            label=self.label,
            gold_segment_after_write=str(after),
            history_rows=int(history),
            checks_run=0,
            can_recover_old_value=False,  # the old value was overwritten, not superseded
            rollback_statements=None,  # there is nothing recorded to roll back TO
            gold_segment_after_rollback=None,
        )
