"""Orchestration only: run each path on its own fresh stand-in lakehouse."""

from __future__ import annotations

import sqlite3

from .models import AgentWrite, PathOutcome
from .protocols import GoldRepository, WritePathStrategy
from .repository import rebuild_gold_segment
from .strategies.write_back_loop import WriteBackLoopStrategy


class WritePathComparisonService:
    """Applies the same proposed correction through every strategy, each on a clean copy."""

    def __init__(self, repository: GoldRepository, paths: list[WritePathStrategy]) -> None:
        self._repository = repository
        self._paths = paths

    def run(self, write: AgentWrite) -> list[PathOutcome]:
        outcomes: list[PathOutcome] = []
        for path in self._paths:
            conn: sqlite3.Connection = self._repository.connect_and_seed()
            try:
                outcome = path.apply(conn, write)
                # The loop's promise is that a promotion is reversible; prove it here,
                # in the orchestrator, rather than inside the strategy.
                if isinstance(path, WriteBackLoopStrategy) and outcome.rollback_statements:
                    stmts = path.roll_back(conn, write.write_id)
                    restored = rebuild_gold_segment(conn, write.c_custkey)
                    outcome = PathOutcome(
                        label=outcome.label,
                        gold_segment_after_write=outcome.gold_segment_after_write,
                        history_rows=outcome.history_rows,
                        checks_run=outcome.checks_run,
                        can_recover_old_value=outcome.can_recover_old_value,
                        rollback_statements=stmts,
                        gold_segment_after_rollback=restored,
                        status=outcome.status,
                    )
                outcomes.append(outcome)
            finally:
                conn.close()
        return outcomes
