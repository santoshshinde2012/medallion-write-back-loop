"""The loop: land in Bronze, validate, promote a versioned correction, rebuild Gold."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ..models import AgentWrite, PathOutcome, ValidationReport
from ..protocols import Validator
from ..repository import rebuild_gold_segment
from ..validators import default_contract


@dataclass(frozen=True)
class WriteBackLoopStrategy:
    """Treat the agent as a source system: append-only landing, then earned trust."""

    validators: tuple[Validator, ...] = field(default_factory=default_contract)
    label: str = "Write-back loop (land -> validate -> promote versioned)"

    def apply(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome:
        # 1. LAND — append-only, attributed, replayable. A replayed write_id is a no-op,
        #    so re-running the agent cannot crash or double-post.
        cur = conn.execute(
            """INSERT INTO bronze_agent_writes
               (write_id, agent_id, c_custkey, column_name, old_value, new_value, evidence_ref)
               VALUES (?, ?, ?, 'c_mktsegment', ?, ?, ?)
               ON CONFLICT(write_id) DO NOTHING""",
            (
                write.write_id,
                write.agent_id,
                write.c_custkey,
                write.old_mktsegment,
                write.new_mktsegment,
                write.evidence_ref,
            ),
        )
        replayed = cur.rowcount == 0
        conn.commit()  # the landing row is durable before any validation runs

        if replayed:
            return self._outcome_for_existing(conn, write)

        # 2. VALIDATE — trust is earned, not asserted by the writer.
        report = ValidationReport(tuple(v.check(conn, write) for v in self.validators))
        status = "promoted" if report.passed else "held"
        conn.execute(
            "UPDATE bronze_agent_writes SET status = ? WHERE write_id = ?",
            (status, write.write_id),
        )

        # 3. PROMOTE — a versioned correction; the old value is superseded, never overwritten.
        if report.passed:
            conn.execute(
                """INSERT INTO silver_customer_corrections
                   (write_id, c_custkey, column_name, old_value, new_value, agent_id, evidence_ref)
                   VALUES (?, ?, 'c_mktsegment', ?, ?, ?, ?)""",
                (
                    write.write_id,
                    write.c_custkey,
                    write.old_mktsegment,
                    write.new_mktsegment,
                    write.agent_id,
                    write.evidence_ref,
                ),
            )
        conn.commit()
        return self._outcome(conn, write, status, report.checks_run)

    def roll_back(self, conn: sqlite3.Connection, write_id: str) -> int:
        """Deactivate a promoted correction. Returns the number of statements that changed rows."""
        cur = conn.execute(
            "UPDATE silver_customer_corrections SET active = 0 WHERE write_id = ? AND active = 1",
            (write_id,),
        )
        conn.commit()
        return 1 if cur.rowcount else 0

    def _history_rows(self, conn: sqlite3.Connection, c_custkey: int) -> int:
        row = conn.execute(
            "SELECT COUNT(*) FROM silver_customer_corrections WHERE c_custkey = ?", (c_custkey,)
        ).fetchone()
        return int(row[0])

    def _outcome(
        self, conn: sqlite3.Connection, write: AgentWrite, status: str, checks: int
    ) -> PathOutcome:
        after = rebuild_gold_segment(conn, write.c_custkey)
        promoted = status == "promoted"
        return PathOutcome(
            label=self.label,
            gold_segment_after_write=str(after),
            history_rows=self._history_rows(conn, write.c_custkey),
            checks_run=checks,
            can_recover_old_value=promoted,
            rollback_statements=1 if promoted else None,
            gold_segment_after_rollback=None,
            status=status,
        )

    def _outcome_for_existing(self, conn: sqlite3.Connection, write: AgentWrite) -> PathOutcome:
        row = conn.execute(
            "SELECT status FROM bronze_agent_writes WHERE write_id = ?", (write.write_id,)
        ).fetchone()
        status = str(row[0]) if row else "pending"
        return self._outcome(conn, write, status, 0)
