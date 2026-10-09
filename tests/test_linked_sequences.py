"""Linked-object correctness and opt-in planner/backtest parity contracts."""
from copy import deepcopy

import pandas as pd
import pytest

from linked_sequences import CONTRACT, add_linked_sequences, apply_sequence_contract
from backtest import run_backtest, BacktestError
from market_state import build_market_state
from trade_planner import build_market_execution_plan
from tests.test_market_execution_backtest import fixture


def inputs(direction='long', family='reversal', *, old_retest=False):
    frame, config = fixture(direction, family)
    side = 'bullish' if direction == 'long' else 'bearish'
    for s in ('bullish', 'bearish'):
        for name in ('core_sequence', 'core_sequence_completed',
                     'displacement_structure_break_event', 'fvg_created'):
            frame[f'{s}_{name}'] = False
    trigger = 1 if old_retest else 0
    if family == 'reversal':
        frame.loc[trigger:, f'{side}_core_sequence'] = True
        frame.loc[trigger, f'{side}_core_sequence_completed'] = True
    else:
        frame.loc[trigger, f'{side}_displacement_structure_break_event'] = True
    frame.loc[0, f'{side}_fvg_created'] = True
    records = [dict(fvg_id=1, direction=side,
        creation_time=frame.timestamp.iloc[0], retest_hold_time=frame.timestamp.iloc[1])]
    if old_retest:
        frame.loc[1, f'{side}_fvg_created'] = True
        records.append(dict(fvg_id=2, direction=side,
            creation_time=frame.timestamp.iloc[1], retest_hold_time=pd.NaT))
    objects = pd.DataFrame(records)
    config['backtest']['sequence_contract'] = CONTRACT
    return frame, objects, config


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('family', ['reversal', 'continuation'])
@pytest.mark.parametrize('old_retest', [False, True])
def test_linked_object_confirmation_agrees_through_real_market_state_and_execution(direction, family, old_retest):
    frame, objects, config = inputs(direction, family, old_retest=old_retest)
    original = frame.copy(deep=True)
    enriched = add_linked_sequences(frame, objects)
    pd.testing.assert_frame_equal(enriched[frame.columns], original)
    selected = apply_sequence_contract(enriched, config)
    side = 'bullish' if direction == 'long' else 'bearish'
    assert bool(selected.loc[1, f'{side}_{family}_entry_valid_event']) is (not old_retest)
    cutoff = frame.available_at.iloc[1]
    state = build_market_state(enriched.iloc[:2], as_of=cutoff, generated_at=cutoff,
                               symbol='MNQ', contract=None, strategy_config=config)
    price = 102 + (0.25 if direction == 'long' else -0.25)
    decision = build_market_execution_plan(state, config, direction=direction,
        entry_price=price, entry_time=frame.timestamp.iloc[2])
    trades = run_backtest(enriched, config)
    if old_retest:
        assert decision['candidate'] is None
        assert 'fresh_confirmation_event_required' in decision['rejections']
        assert trades.empty
    else:
        assert decision['candidate'] is not None, decision
        assert len(trades) == 1
        assert trades.iloc[0].sequence_contract == CONTRACT
        assert trades.iloc[0].setup_family == family
        assert decision['confirmation_fvg_id'] == enriched.loc[1, f'{side}_linked_{family}_fvg_id']
        import json
        assert json.loads(trades.iloc[0].execution_plan) == decision


def test_same_creation_bar_retest_is_not_ordered_and_expiry_rejects_late_retest():
    frame, objects, _ = inputs()
    objects['retest_hold_time'] = frame.timestamp.iloc[0]
    result = add_linked_sequences(frame, objects)
    assert not result.bullish_linked_reversal_entry_valid_event.any()
    objects['retest_hold_time'] = frame.timestamp.iloc[2]
    result = add_linked_sequences(frame, objects, lookback_bars=2)
    assert not result.bullish_linked_reversal_entry_valid_event.any()


def test_invalidation_on_retest_bar_rejects_object_but_future_invalidation_is_invariant():
    frame, objects, _ = inputs()
    objects['invalidation_time'] = frame.timestamp.iloc[1]
    assert not add_linked_sequences(frame, objects).bullish_linked_reversal_entry_valid_event.any()
    objects['invalidation_time'] = frame.timestamp.iloc[-1]
    full = add_linked_sequences(frame, objects)
    prefix = add_linked_sequences(frame.iloc[:2], objects)
    pd.testing.assert_frame_equal(full.iloc[:2], prefix)


@pytest.mark.parametrize('defect', ['naive', 'duplicate_id', 'unmatched_creation', 'wrong_direction', 'mixed_contract'])
def test_bad_object_provenance_fails_closed(defect):
    frame, objects, _ = inputs()
    if defect == 'naive':
        objects['creation_time'] = objects.creation_time.dt.tz_localize(None)
    elif defect == 'duplicate_id':
        objects = pd.concat([objects, objects], ignore_index=True)
    elif defect == 'unmatched_creation':
        frame['bullish_fvg_created'] = False
    elif defect == 'wrong_direction':
        objects['direction'] = 'unknown'
    else:
        frame['contract'] = ['OLD', *(['NEW'] * (len(frame)-1))]
    with pytest.raises(ValueError):
        add_linked_sequences(frame, objects)


def test_opt_in_requires_schema_and_identity_and_cannot_use_score_only_execution():
    frame, objects, config = inputs()
    with pytest.raises(ValueError, match='versioned feature'):
        run_backtest(frame, config)
    linked = add_linked_sequences(frame, objects)
    broken = linked.copy()
    broken['bullish_linked_reversal_fvg_id'] = None
    with pytest.raises(ValueError, match='FVG identity'):
        run_backtest(broken, config)
    config['backtest']['execution_model'] = 'score_signal_v1'
    with pytest.raises(BacktestError, match='requires market v2'):
        run_backtest(linked, config)


def test_legacy_contract_preserves_results_and_inputs_and_missing_planner_evidence_rejects():
    frame, objects, config = inputs()
    cfg = deepcopy(config)
    cfg['backtest'].pop('sequence_contract')
    linked = add_linked_sequences(frame, objects)
    pd.testing.assert_frame_equal(run_backtest(frame, cfg), run_backtest(linked, cfg))
    assert apply_sequence_contract(frame, cfg) is frame
    cutoff = frame.available_at.iloc[1]
    state = build_market_state(frame.iloc[:2], as_of=cutoff, generated_at=cutoff,
        symbol='MNQ', contract=None, strategy_config=config)
    original = deepcopy(state)
    decision = build_market_execution_plan(state, config, direction='long',
        entry_price=102.25, entry_time=frame.timestamp.iloc[2])
    assert decision['candidate'] is None
    assert 'object_linked_confirmation_evidence_required' in decision['rejections']
    assert state == original
