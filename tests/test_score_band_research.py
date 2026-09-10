from __future__ import annotations

import pandas as pd

from score_band_research import analyze_score_bands, markdown_report


def ledger(scores: list[float], results: list[float], direction: str = "long") -> pd.DataFrame:
    return pd.DataFrame({
        "direction": [direction] * len(scores), "raw_score": scores,
        "net_result_points": results, "net_result_r": [value / 20 for value in results],
        "tp1_hit": [value > 0 for value in results], "tp2_hit": [value >= 25 for value in results],
        "tp3_hit": [value >= 50 for value in results], "tp4_hit": [value >= 75 for value in results],
        "stop_hit": [value < 0 for value in results], "mfe_points": [max(value, 0) for value in results],
        "mae_points": [min(value, 0) for value in results], "minutes_held": [10.0] * len(scores),
    })


def test_exp001_assigns_fixed_buckets_and_reports_segments():
    result = analyze_score_bands({2023: ledger([50, 59, 60, 90], [10, -10, 25, 100]), 2024: ledger([70, 80], [-20, 50], "short"), 2025: ledger([79, 89], [20, 30])})
    labels = [band["score_bucket"] for band in result["bands"]]
    assert labels == ["50-59", "60-69", "70-79", "80-89", "90-100"]
    band = next(item for item in result["bands"] if item["score_bucket"] == "50-59")
    assert band["overall"]["trades"] == 2
    assert band["overall"]["profit_factor"] == 1.0
    assert band["by_year"]["2024"]["trades"] == 0
    assert "Score buckets" in markdown_report(result, ledger_paths={2023: "a", 2024: "b", 2025: "c"})


def test_exp001_marks_insufficient_samples_without_claiming_monotonicity():
    result = analyze_score_bands({year: ledger([50, 60], [10, 20]) for year in (2023, 2024, 2025)})
    assert result["monotonicity"]["conclusion"] == "insufficient eligible score bands"
