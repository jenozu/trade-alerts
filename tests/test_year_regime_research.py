from __future__ import annotations

import pandas as pd
import pytest

from year_regime_research import YearRegimeResearchError, analyze_year_regime, flatten_tables, markdown_report


def ledger(year: int) -> pd.DataFrame:
    return pd.DataFrame({
        "direction": ["long", "short", "long", "short"],
        "raw_score": [72, 75, 84, 88],
        "net_result_points": [10, -20, 40, 15] if year != 2024 else [5, -25, -10, 8],
        "net_result_r": [0.4, -0.8, 1.6, 0.6] if year != 2024 else [0.2, -1.0, -0.4, 0.32],
        "tp1_hit": [True, False, True, True],
        "tp2_hit": [False, False, True, False],
        "tp3_hit": [False, False, False, False],
        "tp4_hit": [False, False, False, False],
        "stop_hit": [False, True, False, False],
        "mfe_points": [20, 5, 50, 30],
        "mae_points": [8, 25, 10, 12],
        "minutes_held": [12, 18, 15, 9],
        "liquidity_sweep": [True, True, False, False],
        "displacement": [True, False, True, True],
        "structure_shift": [True, False, True, True],
        "fvg_context": [True, False, True, True],
        "htf_bias": ["bullish", "bearish", "bullish", "bearish"],
        "snr_1m": [1.1, 1.2, 1.8, 2.0],
        "snr_5m": [1.0, 1.1, 1.7, 1.9],
        "snr_15m": [1.2, 1.3, 2.0, 2.1],
        "rvol_rolling": [1.3, 1.4, 2.0, 2.2],
        "rvol_time_of_day": [1.2, 1.3, 1.8, 2.0],
    })


def test_exp004_reports_year_family_direction_band_and_context():
    result = analyze_year_regime({year: ledger(year) for year in (2023, 2024, 2025)})
    assert result["overall_by_year"]["2024"]["trades"] == 4
    assert result["by_year_setup_family"]["2024"]["reversal"]["trades"] == 2
    assert result["by_year_direction"]["2023"]["long"]["trades"] == 2
    assert "70-79" in result["by_year_score_band"]["2025"]
    assert "displacement" in result["contexts"]
    assert "snr_5m" in result["numeric_context"]
    assert result["delta_2024_vs_peer_mean"]["expectancy_points"]["delta"] < 0
    assert result["capabilities"]["volatility_regime_derivable"] is False
    assert not flatten_tables(result)["year_regime_metrics"].empty
    report = markdown_report(result, {2023: "a", 2024: "b", 2025: "c"})
    assert "2024 delta" in report and "Setup family by year" in report


def test_exp004_requires_exact_control_years():
    with pytest.raises(YearRegimeResearchError, match="exactly 2023, 2024, and 2025"):
        analyze_year_regime({2023: ledger(2023)})
