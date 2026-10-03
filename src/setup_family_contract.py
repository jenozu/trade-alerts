"""Shared planner/backtest family precedence; unrelated to profitability."""
from __future__ import annotations


def classify_setup_family(*, reversal_sequence: bool, opposite_recent_sweep: bool,
                          opposite_sweep: bool) -> str:
    # Preserve planner semantics when reversal and continuation context overlap.
    return 'reversal' if (reversal_sequence or opposite_recent_sweep or opposite_sweep) else 'continuation'
