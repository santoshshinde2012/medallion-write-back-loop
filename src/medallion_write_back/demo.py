"""Composition root — the ACME correction from the article, run end to end."""

from __future__ import annotations

import sys

from .comparison_service import WritePathComparisonService
from .models import AgentWrite
from .render import render_text
from .repository import SqliteGoldRepository
from .strategies.in_place import InPlaceUpdateStrategy
from .strategies.write_back_loop import WriteBackLoopStrategy

ACME_CORRECTION = AgentWrite(
    write_id="w-5203-001",
    agent_id="support-agent",
    target_table="gold_customers",
    target_key="ACME-001",
    column="segment",
    old_value="SMB",
    new_value="enterprise",
    evidence_ref="ticket:5203",
)


def main() -> int:
    service = WritePathComparisonService(
        repository=SqliteGoldRepository(),
        paths=[InPlaceUpdateStrategy(), WriteBackLoopStrategy()],
    )
    outcomes = service.run(ACME_CORRECTION)
    print(render_text(outcomes))
    in_place, loop = outcomes
    ok = (
        loop.checks_run == 3
        and loop.gold_segment_after_write == "enterprise"
        and loop.gold_segment_after_rollback == "SMB"
        and not in_place.can_recover_old_value
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
