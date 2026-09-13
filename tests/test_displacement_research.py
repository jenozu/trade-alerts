import pandas as pd

from displacement_research import (
    analyze_displacement,
    enrich_displacement_context,
)


def test_exp009_smoke():
    ledger = pd.DataFrame({
        "signal_time": pd.to_datetime([
            "2025-01-02T14:32:00Z"
        ]),
        "direction": ["long"],
        "raw_score": [80.0],
        "net_result_points": [25.0],
        "tp1_hit": [True],
        "tp2_hit": [False],
        "tp3_hit": [False],
        "tp4_hit": [False],
        "stop_hit": [False],
        "mfe_points": [30.0],
        "mae_points": [10.0],
        "liquidity_sweep": [True],
    })

    features = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2025-01-02T14:32:00Z"
        ]),
        "bullish_displacement": [True],
        "bearish_displacement": [False],
        "displacement_any": [True],
        "displacement_direction": ["bullish"],
        "displacement_score": [85.0],
        "displacement_category": ["strong"],
        "displacement_atr": [10.0],
        "displacement_body": [8.0],
        "displacement_range": [12.0],
        "displacement_body_atr_ratio": [0.8],
        "displacement_range_atr_ratio": [1.2],
        "displacement_close_location": [0.9],
        "displacement_rvol": [1.8],
        "bullish_structure_break": [True],
        "bearish_structure_break": [False],
        "bullish_mss": [True],
        "bearish_mss": [False],
        "bullish_choch": [False],
        "bearish_choch": [False],
        "bullish_bos": [True],
        "bearish_bos": [False],
        "bullish_fvg_created": [True],
        "bearish_fvg_created": [False],
    })

    out = enrich_displacement_context(
        ledger,
        features,
    )

    assert out.iloc[0]["feature_matched"]
    assert out.iloc[0]["directional_displacement"]

    result, _ = analyze_displacement({
        2023: out.copy(),
        2024: out.copy(),
        2025: out.copy(),
    })

    assert result["coverage"]["total_trades"] == 3
