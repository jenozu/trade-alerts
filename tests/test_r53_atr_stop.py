"""Tests for R5.3 ATR / volatility-adjusted stop research."""
from copy import deepcopy

import pandas as pd
import pytest

from backtest import build_backtest_settings, determine_stop_price
from scripts.run_r53_atr_stop import ATR_MODELS, add_atr14, config_for_atr


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
        "slippage": {
            "enabled": True,
            "points_per_entry": 0.25,
            "points_per_exit": 0.25,
        },
    },
}


def test_add_atr14_is_causal_and_requires_full_window():
    frame = pd.DataFrame(
        {
            "high": [11.0, 12.0, 13.0, 14.0],
            "low": [9.0, 10.0, 11.0, 12.0],
            "close": [10.0, 11.0, 12.0, 13.0],
        }
    )
    result = add_atr14(frame, period=3)

    assert pd.isna(result.loc[0, "atr_14_points"])
    assert pd.isna(result.loc[1, "atr_14_points"])
    assert result.loc[2, "atr_14_points"] == pytest.approx(2.0)
    assert result.loc[3, "atr_14_points"] == pytest.approx(2.0)


@pytest.mark.parametrize("model,multiplier", ATR_MODELS.items())
def test_config_changes_only_stop_family(model, multiplier):
    original = deepcopy(BASE)
    result = config_for_atr(BASE, multiplier)

    assert result["stop_loss"]["primary_method"] == "atr"
    assert result["stop_loss"]["atr"] == {
        "period": 14,
        "multiplier": multiplier,
    }
    assert result["take_profit"] == original["take_profit"]
    assert result["trade_management"] == original["trade_management"]
    assert result["backtest"] == original["backtest"]
    assert BASE == original


def test_rejects_unplanned_atr_multiplier():
    with pytest.raises(ValueError):
        config_for_atr(BASE, 1.25)


@pytest.mark.parametrize(
    "direction,multiplier,expected",
    [
        ("long", 1.0, 90.0),
        ("long", 1.5, 85.0),
        ("long", 2.0, 80.0),
        ("short", 1.0, 110.0),
        ("short", 1.5, 115.0),
        ("short", 2.0, 120.0),
    ],
)
def test_atr_stop_distance(direction, multiplier, expected):
    config = config_for_atr(BASE, multiplier)
    settings = build_backtest_settings(config)
    row = pd.Series({"atr_14_points": 10.0})

    stop = determine_stop_price(
        row,
        entry_price=100.0,
        direction=direction,
        settings=settings,
    )
    assert stop == pytest.approx(expected)


def test_missing_atr_falls_back_to_fixed_25():
    config = config_for_atr(BASE, 1.5)
    settings = build_backtest_settings(config)
    row = pd.Series({"atr_14_points": None})

    stop = determine_stop_price(
        row,
        entry_price=100.0,
        direction="long",
        settings=settings,
    )
    assert stop == pytest.approx(75.0)
