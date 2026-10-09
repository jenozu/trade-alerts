"""Research family selection must stay shared, explicit and causally confirmed."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from backtest import confirmed_setup_family, run_backtest
from chronology_sequences import add_chronology_sequences
from market_state import build_market_state
from trade_planner import build_market_execution_plan
from tests.test_chronology_sequences import case

POLICY = 'confirmation_first_family_v1'


def overlap(direction='long'):
    frame, objects, cfg, signal = case(direction, 'continuation')
    frame = add_chronology_sequences(frame, objects)
    opposite = 'sell_side' if direction == 'long' else 'buy_side'
    frame[f'recent_{opposite}_sweep'] = True
    cfg['backtest']['family_policy'] = POLICY
    return frame, cfg, signal


@pytest.mark.parametrize('direction', ['long', 'short'])
def test_confirmed_continuation_with_sweep_has_shared_accepted_plan(direction):
    frame, cfg, signal = overlap(direction)
    before = frame.copy(deep=True)
    old = deepcopy(cfg)
    old['backtest'].pop('family_policy')
    assert run_backtest(frame, old).empty
    cutoff = frame.available_at.iloc[signal]
    state = build_market_state(frame.iloc[:signal+1], as_of=cutoff,
        generated_at=cutoff, symbol='MNQ', contract=None, strategy_config=cfg)
    decision = build_market_execution_plan(state, cfg, direction=direction,
        entry_price=102.25 if direction == 'long' else 101.75,
        entry_time=frame.timestamp.iloc[signal+1])
    assert decision['candidate'] is not None, decision
    trade = run_backtest(frame, cfg).iloc[0]
    assert decision['candidate']['setup']['family'] == trade.setup_family == 'continuation'
    assert json.loads(trade.execution_plan) == decision
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize('direction', ['long','short'])
@pytest.mark.parametrize('reversal_ready', [False, True])
def test_only_fresh_ready_families_compete_and_both_ready_prefers_reversal(direction, reversal_ready):
    frame, cfg, signal = overlap(direction)
    side = 'bullish' if direction == 'long' else 'bearish'
    frame[f'{side}_linked_reversal_sequence'] = True
    frame[f'{side}_linked_reversal_entry_valid_event'] = reversal_ready
    frame[f'{side}_linked_reversal_fvg_id'] = 'test-reversal-object'
    from linked_sequences import apply_sequence_contract
    row = apply_sequence_contract(frame, cfg).iloc[signal]
    assert confirmed_setup_family(row, direction, cfg) == ('reversal' if reversal_ready else 'continuation')
    for name in ('bar_complete','new_entry_allowed'):
        changed = row.copy();changed[name] = False
        assert confirmed_setup_family(changed, direction, cfg) is None


@pytest.mark.parametrize('missing', ['sequence','entry_valid_event'])
def test_no_partial_continuation_evidence_or_fallback(missing):
    frame, cfg, signal = overlap()
    frame[f'bullish_linked_continuation_{missing}'] = False
    if missing == 'sequence':
        frame['bullish_linked_continuation_entry_valid_event'] = False
    assert run_backtest(frame, cfg).empty


@pytest.mark.parametrize('bad', ['typo', None, True])
def test_unknown_policy_fails_even_without_candidates(bad):
    frame, cfg, _ = overlap();cfg['backtest']['family_policy'] = bad
    frame['long_candidate'] = False
    with pytest.raises(ValueError, match='family policy'):
        run_backtest(frame, cfg)


@pytest.mark.parametrize('change', ['execution_model','sequence_contract'])
def test_research_policy_requires_chronology_market_execution(change):
    frame, cfg, _ = overlap()
    cfg['backtest'][change] = 'score_signal_v1' if change == 'execution_model' else 'production_boolean_v1'
    with pytest.raises(ValueError, match='requires'):
        run_backtest(frame, cfg)


@pytest.mark.parametrize('direction', ['long', 'short'])
def test_future_extremes_do_not_change_research_policy_entry_decision(direction):
    frame, cfg, signal = overlap(direction)
    original = run_backtest(frame, cfg).iloc[0]
    frame.loc[signal+1:, ['high','low','close']] = [1000., 1., 800.]
    changed = run_backtest(frame, cfg).iloc[0]
    assert changed.execution_plan == original.execution_plan
    assert changed.setup_family == original.setup_family == 'continuation'


def test_archived_candidate_flags_preserve_seven_signals_and_add_only_named_continuation():
    import base64, gzip
    from pathlib import Path
    from linked_sequences import apply_sequence_contract
    path = Path(__file__).resolve().parents[1] / 'research-archive/EXP-INTEGRITY-2023-QUALIFICATION/qualification_export.txt'
    rows = json.loads(gzip.decompress(base64.b64decode(path.read_text().splitlines()[1])))
    cfg = {'backtest': {'execution_model':'market_after_retest_confirmation_v2',
                       'sequence_contract':'fvg_chronology_v2', 'family_policy':POLICY}}
    frame = apply_sequence_contract(pd.DataFrame(rows), cfg)
    control, variant = set(), set()
    for _, row in frame.iterrows():
        direction = 'long' if row.long_candidate else 'short'
        old = confirmed_setup_family(row, direction)
        new = confirmed_setup_family(row, direction, cfg)
        if old: control.add((row.timestamp, direction, old))
        if new: variant.add((row.timestamp, direction, new))
    assert len(control) == 7 and len(variant) == 8
    assert control.issubset(variant)
    assert variant - control == {('2023-08-24T13:45:00.000Z', 'short', 'continuation')}
