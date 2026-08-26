"""The wrong way: the agent UPDATEs Gold directly."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..models import AgentWrite, PathOutcome


class CustomerNotFoundError(LookupError):
    """Raised when a write targets a customer that Gold does not hold."""


@dataclass(frozen=True)
class InPlaceUpdateStrategy:
    """No landing zone, no checks, no history — and nothing to roll back to."""

    label: str = "In-place UPDATE against Gold (no loop)"

    def apply(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome:
        cur = conn.execute(
            "UPDATE gold_customers SET c_mktsegment = ? WHERE c_custkey = ?",
            (write.new_mktsegment, write.c_custkey),
        )
        if cur.rowcount == 0:
            raise CustomerNotFoundError(f"c_custkey={write.c_custkey} is not in gold_customers")
        conn.commit()
        after = conn.execute(
            "SELECT c_mktsegment FROM gold_customers WHERE c_custkey = ?", (write.c_custkey,)
        ).fetchone()[0]
        history = conn.execute(
            "SELECT COUNT(*) FROM silver_customer_corrections WHERE c_custkey = ?",
            (write.c_custkey,),
        ).fetchone()[0]
        return PathOutcome(
            label=self.label,
            gold_segment_after_write=str(after),
            history_rows=int(history),
            checks_run=0,
            can_recover_old_value=False,  # the old value was overwritten, not superseded
            rollback_statements=None,  # nothing was recorded to roll back TO
            gold_segment_after_rollback=None,
            status="applied",
        )
