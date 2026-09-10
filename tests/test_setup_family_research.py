from __future__ import annotations

import pandas as pd

from setup_family_research import (
    SetupFamilyResearchError,
    analyze_setup_families,
    derive_setup_family,
    flatten_tables,
    markdown_report,
)


def ledger() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "direction": ["long", "short", "long", "short"],
            "raw_score": [82, 76, 74, 88],
            "net_result_points": [30, -20, 10, 40],
            "net_result_r": [1.2, -0.8, 0.4, 1.6],
            "tp1_hit": [True, False, True, True],
            "tp2_hit": [False, False, False, True],
            "tp3_hit": [False, False, False, False],
            "tp4_hit": [False, False, False, False],
            "stop_hit": [False, True, False, False],
            "mfe_points": [40, 8, 20, 55],
            "mae_points": [8, 25, 10, 9],
            "minutes_held": [12, 9, 16, 20],
            "liquidity_sweep": [True, True, False, False],
            "displacement": [True, False, True, True],
            "structure_shift": [True, True, True, True],
            "fvg_context": [True, False, False, True],
            "htf_bias": ["bullish", "bearish", "bullish", "bearish"],
            "snr_1m": [1.8, 1.2, 1.6, 2.0],
            "rvol_rolling": [1.4, 1.1, 1.3, 1.8],
        }
    )


def test_family_derivation_matches_sweep_context():
    families = derive_setup_family(ledger())
    assert families.tolist() == ["reversal", "reversal", "continuation", "continuation"]


def test_exp003_reports_family_year_direction_score_and_context():
    frames = {year: ledger() for year in (2023, 2024, 2025)}
    result = analyze_setup_families(frames)
    assert result["overall"]["reversal"]["trades"] == 6
    assert result["overall"]["continuation"]["trades"] == 6
    assert result["by_direction"]["long"]["reversal"]["trades"] == 3
    assert "80-89" in result["score_bands"]
    assert "htf_alignment" in result["contexts"]
    assert "snr_1m" in result["numeric_context"]
    assert not flatten_tables(result)["setup_family_metrics"].empty
    text = markdown_report(result, {2023: "a", 2024: "b", 2025: "c"})
    assert "Year-by-year" in text
    assert "Capability / limitation flags" in text


def test_exp003_refuses_to_guess_without_family_contract():
    frame = ledger().drop(columns=["liquidity_sweep"])
    try:
        derive_setup_family(frame)
    except SetupFamilyResearchError as exc:
        assert "cannot be derived truthfully" in str(exc)
    else:
        raise AssertionError("expected SetupFamilyResearchError")
