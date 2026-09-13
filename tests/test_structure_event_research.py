import pandas as pd

from structure_event_research import enrich, analyze


def test_exp010_smoke():
    ledger = pd.DataFrame({
        "signal_time": pd.to_datetime(["2025-01-02T14:32:00Z"]),
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
        "timestamp": pd.to_datetime(["2025-01-02T14:32:00Z"]),
        "bullish_mss": [True],
        "bearish_mss": [False],
        "bullish_choch": [True],
        "bearish_choch": [False],
        "bullish_bos": [False],
        "bearish_bos": [False],
        "recent_bullish_mss": [True],
        "recent_bearish_mss": [False],
        "recent_bullish_choch": [True],
        "recent_bearish_choch": [False],
        "recent_bullish_bos": [False],
        "recent_bearish_bos": [False],
        "bullish_structure_break": [True],
        "bearish_structure_break": [False],
        "recent_bullish_displacement": [True],
        "recent_bearish_displacement": [False],
    })

    x = enrich(ledger, features)

    assert x.iloc[0]["recent_mss"]
    assert x.iloc[0]["recent_choch"]

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
