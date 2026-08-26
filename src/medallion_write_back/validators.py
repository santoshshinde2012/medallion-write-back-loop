"""The write contract\'s three checks — the YAML twin lives in ../examples/."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .models import AgentWrite, CheckResult
from .repository import VALID_SEGMENTS, rebuild_gold_segment

AUTHORIZED_PROPOSERS = ("segment-agent",)


@dataclass(frozen=True)
class ShapeValidator:
    """The proposed value must be one of TPC-H\'s five market segments."""

    name: str = "shape"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        ok = write.new_mktsegment in VALID_SEGMENTS
        return CheckResult(self.name, ok, f"new_value={write.new_mktsegment!r}")


@dataclass(frozen=True)
class AuthorityValidator:
    """This agent may propose segment changes — never apply them."""

    name: str = "authority"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        ok = write.agent_id in AUTHORIZED_PROPOSERS
        detail = f"agent_id={write.agent_id!r} (authority: propose)"
        return CheckResult(self.name, ok, detail)


@dataclass(frozen=True)
class EvidenceValidator:
    """The claim must cite a queryable source and match the Gold the loop actually serves.

    The fresh read compares against `rebuild_gold_segment` — the base row overlaid by any
    active correction — not the raw base row. Comparing against the base would let a write
    built on a stale read pass after an earlier correction had already moved the value.
    """

    name: str = "evidence"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        cites = bool(write.evidence_ref.strip())
        served = rebuild_gold_segment(conn, write.c_custkey)
        if served is None:
            return CheckResult(self.name, False, f"c_custkey={write.c_custkey} not found in Gold")
        fresh = served == write.old_mktsegment
        detail = f"evidence_ref={write.evidence_ref!r}, fresh_read={fresh} (Gold serves {served!r})"
        return CheckResult(self.name, cites and fresh, detail)


def default_contract() -> tuple[ShapeValidator, AuthorityValidator, EvidenceValidator]:
    return (ShapeValidator(), AuthorityValidator(), EvidenceValidator())
