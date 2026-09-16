import pandas as pd

from execution_confirmation_research import (
    enrich,
    analyze,
)


def test_exp021_smoke():
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

    features = pd.DataFrame({
        "timestamp": pd.to_datetime(
            ["2025-01-02T14:32:00Z"]
        ),

        "bullish_structure_close_break": [True],
        "bearish_structure_close_break": [False],

        "bullish_structure_wick_break": [True],
        "bearish_structure_wick_break": [False],

        "structure_break_confirmation": ["body_close"],

        "structure_break_timestamp": pd.to_datetime(
            ["2025-01-02T14:31:00Z"]
        ),

        "structure_break_available_at": pd.to_datetime(
            ["2025-01-02T14:32:00Z"]
        ),

        "bullish_structure_reclaim_event": [True],
        "bearish_structure_reclaim_event": [False],

        "bullish_fvg_first_touch": [True],
        "bearish_fvg_first_touch": [False],

        "bullish_fvg_retest_hold": [True],
        "bearish_fvg_retest_hold": [False],

        "bullish_reversal_entry_valid_event": [False],
        "bearish_reversal_entry_valid_event": [False],

        "bullish_continuation_entry_valid_event": [True],
        "bearish_continuation_entry_valid_event": [False],

        "bullish_entry_valid_event": [True],
        "bearish_entry_valid_event": [False],

        "entry_valid_direction": ["bullish"],
    })

    x = enrich(ledger, features)

    assert x.iloc[0]["feature_matched"]
    assert x.iloc[0]["break_mode"] == "close_and_wick"
    assert x.iloc[0]["confirmation_delay_bucket"] == "0-1m"
    assert x.iloc[0]["fvg_confirmation_state"] == "first_touch_and_hold"
    assert x.iloc[0]["entry_valid_family"] == "continuation"

    result, _ = analyze({
        2023: x.copy(),
        2024: x.copy(),
        2025: x.copy(),
    })

    assert result["coverage"]["matched"] == 3
