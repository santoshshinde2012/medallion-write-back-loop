"""Frozen value objects shared across the demo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentWrite:
    """One proposed correction from an agent — a row for bronze.agent_writes.

    Mirrors the shape of Databricks' built-in `samples.tpch.customer`, so the
    column names here are the ones a reader sees in their own workspace.
    """

    write_id: str
    agent_id: str
    c_custkey: int
    old_mktsegment: str
    new_mktsegment: str
    evidence_ref: str


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single validation check."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ValidationReport:
    """All checks run against one proposed write."""

    results: tuple[CheckResult, ...] = field(default_factory=tuple)

    @property
    def checks_run(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> bool:
        """An empty contract must never pass — a mis-wired validator list fails closed."""
        return bool(self.results) and all(r.ok for r in self.results)


@dataclass(frozen=True)
class PathOutcome:
    """What one write path left behind — the article's receipts."""

    label: str
    gold_segment_after_write: str
    history_rows: int
    checks_run: int
    can_recover_old_value: bool
    rollback_statements: int | None
    gold_segment_after_rollback: str | None
    status: str = "n/a"
