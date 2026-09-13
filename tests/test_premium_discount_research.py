import pandas as pd

from premium_discount_research import enrich, analyze


def test_exp013_smoke():
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
        "internal_premium_discount": ["discount"],
        "external_premium_discount": ["discount"],
        "internal_dealing_range_high": [110.0],
        "internal_dealing_range_low": [90.0],
        "internal_dealing_equilibrium": [100.0],
        "internal_dealing_percentile": [0.25],
        "internal_dealing_location": ["discount"],
        "internal_dealing_distance_to_equilibrium": [5.0],
        "internal_dealing_valid": [True],
        "external_dealing_range_high": [120.0],
        "external_dealing_range_low": [80.0],
        "external_dealing_equilibrium": [100.0],
        "external_dealing_percentile": [0.30],
        "external_dealing_location": ["discount"],
        "external_dealing_distance_to_equilibrium": [6.0],
        "external_dealing_valid": [True],
        "draw_on_liquidity_direction": ["bullish"],
        "dol_direction": ["bullish"],
        "dol_primary_direction": ["bullish"],
        "dol_primary_confidence": [0.8],
    })

    x = enrich(ledger, features)

    assert x.iloc[0]["internal_directional_pd"] == "favorable"
    assert x.iloc[0]["dol_alignment"] == "aligned"

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
