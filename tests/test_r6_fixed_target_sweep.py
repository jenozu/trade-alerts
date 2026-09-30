"""Tests for the isolated R6.0 fixed full-target sweep."""
from copy import deepcopy

import pytest

from scripts.run_r6_fixed_target_sweep import config_for_full_target


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
        "preferred_initial_range_points": {"minimum": 20, "maximum": 25},
    },
    "scoring": {"positive_weights": {"displacement": 12}},
}


def test_tp100_is_identical_to_control_target_ladder():
    original = deepcopy(BASE)
    result = config_for_full_target(BASE, 100)
    assert result == original
    assert BASE == original


def test_tp50_changes_only_take_profit_ladder():
    original = deepcopy(BASE)
    result = config_for_full_target(BASE, 50)

    assert result["take_profit"]["preferred_initial"] == {
        "tp1_points": 25.0,
        "tp2_points": 50.0,
        "tp3_points": 50.0,
        "tp4_points": 50.0,
    }
    assert result["stop_loss"] == original["stop_loss"]
    assert result["scoring"] == original["scoring"]
    assert BASE == original


def test_tp75_changes_only_later_target():
    result = config_for_full_target(BASE, 75)
    assert result["take_profit"]["preferred_initial"] == {
        "tp1_points": 25.0,
        "tp2_points": 50.0,
        "tp3_points": 75.0,
        "tp4_points": 75.0,
    }


@pytest.mark.parametrize("value", [25, 60, 85, 125])
def test_rejects_unplanned_target_values(value):
    with pytest.raises(ValueError):
        config_for_full_target(BASE, value)
