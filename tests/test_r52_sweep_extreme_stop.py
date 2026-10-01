"""Tests for R5.2 sweep-extreme stop research."""
from copy import deepcopy

import pandas as pd
import pytest

from backtest import build_backtest_settings, determine_stop_price
from scripts.run_r52_sweep_extreme_stop import (
    add_recent_sweep_extremes,
    config_for_sweep_extreme,
)


BASE = {
    "stop_loss": {
        "primary_method": "structural",
        "structural": {"buffer_points": 2.0},
        "preferred_initial_range_points": {"minimum": 20, "maximum": 25},
        "fixed_research_values_points": [15, 20, 25, 30, 35],
    },
    "take_profit": {
        "preferred_initial": {
            "tp1_points": 25,
            "tp2_points": 50,
            "tp3_points": 75,
            "tp4_points": 100,
        }
    },
    "trade_management": {
        "maximum_holding_minutes": 60,
        "maximum_one_open_trade": True,
    },
    "backtest": {
        "use_completed_bars_only": True,
        "entry_on_next_bar_open": True,
        "conservative_same_bar_resolution": True,
        "same_bar_stop_and_target_behavior": "stop_first",
        "commission": {"enabled": False, "per_contract_round_trip": 0.0},
        "slippage": {"enabled": True, "points_per_entry": 0.25, "points_per_exit": 0.25},
    },
}


def test_config_changes_only_stop_method():
    original = deepcopy(BASE)
    result = config_for_sweep_extreme(BASE)
    assert result["stop_loss"]["primary_method"] == "sweep_extreme"
    assert result["take_profit"] == original["take_profit"]
    assert result["trade_management"] == original["trade_management"]
    assert result["backtest"] == original["backtest"]
    assert BASE == original


def test_recent_sweep_extreme_is_causal_and_expires():
    frame = pd.DataFrame(
        {
            "low": [100, 98, 99, 101, 102],
            "high": [101, 100, 101, 103, 104],
            "sell_side_liquidity_sweep": [False, True, False, False, False],
            "buy_side_liquidity_sweep": [False, False, False, True, False],
        }
    )
    result = add_recent_sweep_extremes(frame, lookback_bars=3)

    assert pd.isna(result.loc[0, "recent_sell_side_sweep_extreme_low"])
    assert result.loc[1, "recent_sell_side_sweep_extreme_low"] == 98
    assert result.loc[2, "recent_sell_side_sweep_extreme_low"] == 98
    assert result.loc[3, "recent_sell_side_sweep_extreme_low"] == 98
    assert pd.isna(result.loc[4, "recent_sell_side_sweep_extreme_low"])

    assert result.loc[3, "recent_buy_side_sweep_extreme_high"] == 103
    assert result.loc[4, "recent_buy_side_sweep_extreme_high"] == 103


def test_long_stop_uses_sell_side_sweep_low_plus_existing_buffer():
    config = config_for_sweep_extreme(BASE)
    settings = build_backtest_settings(config)
    row = pd.Series({"recent_sell_side_sweep_extreme_low": 90.0})
    stop = determine_stop_price(row, entry_price=100.0, direction="long", settings=settings)
    assert stop == pytest.approx(88.0)


def test_short_stop_uses_buy_side_sweep_high_plus_existing_buffer():
    config = config_for_sweep_extreme(BASE)
    settings = build_backtest_settings(config)
    row = pd.Series({"recent_buy_side_sweep_extreme_high": 110.0})
    stop = determine_stop_price(row, entry_price=100.0, direction="short", settings=settings)
    assert stop == pytest.approx(112.0)


def test_missing_or_invalid_sweep_extreme_falls_back_to_fixed_25():
    config = config_for_sweep_extreme(BASE)
    settings = build_backtest_settings(config)

    missing = pd.Series({"recent_sell_side_sweep_extreme_low": None})
    assert determine_stop_price(missing, entry_price=100.0, direction="long", settings=settings) == pytest.approx(75.0)

    invalid = pd.Series({"recent_sell_side_sweep_extreme_low": 105.0})
    assert determine_stop_price(invalid, entry_price=100.0, direction="long", settings=settings) == pytest.approx(75.0)
