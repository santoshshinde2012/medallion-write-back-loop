"""Composition root — the walk-through from the article, run end to end."""

from __future__ import annotations

import sys

from .comparison_service import WritePathComparisonService
from .models import AgentWrite
from .render import render_text
from .repository import SqliteGoldRepository
from .strategies.in_place import InPlaceUpdateStrategy
from .strategies.write_back_loop import WriteBackLoopStrategy

# A segment agent reads Gold, compares it with the account\'s own order history,
# and proposes a correction citing the query that shows the contradiction.
SEGMENT_CORRECTION = AgentWrite(
    write_id="w-2026-08-26-0001",
    agent_id="segment-agent",
    c_custkey=412_445,
    old_mktsegment="FURNITURE",
    new_mktsegment="BUILDING",
    evidence_ref="query:orders_by_part_category#c_custkey=412445",
)


def main() -> int:
    service = WritePathComparisonService(
        repository=SqliteGoldRepository(),
        paths=[InPlaceUpdateStrategy(), WriteBackLoopStrategy()],
    )
    outcomes = service.run(SEGMENT_CORRECTION)
    print(render_text(outcomes))
    in_place, loop = outcomes
    ok = (
        loop.checks_run == 3
        and loop.gold_segment_after_write == "BUILDING"
        and loop.gold_segment_after_rollback == "FURNITURE"
        and loop.rollback_statements == 1
        and not in_place.can_recover_old_value
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
