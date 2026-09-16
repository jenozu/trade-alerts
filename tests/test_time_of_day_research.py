import pandas as pd

from time_of_day_research import (
    enrich,
    analyze,
)


def test_exp020_timezone_and_bucket():
    ledger = pd.DataFrame({
        "signal_time": [
            "2025-01-02T14:32:00+00:00"
        ],
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

    x = enrich(ledger)

    assert (
        x.iloc[0]["signal_clock_et"]
        == "09:32"
    )

    assert (
        x.iloc[0]["time_bucket_5m"]
        == "09:30-09:34"
    )

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert (
        result["coverage"]["valid_signal_time"]
        == 3
    )
