"""Shared planner/backtest family precedence; unrelated to profitability."""
from __future__ import annotations

DEFAULT_FAMILY_POLICY = 'context_first_family_v1'
CONFIRMATION_FIRST = 'confirmation_first_family_v1'


def selected_family_policy(config):
    backtest = config.get('backtest', {})
    value = backtest.get('family_policy', DEFAULT_FAMILY_POLICY)
    if value not in (DEFAULT_FAMILY_POLICY, CONFIRMATION_FIRST):
        raise ValueError(f'Unknown family policy: {value}')
    if value == CONFIRMATION_FIRST and (
            backtest.get('execution_model') != 'market_after_retest_confirmation_v2'
            or backtest.get('sequence_contract') != 'fvg_chronology_v2'):
        raise ValueError('Research family policy requires chronology v2 and market execution v2')
    return value


def select_confirmation_family(*, policy, reversal_sequence, reversal_event,
                               continuation_sequence, continuation_event,
                               opposite_recent_sweep, opposite_sweep):
    if policy == CONFIRMATION_FIRST:
        if reversal_sequence and reversal_event:
            return 'reversal'
        if continuation_sequence and continuation_event:
            return 'continuation'
        return None
    if policy != DEFAULT_FAMILY_POLICY:
        raise ValueError(f'Unknown family policy: {policy}')
    return classify_setup_family(reversal_sequence=reversal_sequence,
        opposite_recent_sweep=opposite_recent_sweep, opposite_sweep=opposite_sweep)


def classify_setup_family(*, reversal_sequence: bool, opposite_recent_sweep: bool,
                          opposite_sweep: bool) -> str:
    # Preserve planner semantics when reversal and continuation context overlap.
    return 'reversal' if (reversal_sequence or opposite_recent_sweep or opposite_sweep) else 'continuation'
