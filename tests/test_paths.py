"""Lock the article's receipts and the contract's promises.

The article quotes: 3 checks, one versioned history row, a one-statement rollback that
restores FURNITURE, and an in-place path with nothing to roll back to. Each is asserted here.
"""

from __future__ import annotations

import unittest

from medallion_write_back.comparison_service import WritePathComparisonService
from medallion_write_back.demo import SEGMENT_CORRECTION
from medallion_write_back.models import AgentWrite, CheckResult, ValidationReport
from medallion_write_back.repository import SqliteGoldRepository, rebuild_gold_segment
from medallion_write_back.strategies.in_place import CustomerNotFoundError, InPlaceUpdateStrategy
from medallion_write_back.strategies.write_back_loop import WriteBackLoopStrategy


def run_paths(write: AgentWrite) -> list:
    service = WritePathComparisonService(
        repository=SqliteGoldRepository(),
        paths=[InPlaceUpdateStrategy(), WriteBackLoopStrategy()],
    )
    return service.run(write)


class TestArticleReceipts(unittest.TestCase):
    """The numbers the article quotes."""

    def test_loop_runs_exactly_three_checks(self) -> None:
        _, loop = run_paths(SEGMENT_CORRECTION)
        self.assertEqual(loop.checks_run, 3)

    def test_loop_promotes_versioned_and_gold_serves_the_correction(self) -> None:
        _, loop = run_paths(SEGMENT_CORRECTION)
        self.assertEqual(loop.gold_segment_after_write, "BUILDING")
        self.assertEqual(loop.history_rows, 1)
        self.assertEqual(loop.status, "promoted")

    def test_rollback_is_one_statement_and_restores_the_old_segment(self) -> None:
        _, loop = run_paths(SEGMENT_CORRECTION)
        self.assertEqual(loop.rollback_statements, 1)
        self.assertEqual(loop.gold_segment_after_rollback, "FURNITURE")

    def test_in_place_loses_the_old_value(self) -> None:
        in_place, _ = run_paths(SEGMENT_CORRECTION)
        self.assertEqual(in_place.gold_segment_after_write, "BUILDING")
        self.assertFalse(in_place.can_recover_old_value)
        self.assertIsNone(in_place.rollback_statements)
        self.assertEqual(in_place.history_rows, 0)


class TestContractHoldsTheLine(unittest.TestCase):
    """Each check must actually stop a bad write."""

    def _loop(self, write: AgentWrite):
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            return WriteBackLoopStrategy().apply(conn, write), conn
        finally:
            pass  # caller closes

    def _apply_and_close(self, write: AgentWrite):
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            return WriteBackLoopStrategy().apply(conn, write)
        finally:
            conn.close()

    def test_invalid_segment_is_held_not_promoted(self) -> None:
        bad = AgentWrite("w-x1", "segment-agent", 412_445, "FURNITURE", "GALACTIC", "ticket:1")
        out = self._apply_and_close(bad)
        self.assertEqual(out.status, "held")
        self.assertEqual(out.gold_segment_after_write, "FURNITURE")
        self.assertEqual(out.history_rows, 0)

    def test_unauthorized_agent_is_held(self) -> None:
        bad = AgentWrite("w-x2", "marketing-agent", 412_445, "FURNITURE", "BUILDING", "ticket:1")
        out = self._apply_and_close(bad)
        self.assertEqual(out.status, "held")
        self.assertEqual(out.gold_segment_after_write, "FURNITURE")

    def test_missing_evidence_is_held(self) -> None:
        bad = AgentWrite("w-x3", "segment-agent", 412_445, "FURNITURE", "BUILDING", "   ")
        out = self._apply_and_close(bad)
        self.assertEqual(out.status, "held")

    def test_unknown_customer_is_held_not_crashed(self) -> None:
        bad = AgentWrite("w-x4", "segment-agent", 999_999, "FURNITURE", "BUILDING", "ticket:1")
        out = self._apply_and_close(bad)
        self.assertEqual(out.status, "held")

    def test_held_write_reports_no_rollback(self) -> None:
        """A held write must not claim a rollback that never happened."""
        bad = AgentWrite("w-x5", "segment-agent", 412_445, "FURNITURE", "GALACTIC", "ticket:1")
        out = self._apply_and_close(bad)
        self.assertIsNone(out.rollback_statements)
        self.assertFalse(out.can_recover_old_value)


class TestFreshReadAgainstServedGold(unittest.TestCase):
    """The fresh read must compare with what Gold *serves*, not the untouched base row."""

    def test_stale_write_after_an_earlier_correction_is_held(self) -> None:
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            loop = WriteBackLoopStrategy()
            first = AgentWrite("w-a", "segment-agent", 412_445, "FURNITURE", "BUILDING", "q:1")
            self.assertEqual(loop.apply(conn, first).status, "promoted")
            self.assertEqual(rebuild_gold_segment(conn, 412_445), "BUILDING")

            # A second agent still believes the old base value. Gold now serves BUILDING,
            # so this write is built on a stale read and must be held.
            stale = AgentWrite("w-b", "segment-agent", 412_445, "FURNITURE", "MACHINERY", "q:2")
            out = loop.apply(conn, stale)
            self.assertEqual(out.status, "held")
            self.assertEqual(rebuild_gold_segment(conn, 412_445), "BUILDING")
        finally:
            conn.close()


class TestReplayIsSafe(unittest.TestCase):
    """Re-running an agent must not crash or double-post."""

    def test_replaying_the_same_write_id_is_a_no_op(self) -> None:
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            loop = WriteBackLoopStrategy()
            first = loop.apply(conn, SEGMENT_CORRECTION)
            second = loop.apply(conn, SEGMENT_CORRECTION)  # must not raise
            self.assertEqual(first.status, "promoted")
            self.assertEqual(second.status, "promoted")
            self.assertEqual(second.history_rows, 1)  # still one correction, not two
            rows = conn.execute("SELECT COUNT(*) FROM bronze_agent_writes").fetchone()[0]
            self.assertEqual(rows, 1)
        finally:
            conn.close()


class TestFailsClosed(unittest.TestCase):
    """A mis-wired contract must never pass."""

    def test_empty_validation_report_does_not_pass(self) -> None:
        self.assertFalse(ValidationReport(()).passed)

    def test_report_with_a_failing_check_does_not_pass(self) -> None:
        report = ValidationReport(
            (CheckResult("shape", True, ""), CheckResult("evidence", False, ""))
        )
        self.assertFalse(report.passed)

    def test_empty_contract_holds_every_write(self) -> None:
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            out = WriteBackLoopStrategy(validators=()).apply(conn, SEGMENT_CORRECTION)
            self.assertEqual(out.status, "held")
        finally:
            conn.close()


class TestInPlaceFailsLoudly(unittest.TestCase):
    def test_unknown_customer_raises_a_named_error(self) -> None:
        conn = SqliteGoldRepository().connect_and_seed()
        try:
            bad = AgentWrite("w-z", "segment-agent", 999_999, "FURNITURE", "BUILDING", "q:1")
            with self.assertRaises(CustomerNotFoundError):
                InPlaceUpdateStrategy().apply(conn, bad)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
