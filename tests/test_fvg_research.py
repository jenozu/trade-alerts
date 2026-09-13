import pandas as pd

from fvg_research import enrich, analyze


def test_exp011_smoke():
    ledger = pd.DataFrame({
        "signal_time": pd.to_datetime(
            ["2025-01-02T14:32:00Z"]
        ),
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
        "timestamp": pd.to_datetime(
            ["2025-01-02T14:32:00Z"]
        ),
        "bullish_fvg_created": [True],
        "bearish_fvg_created": [False],
        "bullish_fvg_size_points": [4.0],
        "bearish_fvg_size_points": [None],
        "bullish_fvg_first_touch": [True],
        "bearish_fvg_first_touch": [False],
        "bullish_fvg_retest_hold": [True],
        "bearish_fvg_retest_hold": [False],
        "bullish_fvg_full_fill": [False],
        "bearish_fvg_full_fill": [False],
        "bullish_ifvg_created": [False],
        "bearish_ifvg_created": [False],
        "bullish_ifvg_created_recent": [False],
        "bearish_ifvg_created_recent": [False],
        "bullish_ifvg_respected_recent": [False],
        "bearish_ifvg_respected_recent": [False],
        "bullish_ifvg_disrespected_recent": [False],
        "bearish_ifvg_disrespected_recent": [False],
        "bullish_core_plus_fvg": [True],
        "bearish_core_plus_fvg": [False],
        "bullish_core_plus_fvg_retest": [True],
        "bearish_core_plus_fvg_retest": [False],
        "nearest_active_bullish_fvg_lower": [100.0],
        "nearest_active_bullish_fvg_upper": [104.0],
        "nearest_active_bearish_fvg_lower": [None],
        "nearest_active_bearish_fvg_upper": [None],
        "distance_to_bullish_fvg": [2.0],
        "distance_to_bearish_fvg": [None],
    })

    x = enrich(ledger, features)

    assert x.iloc[0]["directional_fvg_created"]
    assert x.iloc[0]["directional_fvg_retest_hold"]

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
