"""Tests for the isolated R5.0 fixed stop-loss sweep."""
from copy import deepcopy

import pandas as pd
import pytest

from scripts.run_r5_fixed_stop_sweep import (
    FIXED_STOPS,
    config_for_fixed_stop,
    winner_survival,
)


BASE = {
    "take_profit": {
        "preferred_initial": {
            "tp1_points": 25,
            "tp2_points": 50,
            "tp3_points": 75,
            "tp4_points": 100,
        }
    },
    "stop_loss": {
        "primary_method": "structural",
        "structural": {"buffer_points": 2.0},
        "preferred_initial_range_points": {"minimum": 20, "maximum": 25},
        "fixed_research_values_points": [15, 20, 25, 30, 35],
    },
    "scoring": {"positive_weights": {"displacement": 12}},
    "trade_management": {"maximum_holding_minutes": 60},
    "backtest": {"slippage": {"enabled": True, "points_per_entry": 0.25, "points_per_exit": 0.25}},
}


@pytest.mark.parametrize("stop", FIXED_STOPS)
def test_fixed_stop_changes_only_stop_loss_family(stop):
    original = deepcopy(BASE)
    result = config_for_fixed_stop(BASE, stop)

    assert result["stop_loss"]["primary_method"] == "fixed"
    assert result["stop_loss"]["preferred_initial_range_points"] == {
        "minimum": float(stop),
        "maximum": float(stop),
    }
    assert result["take_profit"] == original["take_profit"]
    assert result["scoring"] == original["scoring"]
    assert result["trade_management"] == original["trade_management"]
    assert result["backtest"] == original["backtest"]
    assert BASE == original


@pytest.mark.parametrize("stop", [10, 17, 22, 40])
def test_rejects_unplanned_stop_values(stop):
    with pytest.raises(ValueError):
        config_for_fixed_stop(BASE, stop)


def test_winner_survival_uses_strict_stop_touch_boundary():
    control = pd.DataFrame(
        {
            "net_result_points": [100.0, 100.0, 100.0, -25.0],
            "mae_points": [14.75, 15.0, 34.75, 2.0],
        }
    )

    result = winner_survival(control).set_index("stop_points")

    assert result.loc[15, "baseline_winners"] == 3
    assert result.loc[15, "surviving_winners"] == 1
    assert result.loc[20, "surviving_winners"] == 2
    assert result.loc[35, "surviving_winners"] == 3
