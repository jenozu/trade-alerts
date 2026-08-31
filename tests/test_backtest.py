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
