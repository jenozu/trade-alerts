from __future__ import annotations

import pandas as pd
import pytest

from path_exit_simulator import (
    ExitLeg,
    ExitModel,
    compare_path_exit_models,
    simulate_model_for_trade,
)


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=6, freq="1min", tz="UTC"),
            "open": [100, 100, 100, 100, 100, 100],
            "high": [100, 126, 151, 176, 201, 201],
            "low": [100, 99, 124, 149, 174, 199],
            "close": [100, 125, 150, 175, 200, 200],
        }
    )


def _trade() -> pd.Series:
    return pd.Series(
        {
            "trade_id": 1,
            "entry_index": 1,
            "exit_index": 4,
            "direction": "long",
            "entry_time": pd.Timestamp("2026-01-01 00:01:00", tz="UTC"),
            "entry_price": 100.0,
            "stop_price": 75.0,
            "stop_distance_points": 25.0,
            "tp1": 125.0,
            "tp2": 150.0,
            "tp3": 175.0,
            "tp4": 200.0,
            "exit_reason": "tp4",
            "exit_price_raw": 200.0,
            "net_result_points": 99.75,
        }
    )


def test_current_baseline_reproduces_existing_tp4_result():
    model = ExitModel("current_baseline", (ExitLeg(1.0, 4),))
    result = simulate_model_for_trade(
        _bars(),
        _trade(),
        model,
        exit_slippage_points=0.25,
    )
    assert result["net_result_points"] == pytest.approx(99.75)
    assert result["exit_reason"] == "tp4"


def test_half_tp1_half_tp4_weights_realized_legs():
    model = ExitModel(
        "half_tp1_half_tp4",
        (ExitLeg(0.5, 1), ExitLeg(0.5, 4)),
    )
    result = simulate_model_for_trade(
        _bars(),
        _trade(),
        model,
        exit_slippage_points=0.25,
    )
    expected = 0.5 * 24.75 + 0.5 * 99.75
    assert result["net_result_points"] == pytest.approx(expected)
    assert result["targets_filled"] == "1,4"


def test_breakeven_activates_on_next_bar_not_same_ohlc_bar():
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="1min", tz="UTC"),
            "open": [100, 100, 100, 100],
            "high": [100, 126, 101, 101],
            "low": [100, 99, 99, 99],
            "close": [100, 125, 100, 100],
        }
    )
    trade = _trade().copy()
    trade["exit_index"] = 3
    trade["exit_reason"] = "max_holding_time"
    trade["exit_price_raw"] = 100.0

    model = ExitModel(
        "half_tp1_be_half_tp4",
        (ExitLeg(0.5, 1), ExitLeg(0.5, 4)),
        breakeven_after_target=1,
    )
    result = simulate_model_for_trade(
        bars,
        trade,
        model,
        exit_slippage_points=0.25,
    )
    assert result["exit_reason"] == "breakeven_stop"
    assert result["net_result_points"] == pytest.approx(
        0.5 * 24.75 + 0.5 * -0.25
    )


def test_same_bar_stop_and_target_is_stop_first():
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="1min", tz="UTC"),
            "open": [100, 100, 100],
            "high": [100, 126, 100],
            "low": [100, 74, 100],
            "close": [100, 100, 100],
        }
    )
    trade = _trade().copy()
    trade["exit_index"] = 1
    trade["exit_reason"] = "stop"
    trade["exit_price_raw"] = 75.0
    trade["net_result_points"] = -25.25

    model = ExitModel(
        "half_tp1_half_tp4",
        (ExitLeg(0.5, 1), ExitLeg(0.5, 4)),
    )
    result = simulate_model_for_trade(
        bars,
        trade,
        model,
        exit_slippage_points=0.25,
        stop_first=True,
    )
    assert result["targets_filled"] == ""
    assert result["net_result_points"] == pytest.approx(-25.25)


def test_comparison_reports_drawdown_and_losing_streak():
    bars = _bars()
    trade = _trade()
    trades = pd.DataFrame([trade, trade.assign(trade_id=2) if hasattr(trade, "assign") else trade])
    # Build explicitly because Series has no assign method.
    trades = pd.DataFrame([_trade().to_dict(), {**_trade().to_dict(), "trade_id": 2}])
    summary, detail = compare_path_exit_models(
        bars,
        trades,
        exit_slippage_points=0.25,
        models=[ExitModel("current_baseline", (ExitLeg(1.0, 4),))],
    )
    assert len(detail) == 2
    assert "max_drawdown_points" in summary.columns
    assert "longest_losing_streak" in summary.columns
