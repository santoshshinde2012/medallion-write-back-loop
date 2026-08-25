"""Lock the article's numbers: 3 checks, versioned promotion, 1-statement rollback."""

from __future__ import annotations

import unittest

from medallion_write_back.comparison_service import WritePathComparisonService
from medallion_write_back.demo import ACME_CORRECTION
from medallion_write_back.models import AgentWrite
from medallion_write_back.repository import SqliteGoldRepository
from medallion_write_back.strategies.in_place import InPlaceUpdateStrategy
from medallion_write_back.strategies.write_back_loop import WriteBackLoopStrategy


def run_paths(write: AgentWrite):
    service = WritePathComparisonService(
        repository=SqliteGoldRepository(),
        paths=[InPlaceUpdateStrategy(), WriteBackLoopStrategy()],
    )
    return service.run(write)


class TestArticleNumbers(unittest.TestCase):
    def test_loop_runs_exactly_three_checks(self) -> None:
        _, loop = run_paths(ACME_CORRECTION)
        self.assertEqual(loop.checks_run, 3)

    def test_loop_promotes_versioned_and_gold_reflects_it(self) -> None:
        _, loop = run_paths(ACME_CORRECTION)
        self.assertEqual(loop.gold_segment_after_write, "enterprise")
        self.assertEqual(loop.history_rows, 1)

    def test_loop_rollback_is_one_statement_and_restores_smb(self) -> None:
        _, loop = run_paths(ACME_CORRECTION)
        self.assertEqual(loop.rollback_statements, 1)
        self.assertEqual(loop.gold_segment_after_rollback, "SMB")

    def test_in_place_loses_the_old_value(self) -> None:
        in_place, _ = run_paths(ACME_CORRECTION)
        self.assertEqual(in_place.gold_segment_after_write, "enterprise")
        self.assertFalse(in_place.can_recover_old_value)
        self.assertIsNone(in_place.rollback_statements)
        self.assertEqual(in_place.history_rows, 0)


class TestContractRejections(unittest.TestCase):
    def _loop_only(self, write: AgentWrite):
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            return WriteBackLoopStrategy().apply(conn, write)
        finally:
            conn.close()

    def test_invalid_segment_is_held_not_promoted(self) -> None:
        bad = AgentWrite(
            "w-x1",
            "support-agent",
            "gold_customers",
            "ACME-001",
            "segment",
            "SMB",
            "galactic",
            "ticket:5203",
        )
        out = self._loop_only(bad)
        self.assertEqual(out.gold_segment_after_write, "SMB")
        self.assertEqual(out.history_rows, 0)

    def test_unauthorized_agent_is_held(self) -> None:
        bad = AgentWrite(
            "w-x2",
            "marketing-agent",
            "gold_customers",
            "ACME-001",
            "segment",
            "SMB",
            "enterprise",
            "ticket:5203",
        )
        out = self._loop_only(bad)
        self.assertEqual(out.gold_segment_after_write, "SMB")

    def test_stale_read_fails_evidence_check(self) -> None:
        stale = AgentWrite(
            "w-x3",
            "support-agent",
            "gold_customers",
            "ACME-001",
            "segment",
            "enterprise",
            "enterprise",
            "ticket:5203",
        )
        out = self._loop_only(stale)
        self.assertEqual(out.gold_segment_after_write, "SMB")

    def test_missing_evidence_is_held(self) -> None:
        bad = AgentWrite(
            "w-x4",
            "support-agent",
            "gold_customers",
            "ACME-001",
            "segment",
            "SMB",
            "enterprise",
            "   ",
        )
        out = self._loop_only(bad)
        self.assertEqual(out.gold_segment_after_write, "SMB")


if __name__ == "__main__":
    unittest.main()
