"""Integrity evidence: preserve causal parity and expose uncertified semantics.

Mismatch assertions are audit findings, not approval of the baseline strategy.
They must be replaced with explicit parity contracts after semantic decisions.
"""
from datetime import timedelta
import numpy as np
import pandas as pd
import pytest
import run_pipeline as pipeline
from backtest import run_backtest, load_strategy_config
from data_clock import filter_as_of
from market_state import build_market_state
from report_generator import build_morning_alert
from scorer import score_setup
from structure import _ordered_core_sequence, _ordered_fvg_confirmation
from trade_planner import build_trade_plan
from tests.test_backtest import _bars, _mark_long, _config as execution_config
from tests.test_trade_planner import _state, _config as planner_config


@pytest.mark.parametrize('direction,side', [('long', 'bullish'), ('short', 'bearish')])
@pytest.mark.parametrize('family', ['reversal', 'continuation'])
def test_unrelated_old_gap_retest_can_complete_production_confirmation(direction, side, family):
    """Characterize an unresolved mismatch, not an approved entry contract.

    The real FVG projection drops object identity. An old gap's retest can then
    complete a new setup despite the new gap never having been retested.
    """
    from backtest import confirmed_setup_family
    from fvg import attach_fvg_events_to_bars
    from structure import add_fvg_structure_sequences, add_production_setup_sequences

    bars = _bars(4)
    bars['bar_complete'] = True
    bars['new_entry_allowed'] = True
    bars[f'{side}_fvg_created'] = [True, False, True, False]
    tracked = pd.DataFrame([
        dict(fvg_id=1, direction=side, creation_time=bars.timestamp.iloc[0],
             retest_hold_time=bars.timestamp.iloc[3]),
        dict(fvg_id=2, direction=side, creation_time=bars.timestamp.iloc[2],
             retest_hold_time=pd.NaT),
    ])
    for column in ('first_touch_time', 'full_fill_time', 'inverse_fvg_time'):
        tracked[column] = pd.NaT
    projected = attach_fvg_events_to_bars(bars, tracked)
    assert projected.loc[3, f'{side}_fvg_retest_hold']
    assert pd.isna(tracked.loc[1, 'retest_hold_time'])
    assert 'fvg_id' not in projected

    if family == 'reversal':
        projected[f'{side}_core_sequence'] = [False, False, True, True]
        projected[f'{side}_core_sequence_completed'] = [False, False, True, False]
        projected = add_fvg_structure_sequences(projected)
    else:
        projected[f'{side}_displacement_structure_break_event'] = [False, False, True, False]
    result = add_production_setup_sequences(projected)
    assert result.loc[3, f'{side}_{family}_entry_valid_event']
    assert confirmed_setup_family(result.iloc[3], direction) == family


def test_positive_plan_and_backtest_have_documented_price_and_confirmation_mismatches():
    state = _state()
    config = planner_config()
    candidate = build_trade_plan(state, config)['preferred']
    bars = _bars(3)
    _mark_long(bars, 0, score=state['scores']['long']['raw_score'])
    bars['dol_direction'] = state['draw_on_liquidity']['direction']
    bars['active_internal_swing_low'] = state['levels']['nearest_important_swing_low']
    cfg = execution_config(slippage=False)
    cfg['stop_loss']['primary_method'] = 'structural'
    trade = run_backtest(bars, cfg).iloc[0]
    assert trade.direction == candidate['direction'] == 'long'
    assert trade.raw_score == candidate['scores']['raw_score'] == 82
    assert trade.dol_direction == 'bullish'
    assert trade.entry_price == candidate['entry_zone']['risk_entry_price'] == 100
    assert trade.stop_price == candidate['stop_loss']['price'] == 78
    assert candidate['scenario_status'] == 'HYPOTHESIS'
    assert trade.tp1 == 125 and candidate['targets']['tp1']['price'] == 130
    assert trade.tp4 == 200 and candidate['targets']['tp4']['price'] == 180
    assert 'setup_family' not in trade.index
    assert 'invalidation_criteria' not in trade.index
    # Baseline traded without ordered confirmation; the alert retains hypothesis.
    alert = build_morning_alert(state, build_trade_plan(state, config))
    assert alert is not None


def test_score_does_not_gate_on_ordered_production_sequence():
    cfg = load_strategy_config()
    row = _bars(3).iloc[0].copy()
    row['recent_sell_side_sweep'] = True
    row['recent_bullish_displacement'] = True
    row['recent_bullish_mss'] = True
    row['bullish_fvg_retest_hold'] = True
    row['bullish_reversal_sequence'] = False
    unordered = score_setup(row, direction='long', config=cfg)
    row['bullish_reversal_sequence'] = True
    ordered = score_setup(row, direction='long', config=cfg)
    assert unordered == ordered


def test_core_and_fvg_state_machines_allow_same_bar_order_assumption():
    active, completed = _ordered_core_sequence(
        sweep_events=pd.Series([True]), displacement_events=pd.Series([True]),
        mss_events=pd.Series([True]), lookback_bars=10)
    assert completed.iloc[0]
    _, retest = _ordered_fvg_confirmation(core_active=active, core_completed=completed,
        fvg_created=pd.Series([True]), fvg_retest=pd.Series([True]))
    assert retest.iloc[0]  # OHLC alone does not prove this intrabar sequence.


def test_scorer_window_is_enforced_but_missing_policy_is_permissive():
    cfg = load_strategy_config()
    row = _bars(3).iloc[0].copy()
    row['new_entry_allowed'] = False
    result = score_setup(row, direction='long', config=cfg)
    assert result.disabled and result.disable_reason == 'outside_entry_window'
    result = score_setup(row.drop('new_entry_allowed'), direction='long', config=cfg)
    assert not result.disabled


def _raw_features(raw, config, destination):
    # Real production stage functions; no feature/state/scorer/planner stubs.
    resampled = pipeline.stage_resample(raw, processed_directory=destination)
    frame = pipeline.stage_bias(raw, resampled_results=resampled, strategy_config=config, processed_directory=destination)
    frame = pipeline.stage_sessions(frame, sessions_config=pipeline.load_sessions_config('config/sessions.yaml'), processed_directory=destination)
    for stage in (pipeline.stage_vwap, pipeline.stage_volume):
        frame = stage(frame, strategy_config=config, processed_directory=destination)
    frame = pipeline.stage_snr(frame, resampled_results=resampled, strategy_config=config, processed_directory=destination)
    for stage in (pipeline.stage_swings, pipeline.stage_liquidity, pipeline.stage_fvg,
                  pipeline.stage_pd_arrays, pipeline.stage_structure):
        frame = stage(frame, strategy_config=config, processed_directory=destination)
    frame = pipeline.stage_dealing_range(frame, processed_directory=destination)
    for stage in (pipeline.stage_dol, pipeline.stage_scoring):
        frame = stage(frame, strategy_config=config, processed_directory=destination)
    return frame


def test_raw_bar_replay_to_market_state_planner_alert_is_append_invariant(tmp_path):
    n = 90
    t = pd.date_range('2025-06-02 13:30', periods=n, freq='min', tz='UTC')
    base = 20000 + np.sin(np.arange(n) / 3) * 15 + np.arange(n) * 0.2
    raw = pd.DataFrame({'timestamp': t, 'available_at': t + timedelta(minutes=1),
                        'bar_complete': True, 'open': base, 'close': base + 0.25,
                        'high': base + 1, 'low': base - 1, 'volume': 1000.0})
    as_of = t[59] + timedelta(minutes=1)
    config = load_strategy_config()
    prefix = filter_as_of(raw, as_of=as_of)
    replay = _raw_features(raw, config, tmp_path / 'replay')
    live = _raw_features(prefix, config, tmp_path / 'live')
    kwargs = dict(as_of=as_of, symbol='MNQ', contract='SYNTHETIC', strategy_config=config,
                  data_quality={'analysis_status': 'pass', 'reasons': [], 'session_coverage': {'all_due_covered': True}})
    replay_state = build_market_state(replay, **kwargs)
    live_state = build_market_state(live, **kwargs)
    assert replay_state == live_state
    replay_plan = build_trade_plan(replay_state, config)
    live_plan = build_trade_plan(live_state, config)
    assert replay_plan == live_plan
    assert build_morning_alert(replay_state, replay_plan) == build_morning_alert(live_state, live_plan)
    pd.testing.assert_frame_equal(run_backtest(filter_as_of(replay, as_of=as_of), config), run_backtest(live, config))


def test_unsegmented_contract_gap_can_create_false_fvg_but_isolated_segments_cannot():
    from fvg import build_fvg_settings, detect_fvg_creation
    from rollover import ContractWindow, stitch_contract_frames, split_rollover_segments
    old = _bars(3).assign(volume=100, contract='OLD')
    new = _bars(3).assign(volume=100, contract='NEW')
    new['timestamp'] += timedelta(minutes=3)
    for column in ('open', 'high', 'low', 'close'):
        new[column] += 100
    boundary = new.timestamp.iloc[0]
    stitched = stitch_contract_frames({'OLD': old, 'NEW': new}, [
        ContractWindow('OLD', start=old.timestamp.iloc[0], end=boundary),
        ContractWindow('NEW', start=boundary)])
    settings = build_fvg_settings({'market': {'tick_size': 0.25}})
    assert detect_fvg_creation(stitched, settings=settings).bullish_fvg_created.any()
    for segment in split_rollover_segments(stitched):
        assert not detect_fvg_creation(segment, settings=settings).bullish_fvg_created.any()
