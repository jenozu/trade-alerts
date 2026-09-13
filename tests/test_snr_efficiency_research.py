import pandas as pd

from snr_efficiency_research import (
    enrich,
    analyze,
)


def test_exp016_smoke():
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

        "snr_1m": [2.0],
        "snr_direction_1m": ["bullish"],
        "snr_delta_1m": [0.2],
        "snr_slope_1m": [0.1],
        "efficiency_1m": [0.7],

        "snr_5m": [2.2],
        "snr_direction_5m": ["bullish"],
        "snr_delta_5m": [0.3],
        "snr_slope_5m": [0.15],
        "efficiency_5m": [0.75],

        "snr_15m": [2.4],
        "snr_direction_15m": ["bullish"],
        "snr_delta_15m": [0.4],
        "snr_slope_15m": [0.2],
        "efficiency_15m": [0.8],

        "snr_alignment": ["aligned"],
        "snr_composite_quality": [0.85],
        "snr_quality_class": ["high"],
        "snr_confidence_modifier_points": [2.0],
        "snr_confidence_modifier_enabled": [True],

        "long_score_signal_to_noise": [8.0],
        "short_score_signal_to_noise": [1.0],
    })

    x = enrich(
        ledger,
        features,
    )

    assert x.iloc[0]["feature_matched"]
    assert (
        x.iloc[0]["snr_trade_alignment_1m"]
        == "aligned"
    )

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
