"""Turn outcomes into the text the article quotes."""

from __future__ import annotations

from .models import PathOutcome


def render_text(outcomes: list[PathOutcome]) -> str:
    lines: list[str] = ["=== The Write-Back Problem: one correction, traced twice ===", ""]
    for o in outcomes:
        lines += [
            f"--- {o.label} ---",
            f"  gold.customers segment after write : {o.gold_segment_after_write}",
            f"  validation checks run              : {o.checks_run}",
            f"  history rows (versioned)           : {o.history_rows}",
            f"  old value recoverable              : {'yes' if o.can_recover_old_value else 'NO'}",
            (
                f"  rollback                           : {o.rollback_statements} statement -> "
                f"segment = {o.gold_segment_after_rollback}"
                if o.rollback_statements is not None
                else "  rollback                           : IMPOSSIBLE (nothing recorded)"
            ),
            "",
        ]
    return "\n".join(lines)
