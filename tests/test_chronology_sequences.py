"""Separate conservative chronology contract, real execution and causality."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from chronology_sequences import add_chronology_sequences
from linked_sequences import CHRONOLOGY, CONTRACT, add_linked_sequences
from backtest import run_backtest
from market_state import build_market_state
from trade_planner import build_market_execution_plan
from tests.test_market_execution_backtest import fixture


def case(direction='long', family='continuation'):
    frame, cfg = fixture(direction, family)
    side = 'bullish' if direction == 'long' else 'bearish'
    for s in ('bullish', 'bearish'):
        for name in ('core_sequence', 'core_sequence_completed', 'displacement',
                     'mss', 'displacement_structure_break_event', 'fvg_created'):
            frame[f'{s}_{name}'] = False
    frame['sell_side_liquidity_sweep'] = False
    frame['buy_side_liquidity_sweep'] = False
    frame['bar_complete'] = True
    frame['long_candidate'] = False
    frame['short_candidate'] = False
    frame['close'] = 101. if direction == 'long' else 103.
    if family == 'reversal':
        sweep = 'sell' if direction == 'long' else 'buy'
        frame.loc[0, f'{sweep}_side_liquidity_sweep'] = True
        frame.loc[1, [f'{side}_displacement', f'{side}_mss', f'{side}_fvg_created']] = True
        frame.loc[1:, f'{side}_core_sequence'] = True
        frame.loc[1, f'{side}_core_sequence_completed'] = True
        created, signal = 1, 2
    else:
        frame.loc[0, [f'{side}_displacement_structure_break_event', f'{side}_fvg_created']] = True
        level = 'high' if direction == 'long' else 'low'
        frame.loc[0, f'active_internal_swing_{level}'] = 98. if direction == 'long' else 106.
        frame.loc[2, f'active_internal_swing_{level}'] = 100. if direction == 'long' else 104.
        frame.loc[2, 'close'] = 99.5 if direction == 'long' else 104.5
        created, signal = 0, 3
    frame.loc[signal, f'{direction}_candidate'] = True
    frame.loc[signal, f'{direction}_raw_score'] = 90.
    frame.loc[signal, f'{direction}_score_band'] = 'a_plus_plus'
    frame.loc[signal + 1, ['open', 'high', 'low', 'close']] = [102., 103., 101., 102.]
    objects = pd.DataFrame([dict(fvg_id=1, direction=side,
        creation_time=frame.timestamp.iloc[created], retest_hold_time=frame.timestamp.iloc[2])])
    cfg['backtest']['sequence_contract'] = CHRONOLOGY
    return frame, objects, cfg, signal


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('family', ['reversal', 'continuation'])
def test_chronology_real_state_plan_and_backtest_parity(direction, family):
    frame, objects, cfg, signal = case(direction, family)
    original = frame.copy(deep=True)
    enriched = add_chronology_sequences(frame, objects, break_buffer_points=.25)
    pd.testing.assert_frame_equal(enriched[frame.columns], original)
    cutoff = frame.available_at.iloc[signal]
    state = build_market_state(enriched.iloc[:signal+1], as_of=cutoff,
        generated_at=cutoff, symbol='MNQ', contract=None, strategy_config=cfg)
    plan = build_market_execution_plan(state, cfg, direction=direction,
        entry_price=102.25 if direction == 'long' else 101.75,
        entry_time=frame.timestamp.iloc[signal+1])
    assert plan['candidate'] is not None, plan
    trade = run_backtest(enriched, cfg).iloc[0]
    assert trade.sequence_contract == CHRONOLOGY
    assert trade.setup_family == family
    assert json.loads(trade.execution_plan) == plan
    assert trade.signal_time == frame.timestamp.iloc[signal]
    assert trade.entry_time == frame.timestamp.iloc[signal+1]


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('defect', ['same_sweep', 'no_acceptance', 'same_retest_bos',
                                   'wrong_level', 'invalidation', 'expiry', 'incomplete'])
def test_chronology_rejects_unproven_order_or_hold(direction, defect):
    family = 'reversal' if defect == 'same_sweep' else 'continuation'
    frame, objects, cfg, signal = case(direction, family)
    side = 'bullish' if direction == 'long' else 'bearish'
    if defect == 'same_sweep':
        sweep = 'sell' if direction == 'long' else 'buy'
        frame[f'{sweep}_side_liquidity_sweep'] = False
        frame.loc[1, f'{sweep}_side_liquidity_sweep'] = True
    elif defect == 'no_acceptance':
        frame.loc[1, 'close'] = 97. if direction == 'long' else 107.
    elif defect == 'same_retest_bos':
        frame.loc[2, 'close'] = 101. if direction == 'long' else 103.
    elif defect == 'wrong_level':
        frame.loc[3:, 'close'] = 99.5 if direction == 'long' else 104.5
        # A newly moved live swing must not replace the retest's frozen swing.
        frame.loc[3:, f'active_internal_swing_{"high" if direction == "long" else "low"}'] = 98. if direction == 'long' else 106.
    elif defect == 'invalidation':
        objects['invalidation_time'] = frame.timestamp.iloc[3]
    elif defect == 'incomplete':
        frame.loc[1, 'bar_complete'] = False
    result = add_chronology_sequences(frame, objects, break_buffer_points=.25,
        lookback_bars=3 if defect == 'expiry' else 10)
    assert not result[f'{side}_linked_{family}_entry_valid_event'].any()
    assert run_backtest(result, cfg).empty


def test_prefix_invariance_and_existing_contract_parity():
    frame, objects, cfg, _ = case()
    full = add_chronology_sequences(frame, objects)
    prefix = add_chronology_sequences(frame.iloc[:3], objects)
    pd.testing.assert_frame_equal(full.iloc[:3], prefix)
    changed = frame.copy()
    changed.loc[3:, ['high', 'low', 'close']] = [1000., 1., 900.]
    pd.testing.assert_frame_equal(add_chronology_sequences(changed, objects).iloc[:3], prefix)
    legacy = deepcopy(cfg)
    legacy['backtest'].pop('sequence_contract')
    pd.testing.assert_frame_equal(run_backtest(frame, legacy), run_backtest(full, legacy))
    linked = add_linked_sequences(frame, objects)
    old = deepcopy(cfg)
    old['backtest']['sequence_contract'] = CONTRACT
    with pytest.raises(ValueError, match='versioned'):
        run_backtest(full, old)
    assert linked.linked_sequence_contract.eq(CONTRACT).all()


@pytest.mark.parametrize('family', ['reversal', 'continuation'])
def test_missing_minute_cannot_bridge_sequence_and_new_trigger_resets(family):
    frame, objects, _, _ = case(family=family)
    frame.loc[2:, 'timestamp'] += pd.Timedelta(minutes=2)
    frame['available_at'] = frame.timestamp + pd.Timedelta(minutes=1)
    objects['retest_hold_time'] = frame.timestamp.iloc[2]
    result = add_chronology_sequences(frame, objects)
    assert not result[f'bullish_linked_{family}_entry_valid_event'].any()
    frame, objects, _, _ = case(family=family)
    if family == 'reversal':
        frame.loc[2, 'sell_side_liquidity_sweep'] = True
    else:
        frame.loc[3, 'bullish_displacement_structure_break_event'] = True
    result = add_chronology_sequences(frame, objects)
    assert not result[f'bullish_linked_{family}_entry_valid_event'].any()


def test_later_invalidation_does_not_rewrite_completed_reversal():
    frame, objects, _, _ = case(family='reversal')
    objects['invalidation_time'] = frame.timestamp.iloc[3]
    result = add_chronology_sequences(frame, objects)
    assert result.bullish_linked_reversal_entry_valid_event.iloc[2]
    assert not result.bullish_linked_reversal_sequence.iloc[3]
    prefix = add_chronology_sequences(frame.iloc[:3], objects)
    pd.testing.assert_frame_equal(result.iloc[:3], prefix)


@pytest.mark.parametrize('defect', ['missing_sweep', 'naive_availability', 'late_availability', 'buffer'])
def test_malformed_chronology_evidence_fails_closed(defect):
    frame, objects, _, _ = case()
    buffer = .25
    if defect == 'missing_sweep': frame = frame.drop(columns='sell_side_liquidity_sweep')
    elif defect == 'naive_availability': frame['available_at'] = frame.available_at.dt.tz_localize(None)
    elif defect == 'late_availability': frame.loc[1, 'available_at'] += pd.Timedelta(minutes=1)
    else: buffer = -1
    with pytest.raises(ValueError):
        add_chronology_sequences(frame, objects, break_buffer_points=buffer)
