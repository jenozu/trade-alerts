"""Tests for the isolated R5.1 structural stop-loss sweep."""
from copy import deepcopy

import pandas as pd
import pytest

from backtest import build_backtest_settings, determine_stop_price
from scripts.run_r51_structural_stop_sweep import (
    MODELS,
    config_for_structural_model,
    stop_distance_summary,
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
        "slippage": {
            "enabled": True,
            "points_per_entry": 0.25,
            "points_per_exit": 0.25,
        },
    },
    "scoring": {"positive_weights": {"displacement": 12}},
}


@pytest.mark.parametrize("model", MODELS)
def test_structural_model_changes_only_stop_family(model):
    original = deepcopy(BASE)
    result = config_for_structural_model(BASE, model)

    expected_method = {
        "STRUCTURAL_RAW": "structural_raw",
        "STRUCTURAL_CAP_25": "structural_cap",
    }[model]
    assert result["stop_loss"]["primary_method"] == expected_method
    assert result["take_profit"] == original["take_profit"]
    assert result["trade_management"] == original["trade_management"]
    assert result["backtest"] == original["backtest"]
    assert result["scoring"] == original["scoring"]
    assert BASE == original


def test_rejects_unknown_structural_model():
    with pytest.raises(ValueError):
        config_for_structural_model(BASE, "STRUCTURAL_CAP_30")


@pytest.mark.parametrize(
    "model,structural_low,expected",
    [
        ("CONTROL", 88.0, 75.0),          # 10-point structure is below 20-point floor -> fixed 25
        ("STRUCTURAL_RAW", 88.0, 86.0),   # swing low 88 minus 2-point buffer
        ("STRUCTURAL_CAP_25", 88.0, 86.0),
        ("CONTROL", 68.0, 75.0),          # 30-point structure is above 25-point ceiling -> fixed 25
        ("STRUCTURAL_RAW", 68.0, 66.0),
        ("STRUCTURAL_CAP_25", 68.0, 75.0),
    ],
)
def test_structural_stop_modes(model, structural_low, expected):
    config = deepcopy(BASE)
    if model != "CONTROL":
        config = config_for_structural_model(config, model)

    settings = build_backtest_settings(config)
    row = pd.Series(
        {
            "active_internal_swing_low": structural_low,
            "active_external_swing_low": None,
        }
    )

    stop = determine_stop_price(
        row,
        entry_price=100.0,
        direction="long",
        settings=settings,
    )
    assert stop == pytest.approx(expected)


def test_structural_modes_fall_back_when_structure_missing():
    for model in MODELS:
        config = config_for_structural_model(BASE, model)
        settings = build_backtest_settings(config)
        row = pd.Series(
            {
                "active_internal_swing_low": None,
                "active_external_swing_low": None,
            }
        )
        stop = determine_stop_price(
            row,
            entry_price=100.0,
            direction="long",
            settings=settings,
        )
        assert stop == pytest.approx(75.0)


def test_stop_distance_summary_reports_distribution():
    trades = pd.DataFrame({"stop_distance_points": [10.0, 15.0, 25.0, 40.0]})
    result = stop_distance_summary(2023, "X", trades)

    assert result["trades"] == 4
    assert result["median_stop_points"] == pytest.approx(20.0)
    assert result["pct_below_15"] == pytest.approx(0.25)
    assert result["pct_below_20"] == pytest.approx(0.50)
    assert result["pct_above_25"] == pytest.approx(0.25)
    assert result["pct_above_35"] == pytest.approx(0.25)
