"""Unit checks for R4.6 descriptive threshold audit."""
import pandas as pd
import pytest

from scripts.run_r46_threshold_diagnostics import (
    REQUIRED, analyze, cohort_metrics, load_ledgers, THRESHOLDS,
)


def fixture_trade(score=75., pnl=25., stop=False):
    return {
        "raw_score": score, "net_result_points": pnl,
        "net_result_r": pnl / 25,
        "tp1_hit": pnl > 0, "tp2_hit": False,
        "tp3_hit": False, "tp4_hit": False, "stop_hit": stop,
        "direction": "long", "session_date": "2024-04-01",
        "entry_time": "2024-04-01T13:32:00Z",
    }


def test_threshold_retention_and_stop_rate():
    frame = pd.DataFrame([
        fixture_trade(60., -25., True),
        fixture_trade(75., 25.),
        fixture_trade(85., 50.),
    ])
    result = cohort_metrics(frame[frame.raw_score >= 75], 3)
    assert result["trades"] == 2
    assert result["net_points"] == 75.
    assert result["executed_trade_retention"] == 0.666667
    assert result["stop_hit_rate"] == 0.
    assert len(THRESHOLDS) == 6


def test_empty_cohort_has_no_fabricated_profit_factor():
    frame = pd.DataFrame([fixture_trade(60., -25., True)])
    result = cohort_metrics(frame[frame.raw_score >= 85], 1)
    assert result["trades"] == 0
    assert result["profit_factor"] is None
    assert result["net_points"] == 0.


def test_load_requires_core_trade_fields(tmp_path):
    path = tmp_path / "2023" / "baseline"
    path.mkdir(parents=True)
    pd.DataFrame([{"raw_score": 75}]).to_csv(path / "trades.csv", index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_ledgers(tmp_path)
