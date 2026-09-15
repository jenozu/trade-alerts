import pandas as pd

from room_to_target_research import (
    enrich,
    analyze,
)


def test_exp019_smoke():

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

        "dol_distance_points": [75.0],
        "dol_primary_distance_points": [80.0],

        "dol_target_category": ["external"],
        "dol_primary_target_category": ["weekly"],

        "distance_to_unswept_liquidity_above": [62.0],
        "distance_to_unswept_liquidity_below": [35.0],

        "long_score_room_to_target": [8.0],
        "short_score_room_to_target": [2.0],

        "long_score_penalty_major_obstacle": [0.0],
        "short_score_penalty_major_obstacle": [1.0],
    })

    x = enrich(
        ledger,
        features,
    )

    assert x.iloc[0][
        "feature_matched"
    ]

    assert x.iloc[0][
        "dol_room_bucket"
    ] == "75-99"

    assert x.iloc[0][
        "unswept_room_bucket"
    ] == "50-74"

    assert not x.iloc[0][
        "major_obstacle"
    ]

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert (
        result["coverage"]["matched"]
        == 3
    )
