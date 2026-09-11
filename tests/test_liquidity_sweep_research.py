import pandas as pd

from liquidity_sweep_research import (
    analyze_liquidity_sweeps,
    enrich_trades_with_sweep_context,
)


def ledger():
    return pd.DataFrame({
        "signal_time": pd.to_datetime([
            "2025-01-02T14:32:00Z",
            "2025-01-02T14:34:00Z",
        ]),
        "direction": ["long", "short"],
        "raw_score": [75.0, 80.0],
        "net_result_points": [25.0, -25.0],
        "tp1_hit": [True, False],
        "tp2_hit": [False, False],
        "tp3_hit": [False, False],
        "tp4_hit": [False, False],
        "stop_hit": [False, True],
        "mfe_points": [30.0, 5.0],
        "mae_points": [10.0, 30.0],
        "liquidity_sweep": [True, False],
    })


def features():
    ts = pd.date_range(
        "2025-01-02T14:30:00Z",
        periods=5,
        freq="min",
    )

    return pd.DataFrame({
        "timestamp": ts,
        "high": [101, 101, 102, 103, 104],
        "low": [99, 98, 99, 100, 101],
        "buy_side_liquidity_sweep": [False]*5,
        "sell_side_liquidity_sweep": [False, True, False, False, False],
        "buy_side_sweep_source": [None]*5,
        "sell_side_sweep_source": [None, "pml", None, None, None],
        "buy_side_sweep_level": [None]*5,
        "sell_side_sweep_level": [None, 99.0, None, None, None],
        "bullish_displacement": [False, False, True, False, False],
        "recent_bullish_displacement": [False, False, True, True, True],
        "bullish_mss": [False, False, True, False, False],
        "recent_bullish_mss": [False, False, True, True, True],
        "bullish_choch": [False]*5,
        "recent_bullish_choch": [False]*5,
        "bullish_bos": [False]*5,
        "recent_bullish_bos": [False]*5,
        "bullish_fvg_created": [False, False, True, False, False],
        "bullish_fvg_retest_hold": [False]*5,
        "bullish_core_plus_fvg": [False]*5,
        "bullish_core_plus_fvg_retest": [False]*5,
        "bearish_displacement": [False]*5,
        "recent_bearish_displacement": [False]*5,
        "bearish_mss": [False]*5,
        "recent_bearish_mss": [False]*5,
        "bearish_choch": [False]*5,
        "recent_bearish_choch": [False]*5,
        "bearish_bos": [False]*5,
        "recent_bearish_bos": [False]*5,
        "bearish_fvg_created": [False]*5,
        "bearish_fvg_retest_hold": [False]*5,
        "bearish_core_plus_fvg": [False]*5,
        "bearish_core_plus_fvg_retest": [False]*5,
    })


def test_enrichment_finds_directional_sweep_and_confirmations():
    out = enrich_trades_with_sweep_context(
        ledger(),
        features(),
        lookback=10,
    )

    assert bool(out.iloc[0]["sweep_present_exact"])
    assert out.iloc[0]["sweep_side"] == "sell_side"
    assert out.iloc[0]["sweep_source"] == "pml"
    assert bool(out.iloc[0]["sweep_then_displacement"])
    assert bool(out.iloc[0]["sweep_then_mss"])
    assert bool(out.iloc[0]["sweep_then_fvg"])


def test_analysis_accepts_three_year_control_set():
    frame = enrich_trades_with_sweep_context(
        ledger(),
        features(),
        lookback=10,
    )

    result = analyze_liquidity_sweeps({
        2023: frame.copy(),
        2024: frame.copy(),
        2025: frame.copy(),
    })

    assert result["coverage"]["match_rate"] == 1.0
    assert "True" in result["sweep_present_vs_absent"]
    assert (
        result["capabilities"]
        ["wick_only_reclaim_category_available"]
        is False
    )
