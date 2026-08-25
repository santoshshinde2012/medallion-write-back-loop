"""Orchestration only: run each path on its own fresh stand-in lakehouse."""

from __future__ import annotations

from .models import AgentWrite, PathOutcome
from .protocols import GoldRepository, WritePathStrategy


class WritePathComparisonService:
    """Applies the same agent write through every strategy, each on a clean copy."""

    def __init__(self, repository: GoldRepository, paths: list[WritePathStrategy]) -> None:
        self._repository = repository
        self._paths = paths

    def run(self, write: AgentWrite) -> list[PathOutcome]:
        outcomes: list[PathOutcome] = []
        for path in self._paths:
            conn = self._repository.connect_and_seed()
            try:
                outcomes.append(path.apply(conn, write))
            finally:
                conn.close()
        return outcomes
