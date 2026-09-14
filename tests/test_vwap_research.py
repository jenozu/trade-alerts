import pandas as pd

from vwap_research import (
    enrich,
    analyze,
)


def test_exp017_smoke():
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
        "liquidity_sweep": [False],
    })

    features = pd.DataFrame({
        "timestamp": pd.to_datetime(
            ["2025-01-02T14:32:00Z"]
        ),
        "vwap": [100.0],
        "vwap_distance_points": [5.0],
        "vwap_distance_pct": [0.05],
        "vwap_position": ["above"],
        "vwap_bullish_cross": [True],
        "vwap_bearish_cross": [False],
        "vwap_slope_points_per_bar": [0.4],
        "vwap_slope_direction": ["bullish"],
    })

    x = enrich(
        ledger,
        features,
    )

    assert x.iloc[0]["feature_matched"]
    assert (
        x.iloc[0]["vwap_directional_position"]
        == "with_side"
    )
    assert (
        x.iloc[0]["vwap_slope_alignment"]
        == "aligned"
    )

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
