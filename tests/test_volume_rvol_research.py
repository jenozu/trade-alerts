import pandas as pd

from volume_rvol_research import enrich, analyze


def test_exp015_smoke():
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
        "volume": [1000.0],
        "volume_percentile_rolling": [0.8],
        "rvol_rolling": [1.5],
        "volume_zscore": [1.2],
        "rvol_time_of_day": [1.4],
        "rvol_rolling_high": [True],
        "rvol_time_of_day_high": [True],
        "volume_zscore_high": [True],
        "volume_spike_rolling": [True],
        "volume_spike_time_of_day": [True],
        "volume_spike_both": [True],
        "volume_spike_any": [True],
        "rvol_agreement": [True],
        "bullish_volume_context": [True],
        "bearish_volume_context": [False],
        "bullish_volume_breakout": [True],
        "bearish_volume_breakout": [False],
        "bullish_volume_rejection": [False],
        "bearish_volume_rejection": [False],
        "bullish_pullback_low_volume": [False],
        "bearish_pullback_low_volume": [False],
        "volume_context": ["high"],
        "displacement_rvol": [1.6],
        "structure_break_rvol": [1.7],
    })

    x = enrich(ledger, features)

    assert x.iloc[0]["feature_matched"]
    assert x.iloc[0]["directional_volume_breakout"]
    assert x.iloc[0]["volume_spike_any"]

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
