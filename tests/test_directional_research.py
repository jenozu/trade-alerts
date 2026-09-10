from __future__ import annotations
import pandas as pd
from directional_research import analyze_long_vs_short, flatten_tables, markdown_report

def ledger(direction, scores, results):
    n=len(scores)
    return pd.DataFrame({
        "direction":direction,
        "raw_score":scores,
        "net_result_points":results,
        "net_result_r":[v/25 for v in results],
        "tp1_hit":[v>0 for v in results],
        "tp2_hit":[v>=25 for v in results],
        "tp3_hit":[v>=50 for v in results],
        "tp4_hit":[v>=75 for v in results],
        "stop_hit":[v<0 for v in results],
        "mfe_points":[max(v,0)+5 for v in results],
        "mae_points":[min(v,0)-2 for v in results],
        "minutes_held":[10+i for i in range(n)],
        "htf_bias":["bullish" if d=="long" else "bearish" for d in direction],
        "liquidity_sweep":[True if i%2==0 else False for i in range(n)],
        "displacement":[True]*n,
        "structure_shift":[True]*n,
        "fvg_context":["aligned"]*n,
        "snr_1m":[1+i/10 for i in range(n)],
        "rvol_rolling":[1.2+i/10 for i in range(n)],
    })

def test_exp002_reports_direction_year_band_and_context():
    frames={}
    for y in (2023,2024,2025):
        frames[y]=ledger(["long","long","short","short"],[70,85,75,92],[10+y%2,40,-20,15])
    r=analyze_long_vs_short(frames)
    assert r["by_direction"]["long"]["trades"]==6
    assert r["by_direction"]["long"]["expectancy_points"]>r["by_direction"]["short"]["expectancy_points"]
    assert r["score_bands"]["80-89"]["long"]["trades"]==3
    assert "htf_alignment" in r["contexts"]
    assert "snr_1m" in r["numeric_context"]
    assert not flatten_tables(r)["directional_metrics"].empty
    text=markdown_report(r,{2023:"a",2024:"b",2025:"c"})
    assert "Year-by-year" in text and "Score-band performance" in text

def test_exp002_requires_three_control_years():
    try:
        analyze_long_vs_short({2023:ledger(["long"],[80],[10])})
    except Exception as exc:
        assert "exactly 2023, 2024, and 2025" in str(exc)
    else:
        raise AssertionError("expected validation error")
