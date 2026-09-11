import pandas as pd

from htf_bias_research import analyze_htf_bias, enrich_trades_with_htf_bias


def _ledger():
    return pd.DataFrame({
        "signal_time": pd.to_datetime([
            "2025-01-02T14:30:00Z", "2025-01-02T14:31:00Z",
            "2025-01-02T14:32:00Z", "2025-01-02T14:33:00Z",
        ]),
        "direction": ["long", "short", "long", "short"],
        "raw_score": [75.0, 82.0, 76.0, 78.0],
        "net_result_points": [20.0, 15.0, -25.0, -10.0],
        "tp1_hit": [True, True, False, False],
        "tp2_hit": [False, False, False, False],
        "tp3_hit": [False, False, False, False],
        "tp4_hit": [False, False, False, False],
        "stop_hit": [False, False, True, True],
        "mfe_points": [30.0, 25.0, 5.0, 8.0],
        "mae_points": [10.0, 12.0, 30.0, 25.0],
        "liquidity_sweep": [True, False, True, False],
        "snr_1m": [1.2, 1.4, 0.8, 0.9],
        "rvol_rolling": [1.5, 1.6, 1.0, 1.1],
    })


def _features():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2025-01-02T14:30:00Z", "2025-01-02T14:31:00Z",
            "2025-01-02T14:32:00Z", "2025-01-02T14:33:00Z",
        ]),
        "bias_1d": ["bullish", "bearish", "bearish", "neutral"],
        "bias_4h": ["bullish", "bearish", "bearish", "neutral"],
        "bias_1h": ["bullish", "bearish", "bearish", "neutral"],
        "bias_30m": ["bullish", "bearish", "bullish", "neutral"],
        "bias_15m": ["bullish", "bearish", "bearish", "neutral"],
        "intraday_bias": ["bullish", "bearish", "bearish", "neutral"],
        "intraday_bias_conflict": [False, False, True, False],
        "macro_bias": ["bullish", "bearish", "bearish", "neutral"],
    })


def test_exact_join_and_context_classification():
    enriched = enrich_trades_with_htf_bias(_ledger(), _features())
    assert enriched["htf_feature_matched"].all()
    assert enriched["htf_context"].tolist() == ["aligned", "aligned", "conflicting", "neutral"]
    assert enriched["relation_1h"].tolist() == ["aligned", "aligned", "opposed", "neutral"]
    assert enriched["setup_family"].tolist() == ["reversal", "continuation", "reversal", "continuation"]


def test_analysis_reports_timeframe_lift_and_redundancy():
    enriched = enrich_trades_with_htf_bias(_ledger(), _features())
    result = analyze_htf_bias({2023: enriched.copy(), 2024: enriched.copy(), 2025: enriched.copy()})
    assert result["coverage"]["match_rate"] == 1.0
    assert result["headline_context"]["aligned"]["trades"] == 6
    assert set(result["timeframes"]) == {"1d", "4h", "1h", "30m", "15m"}
    assert result["timeframes"]["1h"]["aligned_vs_known_non_aligned"]["expectancy_lift_points"] is not None
    assert len(result["pairwise_redundancy"]) == 10
    assert result["scoring_contract"]["score_positive_points_when_intraday_aligned"] == 10.0
