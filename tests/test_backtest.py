from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import BacktestError, run_backtest, validate_input_dataframe


def _config(*, maximum_holding_minutes: int = 60, slippage: bool = True) -> dict:
    return {
        "backtest": {
            "use_completed_bars_only": True,
            "entry_on_next_bar_open": True,
            "conservative_same_bar_resolution": True,
            "same_bar_stop_and_target_behavior": "stop_first",
            "commission": {
                "enabled": False,
                "per_contract_round_trip": 0.0,
            },
            "slippage": {
                "enabled": slippage,
                "points_per_entry": 0.25,
                "points_per_exit": 0.25,
            },
        },
        "trade_management": {
            "maximum_holding_minutes": maximum_holding_minutes,
            "maximum_one_open_trade": True,
        },
        "stop_loss": {
            "primary_method": "fixed",
            "structural": {"buffer_points": 2.0},
            "preferred_initial_range_points": {
                "minimum": 20.0,
                "maximum": 25.0,
            },
            "fixed_research_values_points": [15, 20, 25, 30, 35],
        },
        "take_profit": {
            "number_of_targets": 4,
            "preferred_initial": {
                "tp1_points": 25.0,
                "tp2_points": 50.0,
                "tp3_points": 75.0,
                "tp4_points": 100.0,
            },
        },
    }


def _bars(periods: int = 6) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-08-31 13:30:00",
        periods=periods,
        freq="1min",
        tz="UTC",
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": np.full(periods, 100.0),
            "high": np.full(periods, 101.0),
            "low": np.full(periods, 99.0),
            "close": np.full(periods, 100.0),
            "long_raw_score": np.zeros(periods, dtype=float),
            "short_raw_score": np.zeros(periods, dtype=float),
            "long_score_band": ["no_trade"] * periods,
            "short_score_band": ["no_trade"] * periods,
            "long_candidate": np.zeros(periods, dtype=bool),
            "short_candidate": np.zeros(periods, dtype=bool),
            "bar_complete": np.ones(periods, dtype=bool),
        }
    )


def _mark_long(df: pd.DataFrame, index: int, *, score: float = 80.0) -> None:
    df.loc[index, "long_candidate"] = True
    df.loc[index, "long_raw_score"] = score
    df.loc[index, "long_score_band"] = "high_probability"


def _mark_short(df: pd.DataFrame, index: int, *, score: float = 80.0) -> None:
    df.loc[index, "short_candidate"] = True
    df.loc[index, "short_raw_score"] = score
    df.loc[index, "short_score_band"] = "high_probability"


def test_backtest_rejects_naive_timestamps():
    df = _bars(3)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    with pytest.raises(BacktestError, match="timezone-aware"):
        validate_input_dataframe(df)


def test_long_signal_enters_next_bar_open_with_adverse_slippage_and_entry_based_targets():
    df = _bars(4)
    _mark_long(df, 0)
    df.loc[1, "open"] = 101.0
    df.loc[1:, "high"] = 102.0
    df.loc[1:, "low"] = 100.0
    df.loc[1:, "close"] = 101.0

    trades = run_backtest(df, _config(slippage=True))

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["signal_index"] == 0
    assert trade["entry_index"] == 1
    assert trade["entry_time"] == df.loc[1, "timestamp"]
    assert trade["entry_price_raw"] == pytest.approx(101.0)
    assert trade["entry_price"] == pytest.approx(101.25)
    assert trade["tp1"] == pytest.approx(126.25)
    assert trade["tp2"] == pytest.approx(151.25)
    assert trade["tp3"] == pytest.approx(176.25)
    assert trade["tp4"] == pytest.approx(201.25)


def test_short_entry_slippage_is_adverse_to_the_trader():
    df = _bars(4)
    _mark_short(df, 0)
    df.loc[1, "open"] = 101.0
    df.loc[1:, "high"] = 102.0
    df.loc[1:, "low"] = 100.0
    df.loc[1:, "close"] = 101.0

    trades = run_backtest(df, _config(slippage=True))

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["entry_price_raw"] == pytest.approx(101.0)
    assert trade["entry_price"] == pytest.approx(100.75)
    assert trade["tp1"] == pytest.approx(75.75)


def test_same_bar_stop_and_target_uses_stop_first_conservative_resolution():
    df = _bars(4)
    _mark_long(df, 0)

    # Entry is 100. Fixed stop is 75 and TP1 is 125. Both are touched on
    # the entry bar. With conservative stop-first handling, the trade loses.
    df.loc[1, "open"] = 100.0
    df.loc[1, "high"] = 130.0
    df.loc[1, "low"] = 70.0
    df.loc[1, "close"] = 100.0

    trades = run_backtest(df, _config(slippage=False))

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "stop"
    assert bool(trade["stop_hit"])
    assert not bool(trade["tp1_hit"])
    assert trade["exit_index"] == 1
    assert trade["exit_price_raw"] == pytest.approx(75.0)


def test_second_signal_is_ignored_while_first_trade_is_still_open():
    df = _bars(6)
    _mark_long(df, 0, score=82.0)
    _mark_short(df, 2, score=90.0)

    trades = run_backtest(df, _config(slippage=False))

    assert len(trades) == 1
    assert trades.iloc[0]["signal_index"] == 0
    assert trades.iloc[0]["direction"] == "long"


def test_when_both_sides_signal_higher_score_wins():
    df = _bars(4)
    _mark_long(df, 0, score=85.0)
    _mark_short(df, 0, score=75.0)

    trades = run_backtest(df, _config(slippage=False))

    assert len(trades) == 1
    assert trades.iloc[0]["direction"] == "long"
    assert trades.iloc[0]["raw_score"] == pytest.approx(85.0)


def test_equal_long_short_scores_are_skipped_instead_of_guessing_direction():
    df = _bars(4)
    _mark_long(df, 0, score=80.0)
    _mark_short(df, 0, score=80.0)

    trades = run_backtest(df, _config(slippage=False))

    assert trades.empty


def test_incomplete_signal_bar_is_not_eligible_when_completed_bars_only_is_enabled():
    df = _bars(4)
    _mark_long(df, 0)
    df.loc[0, "bar_complete"] = False

    trades = run_backtest(df, _config(slippage=False))

    assert trades.empty, "An incomplete signal bar was allowed to create a trade"


def test_max_holding_time_excludes_bar_that_starts_at_the_deadline():
    df = _bars(6)
    _mark_long(df, 0)

    # Signal bar starts 13:30, entry is next-bar open at 13:31. With a
    # 2-minute maximum hold on left-labelled 1m bars, bars starting 13:31 and
    # 13:32 are eligible; the bar starting 13:33 is already at the deadline
    # and must not contribute price excursion or an additional minute of risk.
    df.loc[3, "high"] = 120.0
    df.loc[3, "low"] = 99.0

    trades = run_backtest(
        df,
        _config(maximum_holding_minutes=2, slippage=False),
    )

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["exit_reason"] == "max_holding_time"
    assert trade["entry_index"] == 1
    assert trade["exit_index"] == 2
    assert trade["mfe_points"] == pytest.approx(1.0)


def test_mfe_and_mae_begin_at_entry_bar_not_signal_bar():
    df = _bars(4)
    _mark_long(df, 0)

    # Extreme signal-bar prices existed before the next-bar-open entry and
    # therefore must never count toward the trade's MFE/MAE.
    df.loc[0, "high"] = 200.0
    df.loc[0, "low"] = 1.0
    df.loc[1:, "high"] = 103.0
    df.loc[1:, "low"] = 98.0

    trades = run_backtest(df, _config(slippage=False))

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["mfe_points"] == pytest.approx(3.0)
    assert trade["mae_points"] == pytest.approx(2.0)


def test_appending_future_bars_cannot_rewrite_an_already_completed_trade():
    prefix = _bars(4)
    _mark_long(prefix, 0)

    # The trade stops immediately on the entry bar, so later data must have no
    # effect on any execution or excursion field for this completed trade.
    prefix.loc[1, "low"] = 70.0

    future = _bars(3)
    future["timestamp"] = pd.date_range(
        prefix["timestamp"].iloc[-1] + pd.Timedelta(minutes=1),
        periods=3,
        freq="1min",
        tz="UTC",
    )
    future.loc[:, "open"] = [500.0, 10.0, 800.0]
    future.loc[:, "high"] = [900.0, 700.0, 1000.0]
    future.loc[:, "low"] = [1.0, 2.0, 3.0]
    future.loc[:, "close"] = [600.0, 20.0, 900.0]

    extended = pd.concat([prefix, future], ignore_index=True)

    prefix_trade = run_backtest(prefix, _config(slippage=False)).iloc[0]
    extended_trade = run_backtest(extended, _config(slippage=False)).iloc[0]

    columns = [
        "signal_index",
        "entry_index",
        "exit_index",
        "direction",
        "entry_price_raw",
        "entry_price",
        "stop_price",
        "tp1",
        "tp2",
        "tp3",
        "tp4",
        "exit_reason",
        "exit_price_raw",
        "exit_price",
        "net_result_points",
        "mfe_points",
        "mae_points",
        "bars_held",
        "maximum_target_reached",
    ]

    for column in columns:
        left = prefix_trade[column]
        right = extended_trade[column]
        if isinstance(left, (float, np.floating)):
            assert right == pytest.approx(left), column
        else:
            assert right == left, column


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('enabled,cost,unit,point_value,quantity,expected', [
    (False, 2.0, 'points', 2.0, 1, 0.0),
    (True, 0.0, 'points', 2.0, 1, 0.0),
    (True, 1.5, 'points', 2.0, 1, 1.5),
    (True, 3.0, 'dollars', 2.0, 10, 1.5),
    (True, 30.0, 'dollars', 20.0, 3, 1.5),
])
def test_commission_net_points_r_and_position_quantity(direction, enabled, cost, unit, point_value, quantity, expected):
    df = _bars(4)
    (_mark_long if direction == 'long' else _mark_short)(df, 0)
    df.loc[1:, 'close'] = 104.0 if direction == 'long' else 96.0
    config = _config(slippage=True)
    config['market'] = {'point_value': point_value}
    config['backtest']['quantity'] = quantity
    config['backtest']['commission'] = {'enabled': enabled, 'unit': unit, 'per_contract_round_trip': cost}
    trade = run_backtest(df, config).iloc[0]
    assert trade.gross_result_points == pytest.approx(3.5)
    assert trade.commission_cost == expected
    assert trade.net_result_points == pytest.approx(3.5 - expected)
    assert trade.net_result_r == pytest.approx((3.5 - expected) / 25)
    if quantity != 1:
        assert trade.position_net_points == pytest.approx((3.5 - expected) * quantity)
        assert trade.position_commission_points == expected * quantity


@pytest.mark.parametrize('commission', [
    {'unit': 'euros'}, {'per_contract_round_trip': -1},
    {'per_contract_round_trip': float('nan')}, {'unit': 'dollars'},
])
def test_ambiguous_or_invalid_commission_fails_closed(commission):
    from backtest import build_backtest_settings
    config = _config()
    config['backtest']['commission'].update(commission)
    with pytest.raises(BacktestError):
        build_backtest_settings(config)


@pytest.mark.parametrize('quantity', [0, -1, 1.5, True])
def test_invalid_position_quantity_is_rejected(quantity):
    from backtest import build_backtest_settings
    config = _config()
    config['backtest']['quantity'] = quantity
    with pytest.raises(BacktestError, match='quantity'):
        build_backtest_settings(config)


@pytest.mark.parametrize('direction,opening,high,low,expected', [
    ('long', 60, 65, 55, 60), ('short', 140, 145, 135, 140),
])
def test_gap_through_stop_fills_at_adverse_open(direction, opening, high, low, expected):
    df = _bars(4)
    (_mark_long if direction == 'long' else _mark_short)(df, 0)
    df.loc[2, ['open', 'high', 'low', 'close']] = [opening, high, low, opening]
    trade = run_backtest(df, _config(slippage=True)).iloc[0]
    assert trade.exit_reason == 'stop'
    assert trade.exit_price_raw == expected
    assert trade.exit_price == expected + (-0.25 if direction == 'long' else 0.25)


@pytest.mark.parametrize('direction,opening,high,low,target', [
    ('long', 220, 225, 70, 200), ('short', -20, 130, -25, 0),
])
def test_gap_through_terminal_target_is_known_before_intrabar_stop(direction, opening, high, low, target):
    df = _bars(4)
    (_mark_long if direction == 'long' else _mark_short)(df, 0)
    df.loc[2, ['open', 'high', 'low', 'close']] = [opening, high, low, opening]
    trade = run_backtest(df, _config(slippage=False)).iloc[0]
    assert trade.exit_reason == 'tp4'
    assert trade.exit_price_raw == target  # Conservative limit fill, no favorable gap improvement.
    assert trade.maximum_target_reached == 4


def test_next_observed_bar_across_session_gap_is_not_a_next_bar_entry():
    df = _bars(3)
    _mark_long(df, 0)
    df.loc[1:, 'timestamp'] += pd.Timedelta(days=1)
    assert run_backtest(df, _config(slippage=False)).empty


def test_session_gap_beyond_holding_deadline_uses_last_observed_close():
    df = _bars(4)
    _mark_long(df, 0)
    df.loc[2:, 'timestamp'] += pd.Timedelta(days=1)
    df.loc[1, 'close'] = 103
    df.loc[2:, 'low'] = 1
    trade = run_backtest(df, _config(slippage=False)).iloc[0]
    assert trade.exit_reason == 'max_holding_time'
    assert trade.exit_index == 1
    assert trade.exit_price_raw == 103
    assert trade.mae_points == 1


@pytest.mark.parametrize('direction', ['long', 'short'])
def test_end_of_data_closes_full_position_with_adverse_exit_slippage(direction):
    df = _bars(3)
    (_mark_long if direction == 'long' else _mark_short)(df, 0)
    trade = run_backtest(df, _config(slippage=True)).iloc[0]
    assert trade.exit_reason == 'end_of_data'
    assert trade.exit_index == 2
    assert trade.gross_result_points == -0.5


@pytest.mark.parametrize('direction', ['long', 'short'])
def test_same_bar_terminal_target_and_stop_remains_stop_first_without_open_gap(direction):
    df = _bars(3)
    (_mark_long if direction == 'long' else _mark_short)(df, 0)
    df.loc[1, ['high', 'low']] = [210, -10]
    trade = run_backtest(df, _config(slippage=False)).iloc[0]
    assert trade.exit_reason == 'stop'
    assert trade.net_result_points == -25
    assert not trade.tp4_hit


def test_optional_missing_snr_does_not_break_backtest_report():
    from backtest import performance_by_snr_bucket
    df = _bars(3)
    _mark_long(df, 0)
    trades = run_backtest(df, _config(slippage=False))
    assert performance_by_snr_bucket(trades).empty
