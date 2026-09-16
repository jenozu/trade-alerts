import pandas as pd

from score_component_lift_research import (
    COMPONENTS,
    analyze,
    enrich,
)


def test_r42_smoke():
    ledger = pd.DataFrame({
        "signal_time": [
            "2025-01-02T14:32:00Z",
            "2025-01-02T14:33:00Z",
        ],

        "direction": [
            "long",
            "short",
        ],

        "raw_score": [
            80.0,
            75.0,
        ],

        "net_result_points": [
            25.0,
            -25.0,
        ],

        "tp1_hit": [
            True,
            False,
        ],

        "tp2_hit": [
            False,
            False,
        ],

        "tp3_hit": [
            False,
            False,
        ],

        "tp4_hit": [
            False,
            False,
        ],

        "stop_hit": [
            False,
            True,
        ],

        "mfe_points": [
            30.0,
            5.0,
        ],

        "mae_points": [
            5.0,
            25.0,
        ],

        "liquidity_sweep": [
            False,
            False,
        ],
    })

    data = {
        "timestamp": pd.to_datetime([
            "2025-01-02T14:32:00Z",
            "2025-01-02T14:33:00Z",
        ])
    }

    for long_col, short_col in (
        COMPONENTS.values()
    ):
        data[long_col] = [1.0, 0.0]
        data[short_col] = [0.0, 0.0]

    features = pd.DataFrame(data)

    x = enrich(
        ledger,
        features,
    )

    assert len(x) == 2
    assert x["feature_matched"].all()

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert (
        result["coverage"]["matched"]
        == 6
    )

    assert (
        "displacement"
        in result["components"]
    )
