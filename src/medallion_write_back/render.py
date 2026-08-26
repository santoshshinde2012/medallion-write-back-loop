"""Turn outcomes into the text the article quotes."""

from __future__ import annotations

from .models import PathOutcome


def render_text(outcomes: list[PathOutcome]) -> str:
    lines: list[str] = [
        "=== The write-back problem: one proposed correction, traced twice ===",
        "    gold_customers is the TPC-H customer shape (samples.tpch.customer)",
        "",
    ]
    for o in outcomes:
        recoverable = "yes" if o.can_recover_old_value else "NO"
        lines += [
            f"--- {o.label} ---",
            f"  c_mktsegment Gold serves after write : {o.gold_segment_after_write}",
            f"  validation checks run                : {o.checks_run}",
            f"  landing-zone status                  : {o.status}",
            f"  versioned history rows               : {o.history_rows}",
            f"  old value recoverable                : {recoverable}",
            (
                f"  rollback                             : {o.rollback_statements} statement -> "
                f"c_mktsegment = {o.gold_segment_after_rollback}"
                if o.rollback_statements
                else "  rollback                             : IMPOSSIBLE (nothing recorded)"
            ),
            "",
        ]
    return "\n".join(lines)
