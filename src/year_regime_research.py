"""Ledger-only diagnostics for EXP-004 year and regime stability."""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import SCORE_BUCKETS, _metrics, _score_band, _time_bucket, validate_ledger
from setup_family_research import derive_setup_family

YEARS = (2023, 2024, 2025)
CONTEXT_COLUMNS = (
    "setup_family", "direction", "score_band_exp004", "htf_bias", "htf_alignment_exp004",
    "liquidity_sweep", "displacement", "structure_shift", "fvg_context", "time_bucket_exp004",
)
NUMERIC_COLUMNS = ("snr_1m", "snr_5m", "snr_15m", "rvol_rolling", "rvol_time_of_day")
VOLATILITY_COLUMNS = ("volatility_regime", "atr_regime", "realized_volatility_regime", "atr_1m", "realized_volatility")


class YearRegimeResearchError(RuntimeError):
    pass


def _alignment(frame: pd.DataFrame) -> pd.Series | None:
    if "htf_bias" not in frame.columns:
        return None
    bias = frame.htf_bias.astype(str).str.lower()
    direction = frame.direction.astype(str).str.lower()
    return pd.Series(np.where(
        ((direction == "long") & bias.str.contains("bull|long", regex=True)) |
        ((direction == "short") & bias.str.contains("bear|short", regex=True)),
        "aligned",
        np.where(bias.str.contains("neutral|unknown|none|nan", regex=True), "neutral/unknown", "conflicting"),
    ), index=frame.index)


def _metric_delta_2024(by_year: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("win_rate", "expectancy_points", "expectancy_r", "profit_factor", "net_points",
                "tp1_hit_rate", "tp2_hit_rate", "tp3_hit_rate", "tp4_hit_rate", "stop_rate",
                "average_mfe", "median_mfe", "average_mae", "median_mae", "average_hold_minutes"):
        v24 = by_year["2024"].get(key)
        peers = [by_year[y].get(key) for y in ("2023", "2025")]
        peers = [float(v) for v in peers if v is not None and np.isfinite(float(v))]
        if v24 is None or not peers or not np.isfinite(float(v24)):
            out[key] = None
        else:
            peer_mean = float(np.mean(peers))
            out[key] = {"value_2024": float(v24), "peer_mean_2023_2025": peer_mean, "delta": float(v24) - peer_mean}
    return out


def _segment_by_year(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if column not in frame.columns:
        return []
    values = frame[column].where(frame[column].notna(), "<missing>").astype(str)
    rows: list[dict[str, Any]] = []
    for value in sorted(values.unique()):
        row: dict[str, Any] = {"value": value, "by_year": {}}
        for year in YEARS:
            row["by_year"][str(year)] = _metrics(frame[(frame.year == year) & (values == value)])
        rows.append(row)
    return rows


def _numeric_by_year(frame: pd.DataFrame, column: str) -> dict[str, Any] | None:
    if column not in frame.columns:
        return None
    x = pd.to_numeric(frame[column], errors="coerce")
    if not x.notna().any():
        return None
    by_year: dict[str, Any] = {}
    for year in YEARS:
        v = x[frame.year == year].dropna()
        by_year[str(year)] = {
            "count": int(len(v)),
            "mean": float(v.mean()) if len(v) else None,
            "median": float(v.median()) if len(v) else None,
            "q25": float(v.quantile(.25)) if len(v) else None,
            "q75": float(v.quantile(.75)) if len(v) else None,
        }
    return {"by_year": by_year}


def analyze_year_regime(year_ledgers: dict[int, pd.DataFrame]) -> dict[str, Any]:
    if set(year_ledgers) != set(YEARS):
        raise YearRegimeResearchError("EXP-004 control set must contain exactly 2023, 2024, and 2025 ledgers.")

    frames: list[pd.DataFrame] = []
    for year, ledger in sorted(year_ledgers.items()):
        validate_ledger(ledger)
        f = ledger.copy()
        f["direction"] = f.direction.astype(str).str.lower()
        f["year"] = year
        f["setup_family"] = derive_setup_family(f)
        f["score_band_exp004"] = pd.to_numeric(f.raw_score, errors="coerce").map(_score_band)
        frames.append(f)

    all_ = pd.concat(frames, ignore_index=True)
    alignment = _alignment(all_)
    if alignment is not None:
        all_["htf_alignment_exp004"] = alignment
    time_bucket = _time_bucket(all_)
    if time_bucket is not None:
        all_["time_bucket_exp004"] = time_bucket

    by_year = {str(year): _metrics(all_[all_.year == year]) for year in YEARS}
    by_year_direction = {
        str(year): {d: _metrics(all_[(all_.year == year) & (all_.direction == d)]) for d in ("long", "short")}
        for year in YEARS
    }
    by_year_family = {
        str(year): {f: _metrics(all_[(all_.year == year) & (all_.setup_family == f)]) for f in ("reversal", "continuation")}
        for year in YEARS
    }
    by_year_score_band = {
        str(year): {
            label: _metrics(all_[(all_.year == year) & (all_.score_band_exp004 == label)])
            for label, _, _ in SCORE_BUCKETS if (all_.score_band_exp004 == label).any()
        }
        for year in YEARS
    }

    contexts = {col: _segment_by_year(all_, col) for col in CONTEXT_COLUMNS if col in all_.columns}
    numeric = {col: item for col in NUMERIC_COLUMNS if (item := _numeric_by_year(all_, col)) is not None}

    volatility_col = next((c for c in VOLATILITY_COLUMNS if c in all_.columns), None)
    volatility: dict[str, Any] | None = None
    if volatility_col:
        if "regime" in volatility_col:
            volatility = {"column": volatility_col, "segments": _segment_by_year(all_, volatility_col)}
        else:
            volatility = {"column": volatility_col, "numeric": _numeric_by_year(all_, volatility_col)}

    time_capability = {"available": "time_bucket_exp004" in all_.columns, "reliable": False, "distribution": {}}
    if "time_bucket_exp004" in all_.columns:
        counts = all_.time_bucket_exp004.value_counts(dropna=False)
        time_capability["distribution"] = {str(k): int(v) for k, v in counts.items()}
        time_capability["reliable"] = bool(len(counts) > 1 and counts.max() / len(all_) < 0.95)

    return {
        "experiment_id": "EXP-004_year-and-regime-stability",
        "years": list(YEARS),
        "overall_by_year": by_year,
        "delta_2024_vs_peer_mean": _metric_delta_2024(by_year),
        "by_year_direction": by_year_direction,
        "by_year_setup_family": by_year_family,
        "by_year_score_band": by_year_score_band,
        "contexts": contexts,
        "numeric_context": numeric,
        "volatility": volatility,
        "capabilities": {
            "volatility_regime_derivable": volatility is not None,
            "volatility_source_column": volatility_col,
            "time_of_day": time_capability,
            "setup_family_contract": "explicit setup_family when present; otherwise EXP-003 deterministic liquidity_sweep projection",
        },
        "sample_size_note": "Treat categorical cells under 30 trades as exploratory. EXP-004 is diagnostic only; aggregate year differences do not authorize production changes without later controlled experiments and validation.",
    }


def flatten_tables(result: dict[str, Any]) -> dict[str, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for year, metrics in result["overall_by_year"].items():
        rows.append({"segment": "overall", "year": year, "value": "all", **metrics})
    for year, groups in result["by_year_direction"].items():
        for value, metrics in groups.items(): rows.append({"segment": "direction", "year": year, "value": value, **metrics})
    for year, groups in result["by_year_setup_family"].items():
        for value, metrics in groups.items(): rows.append({"segment": "setup_family", "year": year, "value": value, **metrics})
    for year, groups in result["by_year_score_band"].items():
        for value, metrics in groups.items(): rows.append({"segment": "score_band", "year": year, "value": value, **metrics})
    for context, items in result["contexts"].items():
        for item in items:
            for year, metrics in item["by_year"].items(): rows.append({"segment": context, "year": year, "value": item["value"], **metrics})
    return {"year_regime_metrics": pd.DataFrame(rows)}


def markdown_report(result: dict[str, Any], ledger_paths: dict[int, str]) -> str:
    def n(v: Any, d: int = 2) -> str:
        if v is None: return "—"
        try:
            if np.isnan(float(v)): return "—"
            if np.isinf(float(v)): return "∞"
        except (TypeError, ValueError): return str(v)
        return f"{float(v):.{d}f}"
    def pct(v: Any) -> str: return "—" if v is None else f"{100*float(v):.1f}%"
    def row(label: str, m: dict[str, Any]) -> str:
        return f"| {label} | {m.get('trades',0)} | {pct(m.get('win_rate'))} | {n(m.get('expectancy_points'))} | {n(m.get('expectancy_r'),3)} | {n(m.get('profit_factor'))} | {n(m.get('net_points'))} | {pct(m.get('tp1_hit_rate'))} | {pct(m.get('tp2_hit_rate'))} | {pct(m.get('tp3_hit_rate'))} | {pct(m.get('tp4_hit_rate'))} | {pct(m.get('stop_rate'))} | {n(m.get('average_mfe'))} | {n(m.get('median_mfe'))} | {n(m.get('average_mae'))} | {n(m.get('median_mae'))} | {n(m.get('average_hold_minutes'))} |"
    header = "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    L = ["# EXP-004 — Year and Regime Stability", "", "Ledger-only diagnostic; no historical pipeline rerun and no strategy changes.", "", "## Inputs", ""]
    L += [f"- {y}: `{p}`" for y,p in sorted(ledger_paths.items())]
    L += ["", "## Overall by year", "", header]
    for y in map(str, YEARS): L.append(row(y, result["overall_by_year"][y]))
    L += ["", "## 2024 delta versus mean of 2023 and 2025", ""]
    for k,v in result["delta_2024_vs_peer_mean"].items():
        if v is not None: L.append(f"- {k}: 2024={n(v['value_2024'],3)}, peer mean={n(v['peer_mean_2023_2025'],3)}, delta={n(v['delta'],3)}")
    for title,key in (("Direction by year","by_year_direction"),("Setup family by year","by_year_setup_family"),("Score bands by year","by_year_score_band")):
        L += ["", f"## {title}", "", header]
        for y, groups in result[key].items():
            for value,m in groups.items(): L.append(row(f"{y} {value}",m))
    L += ["", "## Context diagnostics", ""]
    for context, items in result["contexts"].items():
        L += [f"### {context}", ""]
        for item in items:
            parts=[]
            for y,m in item["by_year"].items(): parts.append(f"{y}: n={m.get('trades',0)}, exp={n(m.get('expectancy_points'))}, PF={n(m.get('profit_factor'))}")
            L.append(f"- `{item['value']}` — " + "; ".join(parts))
        L.append("")
    L += ["## SNR / RVOL by year", ""]
    for col,item in result["numeric_context"].items():
        vals=[]
        for y,s in item["by_year"].items(): vals.append(f"{y}: mean={n(s['mean'])}, median={n(s['median'])}, n={s['count']}")
        L.append(f"- {col}: " + "; ".join(vals))
    L += ["", "## Capability / limitation flags", ""]
    cap=result["capabilities"]
    L.append(f"- Volatility regime derivable from ledger: **{cap['volatility_regime_derivable']}**" + (f" (`{cap['volatility_source_column']}`)" if cap['volatility_source_column'] else "."))
    L.append(f"- Time-of-day bucket available: **{cap['time_of_day']['available']}**; reliable for comparison: **{cap['time_of_day']['reliable']}**; distribution={cap['time_of_day']['distribution']}.")
    L += ["", "## Sample-size discipline", "", f"- {result['sample_size_note']}"]
    return "\n".join(L) + "\n"
