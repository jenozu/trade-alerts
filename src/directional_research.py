"""Ledger-only diagnostics for EXP-002 long-vs-short research."""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

SCORE_BUCKETS = (("<50", -np.inf, 50.0), ("50-59",50,60), ("60-69",60,70), ("70-79",70,80), ("80-89",80,90), ("90-100",90,100.0000001))
REQUIRED = {"direction","raw_score","net_result_points","tp1_hit","tp2_hit","tp3_hit","tp4_hit","stop_hit","mfe_points","mae_points"}
CONTEXT_COLUMNS = ("htf_bias","dol_direction","liquidity_sweep","displacement","structure_shift","fvg_context")
NUMERIC_CONTEXT = ("snr_1m","snr_5m","snr_15m","rvol_rolling","rvol_time_of_day")

class DirectionalResearchError(RuntimeError): pass

def _bool_rate(s: pd.Series) -> float:
    if s.empty: return float("nan")
    if s.dtype == bool: return float(s.mean())
    t=s.astype(str).str.strip().str.lower()
    mapped=t.map({"true":True,"1":True,"yes":True,"y":True,"false":False,"0":False,"no":False,"n":False})
    return float(mapped.mean()) if mapped.notna().any() else float(s.astype(bool).mean())

def _score_band(v: float) -> str:
    for label, lo, hi in SCORE_BUCKETS:
        if lo <= v < hi: return label
    return "out-of-range"

def validate_ledger(df: pd.DataFrame) -> None:
    missing=REQUIRED-set(df.columns)
    if missing: raise DirectionalResearchError(f"Trade ledger is missing required columns: {sorted(missing)}")
    if df.empty: raise DirectionalResearchError("Trade ledger is empty.")
    dirs=set(df.direction.dropna().astype(str).str.lower())
    if not dirs <= {"long","short"}: raise DirectionalResearchError(f"Unsupported directions: {sorted(dirs-{'long','short'})}")
    scores=pd.to_numeric(df.raw_score,errors="coerce")
    if scores.isna().any() or ((scores<0)|(scores>100)).any(): raise DirectionalResearchError("raw_score must be present and between 0 and 100.")

def _hold_minutes(g: pd.DataFrame) -> pd.Series | None:
    for col in ("minutes_held","hold_minutes","duration_minutes"):
        if col in g: return pd.to_numeric(g[col],errors="coerce")
    for a,b in (("entry_time","exit_time"),("entry_datetime","exit_datetime"),("entry_ts","exit_ts")):
        if a in g and b in g:
            return (pd.to_datetime(g[b],errors="coerce")-pd.to_datetime(g[a],errors="coerce")).dt.total_seconds()/60
    return None

def _metrics(g: pd.DataFrame) -> dict[str,Any]:
    if g.empty: return {"trades":0}
    pts=pd.to_numeric(g.net_result_points,errors="coerce")
    wins=pts[pts>0].sum(); losses=abs(pts[pts<0].sum())
    r=pd.to_numeric(g["net_result_r"],errors="coerce") if "net_result_r" in g else pd.Series(np.nan,index=g.index)
    mfe=pd.to_numeric(g.mfe_points,errors="coerce"); mae=pd.to_numeric(g.mae_points,errors="coerce")
    out={"trades":int(len(g)),"win_rate":float((pts>0).mean()),"expectancy_points":float(pts.mean()),"expectancy_r":float(r.mean()) if r.notna().any() else None,"profit_factor":float(wins/losses) if losses else (float("inf") if wins else None),"net_points":float(pts.sum()),"tp1_hit_rate":_bool_rate(g.tp1_hit),"tp2_hit_rate":_bool_rate(g.tp2_hit),"tp3_hit_rate":_bool_rate(g.tp3_hit),"tp4_hit_rate":_bool_rate(g.tp4_hit),"stop_rate":_bool_rate(g.stop_hit),"average_mfe":float(mfe.mean()),"median_mfe":float(mfe.median()),"average_mae":float(mae.mean()),"median_mae":float(mae.median()),"average_score":float(pd.to_numeric(g.raw_score).mean()),"median_score":float(pd.to_numeric(g.raw_score).median())}
    hm=_hold_minutes(g)
    out["average_hold_minutes"]=float(hm.mean()) if hm is not None and hm.notna().any() else None
    return out

def _segments(df: pd.DataFrame,col: str) -> list[dict[str,Any]]:
    if col not in df: return []
    rows=[]
    vals=df[col].where(df[col].notna(),"<missing>").astype(str)
    for val in sorted(vals.unique()):
        mask=vals==val
        rows.append({"value":val,"overall":_metrics(df[mask]),"long":_metrics(df[mask & (df.direction=="long")]),"short":_metrics(df[mask & (df.direction=="short")])})
    return rows

def _time_bucket(df: pd.DataFrame) -> pd.Series | None:
    candidate=None
    for col in ("entry_time","entry_datetime","entry_ts","timestamp","time"):
        if col in df:
            candidate=pd.to_datetime(df[col],errors="coerce")
            break
    if candidate is None or not candidate.notna().any(): return None
    mins=candidate.dt.hour*60+candidate.dt.minute
    bins=[0,9*60+35,9*60+45,10*60,10*60+15,10*60+30,24*60]
    labels=["before-09:35","09:35-09:44","09:45-09:59","10:00-10:14","10:15-10:29","10:30+"]
    return pd.cut(mins,bins=bins,labels=labels,right=False,include_lowest=True).astype(str)

def _alignment(df: pd.DataFrame) -> list[dict[str,Any]]:
    if "htf_bias" not in df: return []
    b=df.htf_bias.astype(str).str.lower(); d=df.direction
    status=np.where(((d=="long") & b.str.contains("bull|long",regex=True))|((d=="short") & b.str.contains("bear|short",regex=True)),"aligned",np.where(b.str.contains("neutral|unknown|none|nan",regex=True),"neutral/unknown","conflicting"))
    tmp=df.copy(); tmp["htf_alignment"]=status
    return _segments(tmp,"htf_alignment")

def _numeric_summary(df: pd.DataFrame,col: str) -> dict[str,Any] | None:
    if col not in df: return None
    x=pd.to_numeric(df[col],errors="coerce")
    if not x.notna().any(): return None
    by={}
    for d in ("long","short"):
        v=x[df.direction==d].dropna(); by[d]={"count":int(len(v)),"mean":float(v.mean()),"median":float(v.median()),"q25":float(v.quantile(.25)),"q75":float(v.quantile(.75))}
    q=x.quantile([0,.25,.5,.75,1]).values
    uniq=np.unique(q)
    buckets=[]
    if len(uniq)>=3:
        cats=pd.qcut(x,4,duplicates="drop")
        tmp=df.copy(); tmp["bucket"]=cats.astype(str)
        buckets=_segments(tmp,"bucket")
    return {"by_direction":by,"quartile_performance":buckets}

def analyze_long_vs_short(year_ledgers: dict[int,pd.DataFrame]) -> dict[str,Any]:
    if set(year_ledgers)!={2023,2024,2025}: raise DirectionalResearchError("EXP-002 control set must contain exactly 2023, 2024, and 2025 ledgers.")
    frames=[]
    for y,df in sorted(year_ledgers.items()):
        validate_ledger(df); f=df.copy(); f["year"]=y; f["direction"]=f.direction.astype(str).str.lower(); f["score_band"]=pd.to_numeric(f.raw_score).map(_score_band); frames.append(f)
    all_=pd.concat(frames,ignore_index=True)
    tb=_time_bucket(all_)
    if tb is not None: all_["time_bucket"]=tb
    direction={d:_metrics(all_[all_.direction==d]) for d in ("long","short")}
    by_year={str(y):{d:_metrics(all_[(all_.year==y)&(all_.direction==d)]) for d in ("long","short")} for y in sorted(year_ledgers)}
    bands={label:{d:_metrics(all_[(all_.score_band==label)&(all_.direction==d)]) for d in ("long","short")} for label,_,_ in SCORE_BUCKETS if (all_.score_band==label).any()}
    score_dist={d:{"count":int((all_.direction==d).sum()),"mean":float(all_.loc[all_.direction==d,"raw_score"].mean()),"median":float(all_.loc[all_.direction==d,"raw_score"].median()),"std":float(all_.loc[all_.direction==d,"raw_score"].std(ddof=1)),"band_counts":all_.loc[all_.direction==d,"score_band"].value_counts().sort_index().to_dict()} for d in ("long","short")}
    contexts={c:_segments(all_,c) for c in CONTEXT_COLUMNS if c in all_}
    contexts["htf_alignment"]=_alignment(all_)
    if "time_bucket" in all_: contexts["time_bucket"]=_segments(all_,"time_bucket")
    numeric={c:_numeric_summary(all_,c) for c in NUMERIC_CONTEXT if c in all_}
    numeric={k:v for k,v in numeric.items() if v is not None}
    diff=direction["long"]["expectancy_points"]-direction["short"]["expectancy_points"]
    stable_sign=sum(np.sign(by_year[str(y)]["long"].get("expectancy_points",0)-by_year[str(y)]["short"].get("expectancy_points",0))==np.sign(diff) for y in sorted(year_ledgers))
    high_short=sum(bands.get(b,{}).get("short",{}).get("trades",0) for b in ("80-89","90-100"))
    return {"experiment_id":"EXP-002_long-vs-short","years":[2023,2024,2025],"overall":_metrics(all_),"by_direction":direction,"expectancy_gap_long_minus_short":float(diff),"direction_gap_same_sign_years":int(stable_sign),"by_year":by_year,"score_distribution":score_dist,"score_bands":bands,"contexts":contexts,"numeric_context":numeric,"diagnostics":{"high_score_short_sample":int(high_short),"separate_scoring_evidence":"candidate" if stable_sign>=2 and abs(diff)>=1 else "insufficient","sample_size_note":"Treat categorical cells under 30 trades and numeric quartiles under 30 trades as exploratory; direction-level conclusions should also be checked for year stability."}}

def flatten_tables(result: dict[str,Any]) -> dict[str,pd.DataFrame]:
    rows=[]
    for d,m in result["by_direction"].items(): rows.append({"segment":"direction","value":d,**m})
    for y,dm in result["by_year"].items():
        for d,m in dm.items(): rows.append({"segment":"year","value":y,"direction":d,**m})
    for b,dm in result["score_bands"].items():
        for d,m in dm.items(): rows.append({"segment":"score_band","value":b,"direction":d,**m})
    for c,vals in result["contexts"].items():
        for item in vals:
            for d in ("long","short"): rows.append({"segment":c,"value":item["value"],"direction":d,**item[d]})
    return {"directional_metrics":pd.DataFrame(rows)}

def markdown_report(result: dict[str,Any], ledger_paths: dict[int,str]) -> str:
    def n(v,d=2):
        if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
        if isinstance(v,float) and np.isinf(v): return "∞"
        return f"{float(v):.{d}f}"
    def p(v): return "—" if v is None else f"{100*float(v):.1f}%"
    def row(label,m): return f"| {label} | {m.get('trades',0)} | {p(m.get('win_rate'))} | {n(m.get('expectancy_points'))} | {n(m.get('expectancy_r'),3)} | {n(m.get('profit_factor'))} | {n(m.get('net_points'))} | {p(m.get('tp1_hit_rate'))} | {p(m.get('tp2_hit_rate'))} | {p(m.get('tp3_hit_rate'))} | {p(m.get('tp4_hit_rate'))} | {p(m.get('stop_rate'))} | {n(m.get('average_mfe'))} | {n(m.get('median_mfe'))} | {n(m.get('average_mae'))} | {n(m.get('median_mae'))} | {n(m.get('average_hold_minutes'))} |"
    h="| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    L=["# EXP-002 — Long vs Short","","Ledger-only diagnostic; no pipeline rerun and no strategy/scoring changes.","","## Inputs",""]+[f"- {y}: `{p}`" for y,p in sorted(ledger_paths.items())]+["","## Overall direction comparison","",h,row("LONG",result["by_direction"]["long"]),row("SHORT",result["by_direction"]["short"]),"",f"Long-minus-short expectancy gap: **{n(result['expectancy_gap_long_minus_short'])} points/trade**.","", "## Year-by-year", "", h]
    for y,dm in result["by_year"].items(): L += [row(f"{y} LONG",dm["long"]),row(f"{y} SHORT",dm["short"])]
    L += ["","## Score-band performance","",h]
    for b,dm in result["score_bands"].items(): L += [row(f"{b} LONG",dm["long"]),row(f"{b} SHORT",dm["short"])]
    L += ["","## Score distribution",""]
    for d,s in result["score_distribution"].items(): L.append(f"- {d.upper()}: n={s['count']}, mean={n(s['mean'])}, median={n(s['median'])}, std={n(s['std'])}, bands={s['band_counts']}.")
    L += ["","## Context diagnostics",""]
    for c,items in result["contexts"].items():
        L += [f"### {c}",""]
        for item in items:
            L.append(f"- `{item['value']}` — long n={item['long'].get('trades',0)}, exp={n(item['long'].get('expectancy_points'))}, PF={n(item['long'].get('profit_factor'))}; short n={item['short'].get('trades',0)}, exp={n(item['short'].get('expectancy_points'))}, PF={n(item['short'].get('profit_factor'))}.")
        L.append("")
    L += ["## SNR / RVOL diagnostics",""]
    for c,item in result["numeric_context"].items():
        a=item["by_direction"]; L.append(f"- {c}: long mean {n(a['long']['mean'])} / median {n(a['long']['median'])} (n={a['long']['count']}); short mean {n(a['short']['mean'])} / median {n(a['short']['median'])} (n={a['short']['count']}).")
    L += ["","## Diagnostic flags","",f"- Direction gap has the aggregate sign in **{result['direction_gap_same_sign_years']}/3 years**.",f"- High-score (80+) short sample: **{result['diagnostics']['high_score_short_sample']} trades**.",f"- Evidence for later separate scoring: **{result['diagnostics']['separate_scoring_evidence']}** (diagnostic flag only; no config split authorized).",f"- {result['diagnostics']['sample_size_note']}",""]
    return "\n".join(L)
