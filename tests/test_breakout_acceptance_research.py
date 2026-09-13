import pandas as pd

from breakout_acceptance_research import (
    enrich_continuations,
    analyze_exp008,
)


def test_exp008_smoke():
    ledger = pd.DataFrame({
        "signal_time": pd.to_datetime(["2025-01-02T14:32:00Z"]),
        "direction": ["long"],
        "raw_score": [75.0],
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
        "timestamp": pd.to_datetime([
            "2025-01-02T14:30:00Z",
            "2025-01-02T14:31:00Z",
            "2025-01-02T14:32:00Z",
        ]),
        "open": [99, 100, 101],
        "high": [101, 102, 103],
        "low": [98, 99.5, 100.5],
        "close": [100.5, 101.5, 102],
        "bullish_structure_close_break": [False, True, True],
        "bearish_structure_close_break": [False]*3,
        "bullish_structure_wick_break": [False]*3,
        "bearish_structure_wick_break": [False]*3,
        "structure_break_direction": ["bullish"]*3,
        "structure_break_confirmation": ["close"]*3,
        "structure_broken_level": [100.0]*3,
        "structure_broken_timeframe": ["1m"]*3,
        "structure_break_timestamp": pd.to_datetime(
            ["2025-01-02T14:31:00Z"]*3
        ),
        "structure_break_displacement_score": [1.0]*3,
        "structure_break_displacement_category": ["medium"]*3,
        "structure_break_rvol": [1.5]*3,
    })

    out = enrich_continuations(ledger, features)

    assert out.iloc[0]["feature_matched"]
    assert out.iloc[0]["setup_family"] == "continuation"

    result, _ = analyze_exp008({
        2023: out.copy(),
        2024: out.copy(),
        2025: out.copy(),
    })

    assert result["coverage"]["continuation_trades"] == 3
