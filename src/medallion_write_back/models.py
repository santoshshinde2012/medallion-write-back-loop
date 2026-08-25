"""Frozen value objects shared across the demo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentWrite:
    """One proposed change from an agent — a row for bronze.agent_writes."""

    write_id: str
    agent_id: str
    target_table: str
    target_key: str
    column: str
    old_value: str
    new_value: str
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
        return all(r.ok for r in self.results)


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
