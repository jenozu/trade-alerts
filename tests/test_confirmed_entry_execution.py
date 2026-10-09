"""The selected entry contract: completed retest confirmation -> next open."""
import pandas as pd
import pytest
from backtest import BacktestError, build_backtest_settings, run_backtest
from tests.test_backtest import _bars, _mark_long, _mark_short, _config

MODE = 'market_after_retest_confirmation_v1'


def config():
    result = _config(slippage=True)
    result['backtest']['execution_model'] = MODE
    return result


def bars(direction='long', family='reversal'):
    frame = _bars(5)
    (_mark_long if direction == 'long' else _mark_short)(frame, 1)
    frame['new_entry_allowed'] = True
    frame['recent_sell_side_sweep'] = family == 'reversal' and direction == 'long'
    frame['recent_buy_side_sweep'] = family == 'reversal' and direction == 'short'
    for side in ('bullish', 'bearish'):
        for setup in ('reversal', 'continuation'):
            frame[f'{side}_{setup}_sequence'] = False
            frame[f'{side}_{setup}_entry_valid_event'] = False
    side = 'bullish' if direction == 'long' else 'bearish'
    frame.loc[1:, f'{side}_{family}_sequence'] = True
    frame.loc[1, f'{side}_{family}_entry_valid_event'] = True
    frame['available_at'] = frame.timestamp + pd.Timedelta(minutes=1)
    frame.loc[2, ['open', 'high', 'low', 'close']] = [102, 103, 101, 102]
    return frame


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('family', ['reversal', 'continuation'])
def test_confirmation_enters_next_open_with_adverse_slippage(direction, family):
    frame = bars(direction, family)
    trade = run_backtest(frame, config()).iloc[0]
    assert trade.entry_time == frame.timestamp.iloc[2]
    assert trade.confirmation_time == frame.available_at.iloc[1]
    assert trade.entry_price_raw == 102
    assert trade.entry_price == 102 + (0.25 if direction == 'long' else -0.25)
    assert trade.setup_family == family
    assert trade.execution_model == MODE


@pytest.mark.parametrize('missing', ['sequence', 'entry_valid_event'])
def test_high_score_and_ingredients_cannot_substitute_for_confirmation(missing):
    frame = bars()
    frame[f'bullish_reversal_{missing}'] = False
    frame['recent_bullish_displacement'] = True
    frame['recent_bullish_mss'] = True
    frame['bullish_fvg_retest_hold'] = True
    assert run_backtest(frame, config()).empty


def test_persisting_sequence_does_not_reenter_without_a_new_confirmation_event():
    frame = bars()
    frame.loc[:, 'bullish_reversal_entry_valid_event'] = False
    for i in range(4):
        _mark_long(frame, i)
    assert run_backtest(frame, config()).empty


def test_planner_reversal_context_does_not_become_continuation_by_choosing_other_flag():
    frame = bars()
    frame['bullish_reversal_sequence'] = False
    frame['bullish_continuation_sequence'] = True
    frame['bullish_continuation_entry_valid_event'] = True
    assert run_backtest(frame, config()).empty


@pytest.mark.parametrize('field', ['bar_complete', 'new_entry_allowed'])
def test_incomplete_or_ineligible_confirmation_does_not_enter(field):
    frame = bars()
    frame.loc[1, field] = False
    assert run_backtest(frame, config()).empty


def test_confirmation_not_available_at_next_open_cannot_fill_in_the_past():
    frame = bars()
    frame.loc[1, 'available_at'] += pd.Timedelta(minutes=1)
    assert run_backtest(frame, config()).empty


def test_missing_confirmation_schema_fails_closed():
    frame = bars().drop(columns='bullish_reversal_sequence')
    with pytest.raises(BacktestError, match='confirmation'):
        run_backtest(frame, config())


def test_archived_baseline_remains_available_without_new_columns():
    frame = _bars(3)
    _mark_long(frame, 0)
    legacy = _config()
    implicit = run_backtest(frame, legacy)
    legacy['backtest']['execution_model'] = 'score_signal_v1'
    pd.testing.assert_frame_equal(implicit, run_backtest(frame, legacy))
    assert 'execution_model' not in implicit


@pytest.mark.parametrize('change', [
    {'execution_model': 'unknown'},
    {'entry_on_next_bar_open': False},
    {'use_completed_bars_only': False},
])
def test_invalid_confirmed_mode_options_rejected(change):
    cfg = config()
    cfg['backtest'].update(change)
    with pytest.raises(BacktestError):
        build_backtest_settings(cfg)


def test_unconfirmed_higher_score_does_not_block_confirmed_opposite_direction():
    frame = bars('short', 'continuation')
    _mark_long(frame, 1, score=99)
    trade = run_backtest(frame, config()).iloc[0]
    assert trade.direction == 'short'


def test_future_rows_cannot_rewrite_a_completed_confirmed_trade():
    prefix = bars().iloc[:3].copy()
    prefix.loc[2, 'low'] = 50
    future = bars().iloc[:2].copy()
    future['timestamp'] = pd.date_range(prefix.timestamp.iloc[-1] + pd.Timedelta(minutes=1), periods=2, freq='min', tz='UTC')
    future['available_at'] = future.timestamp + pd.Timedelta(minutes=1)
    future.loc[:, ['open', 'high', 'low', 'close']] = [200, 250, 1, 100]
    first = run_backtest(prefix, config()).iloc[[0]].reset_index(drop=True)
    extended = run_backtest(pd.concat([prefix, future], ignore_index=True), config()).iloc[[0]].reset_index(drop=True)
    pd.testing.assert_frame_equal(first, extended)


def test_cached_runner_exposes_explicit_execution_model_selection(monkeypatch):
    from scripts import run_cached_backtest
    monkeypatch.setattr('sys.argv', ['run_cached_backtest.py', '--cache-dir', '/cache',
        '--input', '/raw.parquet', '--execution-model', MODE])
    assert run_cached_backtest.parse_args().execution_model == MODE


def test_string_confirmation_flags_are_not_treated_as_true():
    frame = bars()
    frame['bullish_reversal_entry_valid_event'] = 'false'
    with pytest.raises(BacktestError, match='boolean'):
        run_backtest(frame, config())
