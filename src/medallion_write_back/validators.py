"""The write contract's three checks — mirrors examples/agent-write-contract.yaml."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .models import AgentWrite, CheckResult

ALLOWED_SEGMENTS = ("SMB", "mid-market", "enterprise")
AUTHORIZED_PROPOSERS = ("support-agent",)


@dataclass(frozen=True)
class ShapeValidator:
    """The proposed value must be a valid segment."""

    name: str = "shape"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        ok = write.new_value in ALLOWED_SEGMENTS
        return CheckResult(self.name, ok, f"new_value={write.new_value!r}")


@dataclass(frozen=True)
class AuthorityValidator:
    """This agent may propose segment changes — never apply them."""

    name: str = "authority"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        ok = write.agent_id in AUTHORIZED_PROPOSERS
        return CheckResult(self.name, ok, f"agent_id={write.agent_id!r} (authority: propose)")


@dataclass(frozen=True)
class EvidenceValidator:
    """The claim must cite a queryable source and match a fresh read of the target."""

    name: str = "evidence"

    def check(self, conn: sqlite3.Connection, write: AgentWrite) -> CheckResult:
        cites = bool(write.evidence_ref.strip())
        row = conn.execute(
            "SELECT segment FROM gold_customers WHERE customer_id = ?",
            (write.target_key,),
        ).fetchone()
        fresh = row is not None and str(row[0]) == write.old_value
        ok = cites and fresh
        return CheckResult(
            self.name, ok, f"evidence_ref={write.evidence_ref!r}, fresh_read={fresh}"
        )


def default_contract() -> tuple[ShapeValidator, AuthorityValidator, EvidenceValidator]:
    return (ShapeValidator(), AuthorityValidator(), EvidenceValidator())
