"""The loop: land in Bronze, validate, promote versioned, rebuild Gold — and roll back."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ..models import AgentWrite, PathOutcome, ValidationReport
from ..protocols import Validator
from ..repository import rebuild_gold_segment
from ..validators import default_contract


@dataclass(frozen=True)
class WriteBackLoopStrategy:
    """Treat the agent as a source system: append-only landing + earned trust."""

    validators: tuple[Validator, ...] = field(default_factory=default_contract)
    label: str = "Write-back loop (land -> validate -> promote versioned)"

    def apply(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome:
        # 1. Land — append-only, attributed, replayable.
        conn.execute(
            """INSERT INTO bronze_agent_writes
               (write_id, agent_id, target_table, target_key, column_name,
                old_value, new_value, evidence_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                write.write_id,
                write.agent_id,
                write.target_table,
                write.target_key,
                write.column,
                write.old_value,
                write.new_value,
                write.evidence_ref,
            ),
        )
        # 2. Validate — trust is earned, not asserted.
        report = ValidationReport(tuple(v.check(conn, write) for v in self.validators))
        status = "promoted" if report.passed else "held"
        conn.execute(
            "UPDATE bronze_agent_writes SET status = ? WHERE write_id = ?",
            (status, write.write_id),
        )
        # 3. Promote — versioned correction; the old value is superseded, never overwritten.
        if report.passed:
            conn.execute(
                """INSERT INTO silver_customer_corrections
                   (write_id, customer_id, column_name, old_value, new_value,
                    agent_id, evidence_ref)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    write.write_id,
                    write.target_key,
                    write.column,
                    write.old_value,
                    write.new_value,
                    write.agent_id,
                    write.evidence_ref,
                ),
            )
        conn.commit()
        after = rebuild_gold_segment(conn, write.target_key)
        history = conn.execute(
            "SELECT COUNT(*) FROM silver_customer_corrections WHERE customer_id = ?",
            (write.target_key,),
        ).fetchone()[0]
        # 4. Roll back — one statement against the versioned history.
        conn.execute(
            "UPDATE silver_customer_corrections SET active = 0 WHERE write_id = ?",
            (write.write_id,),
        )
        conn.commit()
        restored = rebuild_gold_segment(conn, write.target_key)
        return PathOutcome(
            label=self.label,
            gold_segment_after_write=str(after),
            history_rows=int(history),
            checks_run=report.checks_run,
            can_recover_old_value=True,
            rollback_statements=1,
            gold_segment_after_rollback=restored,
        )
