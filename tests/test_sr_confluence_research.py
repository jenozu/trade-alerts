import pandas as pd

from sr_confluence_research import (
    enrich,
    analyze,
)


def test_exp018_smoke():
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

        "long_score_detail_key_location_confluence_aligned": [1.0],
        "short_score_detail_key_location_confluence_aligned": [0.0],

        "long_score_detail_key_location_confluence_score": [76.666667],
        "short_score_detail_key_location_confluence_score": [30.0],

        "internal_swing_high_equal_cluster_count": [0],
        "internal_swing_low_equal_cluster_count": [2],
        "external_swing_high_equal_cluster_count": [0],
        "external_swing_low_equal_cluster_count": [1],
    })

    x = enrich(
        ledger,
        features,
    )

    assert x.iloc[0]["feature_matched"]

    assert (
        x.iloc[0]["directional_confluence_aligned"]
        == True
    )

    assert (
        round(
            x.iloc[0]["directional_confluence_score"],
            2,
        )
        == 76.67
    )

    assert x.iloc[0]["equal_cluster_total"] == 3

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
