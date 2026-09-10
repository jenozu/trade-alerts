import pandas as pd

from src.level_research import enrich_trades_with_levels, analyze_level_performance


def _ledger():
    return pd.DataFrame([
        {"signal_time":"2025-01-02T14:30:00Z","direction":"long","raw_score":75,"score_band":"near_trigger","score_edge":1.0,"tp1_hit":True,"tp2_hit":False,"tp3_hit":False,"tp4_hit":False,"stop_hit":False,"net_result_points":10.0,"net_result_r":0.4,"mfe_points":30.0,"mae_points":5.0,"minutes_held":10.0,"liquidity_sweep":True},
        {"signal_time":"2025-01-02T14:31:00Z","direction":"short","raw_score":80,"score_band":"high_probability","score_edge":2.0,"tp1_hit":False,"tp2_hit":False,"tp3_hit":False,"tp4_hit":False,"stop_hit":True,"net_result_points":-25.0,"net_result_r":-1.0,"mfe_points":5.0,"mae_points":25.0,"minutes_held":5.0,"liquidity_sweep":False},
    ])


def _features():
    rows=[]
    for minute in range(22,32):
        rows.append({
            "timestamp":f"2025-01-02T14:{minute:02d}:00Z",
            "pmh":20100.0,"pml":19900.0,"pdh":20200.0,"pdl":19800.0,
            "onh":20080.0,"onl":19920.0,"loh":20060.0,"lol":19940.0,"ash":20050.0,"asl":19950.0,
            "week_high":20300.0,"week_low":19700.0,
            "active_internal_swing_high":20025.0,"active_internal_swing_low":19975.0,
            "active_external_swing_high":20075.0,"active_external_swing_low":19925.0,
            "internal_swing_high_equal_cluster_level":None,"internal_swing_low_equal_cluster_level":None,
            "external_swing_high_equal_cluster_level":None,"external_swing_low_equal_cluster_level":None,
            "buy_side_sweep_source":None,"sell_side_sweep_source":None,
            "buy_side_sweep_level":None,"sell_side_sweep_level":None,
            "structure_broken_level":None,
        })
    rows[7]["sell_side_sweep_source"]="pml"
    rows[7]["sell_side_sweep_level"]=19900.0
    rows[9]["structure_broken_level"]=19975.0
    return pd.DataFrame(rows)


def test_reversal_uses_recent_directional_sweep_source():
    out=enrich_trades_with_levels(_ledger(), _features(), recent_sweep_lookback=10)
    first=out.iloc[0]
    assert first.level_source == "pml"
    assert first.level_group == "PMH/PML"
    assert first.level_classification_method == "recent_directional_sweep_source"


def test_continuation_requires_exact_structure_level_match():
    out=enrich_trades_with_levels(_ledger(), _features(), recent_sweep_lookback=10)
    second=out.iloc[1]
    assert second.level_source == "active_internal_swing_low"
    assert second.level_group == "internal swing"
    assert second.level_classification_method == "exact_structure_broken_level_match"
    result=analyze_level_performance({2025:out})
    assert result["coverage"]["classified_trades"] == 2
