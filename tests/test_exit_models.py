from __future__ import annotations

import pandas as pd

from analyze_exit_models import compare_exit_models


def _config() -> dict:
    return {
        "take_profit": {
            "preferred_initial": {
                "tp1_points": 25,
                "tp2_points": 50,
                "tp3_points": 75,
                "tp4_points": 100,
            }
        },
        "backtest": {
            "slippage": {
                "enabled": True,
                "points_per_exit": 0.25,
            }
        },
    }


def test_compare_exit_models_uses_milestones_without_changing_signals():
    trades = pd.DataFrame(
        {
            "net_result_points": [-25.25, 99.75, -10.0],
            "net_result_r": [-1.01, 3.99, -0.40],
            "stop_distance_points": [25.0, 25.0, 25.0],
            "tp1_hit": [True, True, False],
            "tp2_hit": [False, True, False],
            "tp3_hit": [False, True, False],
            "tp4_hit": [False, True, False],
        }
    )

    result = compare_exit_models(trades, _config()).set_index("model")

    assert result.loc["current_baseline", "trades"] == 3
    assert result.loc["full_exit_tp1", "wins"] == 2
    assert result.loc["full_exit_tp1", "losses"] == 1
    assert result.loc["full_exit_tp1", "total_points"] == 39.5

    assert result.loc["full_exit_tp2", "wins"] == 1
    assert result.loc["full_exit_tp2", "total_points"] == 14.5

    assert result.loc["full_exit_tp3", "wins"] == 1
    assert result.loc["full_exit_tp3", "total_points"] == 39.5

    # The existing simulator already exits fully at TP4, so this model should
    # reproduce the baseline results exactly.
    assert result.loc["full_exit_tp4", "expectancy_delta_vs_baseline"] == 0.0
