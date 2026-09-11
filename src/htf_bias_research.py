"""EXP-006 higher-timeframe-bias diagnostics from baseline ledgers plus scored features.

No historical pipeline stages are rerun. Trades are joined to the exact signal-time
feature row. The experiment preserves the production HTF hierarchy: 1h/30m/15m
form intraday bias, while 4h/1d are macro context.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from directional_research import NUMERIC_CONTEXT, SCORE_BUCKETS, _metrics, _score_band, _time_bucket, validate_ledger
from setup_family_research import derive_setup_family

YEARS = (2023, 2024, 2025)
TIMEFRAMES = ("1d", "4h", "1h", "30m", "15m")
INTRADAY_TIMEFRAMES = ("1h", "30m", "15m")
MACRO_TIMEFRAMES = ("4h", "1d")
REQUIRED_FEATURE_COLUMNS = {"timestamp", *(f"bias_{tf}" for tf in TIMEFRAMES)}
BIAS_STATES = {"bullish", "bearish", "neutral"}
RELATIONS = ("aligned", "opposed", "neutral", "unknown")
HEADLINE_CONTEXTS = ("aligned", "conflicting", "neutral", "unknown")


class HTFBiasResearchError(RuntimeError):
    pass


def _normalise_bias(value: Any) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    value = str(value).strip().lower()
    return value if value in BIAS_STATES else "unknown"


def _relation(state: str, direction: str) -> str:
    state = _normalise_bias(state)
    direction = str(direction).strip().lower()
    if state == "unknown":
        return "unknown"
    if state == "neutral":
        return "neutral"
    if direction == "long":
        return "aligned" if state == "bullish" else "opposed"
    if direction == "short":
        return "aligned" if state == "bearish" else "opposed"
    return "unknown"


def _as_bool(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def enrich_trades_with_htf_bias(ledger: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Exact signal-time join of the production HTF feature state onto trades."""
    validate_ledger(ledger)
    missing = REQUIRED_FEATURE_COLUMNS - set(features.columns)
    if missing:
        raise HTFBiasResearchError(f"Feature artifact missing EXP-006 columns: {sorted(missing)}")
    if "signal_time" not in ledger.columns:
        raise HTFBiasResearchError("Trade ledger must contain signal_time for exact feature joining.")

    optional = (
        "intraday_bias", "intraday_bias_confidence", "intraday_bias_known_count", "intraday_bias_conflict",
        "intraday_bias_score", "macro_bias", "macro_bias_confidence", "macro_bias_known_count",
        "macro_bias_conflict", "macro_bias_score", "macro_intraday_conflict", "htf_bias",
        "htf_bias_confidence", "htf_bias_known_count", "htf_bias_conflict",
    )
    columns = ["timestamp", *(f"bias_{tf}" for tf in TIMEFRAMES)]
    columns += [c for c in optional if c in features.columns and c not in columns]

    right = features[columns].copy()
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True, errors="coerce")
    right = (
        right.dropna(subset=["timestamp"])
        .sort_values("timestamp", kind="stable")
        .drop_duplicates("timestamp", keep="last")
        .rename(columns={"timestamp": "signal_time"})
    )

    out = ledger.copy()
    out["signal_time"] = pd.to_datetime(out["signal_time"], utc=True, errors="coerce")
    out["direction"] = out["direction"].astype(str).str.lower()
    out["setup_family"] = derive_setup_family(out)
    out["score_band_exp006"] = pd.to_numeric(out["raw_score"], errors="coerce").map(_score_band)
    out = out.merge(right, how="left", on="signal_time", validate="many_to_one", indicator="_htf_join")
    out["htf_feature_matched"] = out["_htf_join"].eq("both")
    out.drop(columns=["_htf_join"], inplace=True)

    for tf in TIMEFRAMES:
        col = f"bias_{tf}"
        out[col] = out[col].map(_normalise_bias)
        out[f"relation_{tf}"] = [
            _relation(state, direction) for state, direction in zip(out[col], out["direction"])
        ]

    # Production compatibility alias: htf_bias == intraday_bias. Prefer the explicit
    # hierarchy column from features and reconstruct only when it is unavailable.
    if "intraday_bias" not in out.columns:
        if "htf_bias" in out.columns:
            out["intraday_bias"] = out["htf_bias"]
        else:
            # Deterministic current production weights: 1h=3, 30m=2, 15m=1.
            weights = {"1h": 3.0, "30m": 2.0, "15m": 1.0}
            states: list[str] = []
            for _, row in out.iterrows():
                score = 0.0
                known = 0
                for tf, weight in weights.items():
                    state = _normalise_bias(row[f"bias_{tf}"])
                    if state == "unknown":
                        continue
                    known += 1
                    if state == "bullish": score += weight
                    elif state == "bearish": score -= weight
                states.append("unknown" if known == 0 else ("bullish" if score > 0 else "bearish" if score < 0 else "neutral"))
            out["intraday_bias"] = states
    out["intraday_bias"] = out["intraday_bias"].map(_normalise_bias)
    out["intraday_relation"] = [
        _relation(state, direction) for state, direction in zip(out["intraday_bias"], out["direction"])
    ]

    conflict_col = "intraday_bias_conflict" if "intraday_bias_conflict" in out.columns else "htf_bias_conflict"
    if conflict_col in out.columns:
        component_conflict = out[conflict_col].map(_as_bool)
    else:
        component_conflict = pd.Series(False, index=out.index)
        for idx, row in out.iterrows():
            directional = {_normalise_bias(row[f"bias_{tf}"]) for tf in INTRADAY_TIMEFRAMES} & {"bullish", "bearish"}
            component_conflict.loc[idx] = len(directional) > 1
    out["intraday_component_conflict"] = component_conflict.astype(bool)

    headline = []
    for relation, conflict, matched in zip(out["intraday_relation"], out["intraday_component_conflict"], out["htf_feature_matched"]):
        if not matched or relation == "unknown": headline.append("unknown")
        elif relation == "opposed" or conflict: headline.append("conflicting")
        elif relation == "neutral": headline.append("neutral")
        else: headline.append("aligned")
    out["htf_context"] = headline

    if "macro_bias" in out.columns:
        out["macro_bias"] = out["macro_bias"].map(_normalise_bias)
    else:
        # Same deterministic production macro weights: 4h=2, 1d=1.
        macro = []
        for _, row in out.iterrows():
            score = 0.0; known = 0
            for tf, weight in (("4h", 2.0), ("1d", 1.0)):
                state = _normalise_bias(row[f"bias_{tf}"])
                if state == "unknown": continue
                known += 1
                if state == "bullish": score += weight
                elif state == "bearish": score -= weight
            macro.append("unknown" if known == 0 else ("bullish" if score > 0 else "bearish" if score < 0 else "neutral"))
        out["macro_bias"] = macro
    out["macro_relation"] = [_relation(s, d) for s, d in zip(out["macro_bias"], out["direction"])]
    return out


def _metric_map(frame: pd.DataFrame, column: str, values: tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    if column not in frame.columns:
        return {}
    keys = list(values) if values else sorted(frame[column].dropna().astype(str).unique())
    return {key: _metrics(frame[frame[column].astype(str) == key]) for key in keys}


def _nested_metric_map(frame: pd.DataFrame, outer: str, inner: str, inner_values: tuple[str, ...] | None = None) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for value in sorted(frame[outer].dropna().astype(str).unique()):
        sub = frame[frame[outer].astype(str) == value]
        result[value] = _metric_map(sub, inner, inner_values)
    return result


def _numeric_by_context(frame: pd.DataFrame, column: str) -> dict[str, dict[str, Any]] | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce")
    if not values.notna().any():
        return None
    out: dict[str, dict[str, Any]] = {}
    for context in HEADLINE_CONTEXTS:
        v = values[frame["htf_context"] == context].dropna()
        out[context] = {
            "count": int(len(v)),
            "mean": float(v.mean()) if len(v) else None,
            "median": float(v.median()) if len(v) else None,
            "q25": float(v.quantile(.25)) if len(v) else None,
            "q75": float(v.quantile(.75)) if len(v) else None,
        }
    return out


def _pairwise_redundancy(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a, b in combinations(TIMEFRAMES, 2):
        sa = frame[f"bias_{a}"]
        sb = frame[f"bias_{b}"]
        mask = sa.isin({"bullish", "bearish"}) & sb.isin({"bullish", "bearish"})
        n = int(mask.sum())
        agreement = float((sa[mask] == sb[mask]).mean()) if n else None
        rel_a = frame[f"relation_{a}"]
        rel_b = frame[f"relation_{b}"]
        both_aligned = frame[(rel_a == "aligned") & (rel_b == "aligned")]
        a_only = frame[(rel_a == "aligned") & (rel_b != "aligned") & (rel_b != "unknown")]
        b_only = frame[(rel_b == "aligned") & (rel_a != "aligned") & (rel_a != "unknown")]
        rows.append({
            "timeframe_a": a,
            "timeframe_b": b,
            "known_directional_pairs": n,
            "directional_state_agreement_rate": agreement,
            "both_aligned": _metrics(both_aligned),
            "a_aligned_b_not": _metrics(a_only),
            "b_aligned_a_not": _metrics(b_only),
        })
    return rows


def analyze_htf_bias(year_frames: dict[int, pd.DataFrame]) -> dict[str, Any]:
    if set(year_frames) != set(YEARS):
        raise HTFBiasResearchError("EXP-006 requires exactly 2023, 2024, and 2025.")
    frames = []
    for year, frame in sorted(year_frames.items()):
        f = frame.copy()
        f["year"] = year
        frames.append(f)
    all_ = pd.concat(frames, ignore_index=True)

    time_bucket = _time_bucket(all_)
    if time_bucket is not None:
        all_["time_bucket_exp006"] = time_bucket
    time_cap = {"available": "time_bucket_exp006" in all_.columns, "reliable": False, "distribution": {}}
    if "time_bucket_exp006" in all_.columns:
        counts = all_["time_bucket_exp006"].value_counts(dropna=False)
        time_cap["distribution"] = {str(k): int(v) for k, v in counts.items()}
        time_cap["reliable"] = bool(len(counts) > 1 and counts.max() / len(all_) < .95)

    coverage = {
        "total_trades": int(len(all_)),
        "feature_matched": int(all_["htf_feature_matched"].sum()),
    }
    coverage["match_rate"] = coverage["feature_matched"] / coverage["total_trades"] if coverage["total_trades"] else 0.0

    timeframe_results: dict[str, Any] = {}
    for tf in TIMEFRAMES:
        relation_col = f"relation_{tf}"
        relations = _metric_map(all_, relation_col, RELATIONS)
        aligned = all_[all_[relation_col] == "aligned"]
        known_non_aligned = all_[all_[relation_col].isin(["opposed", "neutral"])]
        timeframe_results[tf] = {
            "relations": relations,
            "aligned_vs_known_non_aligned": {
                "aligned": _metrics(aligned),
                "known_non_aligned": _metrics(known_non_aligned),
                "expectancy_lift_points": (
                    _metrics(aligned).get("expectancy_points", np.nan) - _metrics(known_non_aligned).get("expectancy_points", np.nan)
                    if len(aligned) and len(known_non_aligned) else None
                ),
            },
            "by_year": _nested_metric_map(all_, "year", relation_col, RELATIONS),
            "by_setup_family": _nested_metric_map(all_, "setup_family", relation_col, RELATIONS),
            "by_direction": _nested_metric_map(all_, "direction", relation_col, RELATIONS),
        }

    numeric = {}
    for col in NUMERIC_CONTEXT:
        item = _numeric_by_context(all_, col)
        if item is not None: numeric[col] = item

    sweep_context: dict[str, Any] = {}
    if "liquidity_sweep" in all_.columns:
        sweep_values = all_["liquidity_sweep"].astype(str)
        for value in sorted(sweep_values.unique()):
            sub = all_[sweep_values == value]
            sweep_context[value] = _metric_map(sub, "htf_context", HEADLINE_CONTEXTS)

    return {
        "experiment_id": "EXP-006_htf-bias",
        "coverage": coverage,
        "headline_context": _metric_map(all_, "htf_context", HEADLINE_CONTEXTS),
        "directional_relation": _metric_map(all_, "intraday_relation", RELATIONS),
        "macro_relation": _metric_map(all_, "macro_relation", RELATIONS),
        "by_year": _nested_metric_map(all_, "year", "htf_context", HEADLINE_CONTEXTS),
        "by_direction": _nested_metric_map(all_, "direction", "htf_context", HEADLINE_CONTEXTS),
        "by_setup_family": _nested_metric_map(all_, "setup_family", "htf_context", HEADLINE_CONTEXTS),
        "by_score_band": _nested_metric_map(all_, "score_band_exp006", "htf_context", HEADLINE_CONTEXTS),
        "timeframes": timeframe_results,
        "pairwise_redundancy": _pairwise_redundancy(all_),
        "snr_rvol": numeric,
        "liquidity_sweep_context": sweep_context,
        "time_of_day": time_cap,
        "scoring_contract": {
            "production_intraday_timeframes": ["1h", "30m", "15m"],
            "production_intraday_weights": {"1h": 3.0, "30m": 2.0, "15m": 1.0},
            "macro_context_timeframes": ["4h", "1d"],
            "macro_context_weights": {"4h": 2.0, "1d": 1.0},
            "score_positive_points_when_intraday_aligned": 10.0,
            "score_penalty_points_when_intraday_opposed": -20.0,
            "daily_role": "context_only",
        },
        "limitations": [
            "Diagnostic association does not prove unique causal contribution; pairwise agreement is a redundancy diagnostic, not an ablation result.",
            "Time-of-day conclusions are allowed only when the recorded timestamp buckets are demonstrably non-degenerate.",
            "Cells under 30 trades are exploratory.",
        ],
    }


def metrics_frame(result: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    def add(segment: str, value: str, metrics: dict[str, Any], **extra: Any) -> None:
        rows.append({"segment": segment, "value": value, **extra, **metrics})
    for value, metrics in result["headline_context"].items(): add("headline_context", value, metrics)
    for value, metrics in result["directional_relation"].items(): add("intraday_relation", value, metrics)
    for year, groups in result["by_year"].items():
        for value, metrics in groups.items(): add("year_htf_context", value, metrics, year=year)
    for family, groups in result["by_setup_family"].items():
        for value, metrics in groups.items(): add("family_htf_context", value, metrics, setup_family=family)
    for direction, groups in result["by_direction"].items():
        for value, metrics in groups.items(): add("direction_htf_context", value, metrics, direction=direction)
    for tf, data in result["timeframes"].items():
        for relation, metrics in data["relations"].items(): add("timeframe_relation", relation, metrics, timeframe=tf)
        for year, groups in data["by_year"].items():
            for relation, metrics in groups.items(): add("timeframe_year_relation", relation, metrics, timeframe=tf, year=year)
    return pd.DataFrame(rows)


def _fmt(v: Any, digits: int = 2) -> str:
    if v is None: return "—"
    try:
        f = float(v)
        if np.isnan(f): return "—"
        if np.isinf(f): return "∞"
        return f"{f:.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v: Any) -> str:
    return "—" if v is None else f"{100*float(v):.1f}%"


def _row(label: str, m: dict[str, Any]) -> str:
    return f"| {label} | {m.get('trades',0)} | {_pct(m.get('win_rate'))} | {_fmt(m.get('expectancy_points'))} | {_fmt(m.get('expectancy_r'),3)} | {_fmt(m.get('profit_factor'))} | {_fmt(m.get('net_points'))} | {_pct(m.get('tp1_hit_rate'))} | {_pct(m.get('tp2_hit_rate'))} | {_pct(m.get('tp3_hit_rate'))} | {_pct(m.get('tp4_hit_rate'))} | {_pct(m.get('stop_rate'))} | {_fmt(m.get('average_mfe'))} | {_fmt(m.get('median_mfe'))} | {_fmt(m.get('average_mae'))} | {_fmt(m.get('median_mae'))} |"


def markdown_report(result: dict[str, Any], ledgers: dict[int, str], features: dict[int, str]) -> str:
    header = "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    L = ["# EXP-006 — HTF Bias", "", "Diagnostic only; exact signal-time join to existing scored feature artifacts. No historical pipeline rerun and no strategy/scoring changes.", "", "## Inputs", ""]
    for year in YEARS:
        L += [f"- {year} ledger: `{ledgers[year]}`", f"- {year} features: `{features[year]}`"]
    c = result["coverage"]
    L += ["", "## Feature-join coverage", "", f"- Matched: **{c['feature_matched']}/{c['total_trades']} ({100*c['match_rate']:.1f}%)**", "", "## Production intraday HTF context", "", header]
    for context in HEADLINE_CONTEXTS: L.append(_row(context, result["headline_context"][context]))
    L += ["", "Headline `conflicting` includes a directional intraday bias opposed to the trade or an explicit conflict among the intraday HTF components.", "", "## Pure intraday directional relation", "", header]
    for relation in RELATIONS: L.append(_row(relation, result["directional_relation"][relation]))
    L += ["", "## By year", "", header]
    for year, groups in result["by_year"].items():
        for context in HEADLINE_CONTEXTS: L.append(_row(f"{year} {context}", groups[context]))
    L += ["", "## By setup family", "", header]
    for family, groups in result["by_setup_family"].items():
        for context in HEADLINE_CONTEXTS: L.append(_row(f"{family} {context}", groups[context]))
    L += ["", "## By direction", "", header]
    for direction, groups in result["by_direction"].items():
        for context in HEADLINE_CONTEXTS: L.append(_row(f"{direction} {context}", groups[context]))
    L += ["", "## Individual timeframe contribution", ""]
    for tf in TIMEFRAMES:
        data = result["timeframes"][tf]
        lift = data["aligned_vs_known_non_aligned"]
        L += [f"### {tf}", "", header]
        for relation in RELATIONS: L.append(_row(relation, data["relations"][relation]))
        L.append(f"- Aligned-minus-known-non-aligned expectancy lift: **{_fmt(lift['expectancy_lift_points'])} pts/trade**.")
        L.append("")
    L += ["## Pairwise timeframe redundancy diagnostics", ""]
    for item in result["pairwise_redundancy"]:
        L.append(f"- {item['timeframe_a']} vs {item['timeframe_b']}: known directional pairs={item['known_directional_pairs']}, state agreement={_pct(item['directional_state_agreement_rate'])}; both aligned n={item['both_aligned'].get('trades',0)}, exp={_fmt(item['both_aligned'].get('expectancy_points'))}, PF={_fmt(item['both_aligned'].get('profit_factor'))}.")
    L += ["", "## Score-band × HTF context", "", header]
    for band, groups in result["by_score_band"].items():
        for context in HEADLINE_CONTEXTS: L.append(_row(f"{band} {context}", groups[context]))
    L += ["", "## SNR / RVOL by HTF context", ""]
    for col, groups in result["snr_rvol"].items():
        parts=[]
        for context in HEADLINE_CONTEXTS:
            s=groups[context]; parts.append(f"{context}: mean={_fmt(s['mean'])}, median={_fmt(s['median'])}, n={s['count']}")
        L.append(f"- {col}: " + "; ".join(parts))
    L += ["", "## Liquidity/sweep interaction", ""]
    for sweep, groups in result["liquidity_sweep_context"].items():
        L += [f"### liquidity_sweep={sweep}", "", header]
        for context in HEADLINE_CONTEXTS: L.append(_row(context, groups[context]))
        L.append("")
    sc = result["scoring_contract"]
    L += ["## Current scoring contract", "", f"- Intraday production bias: 1h/30m/15m weighted {sc['production_intraday_weights']}.", f"- Macro context: 4h/1d weighted {sc['macro_context_weights']}; Daily remains `{sc['daily_role']}`.", f"- Current score treatment: +{sc['score_positive_points_when_intraday_aligned']:.0f} points when aligned and {sc['score_penalty_points_when_intraday_opposed']:.0f} points when opposed.", "", "## Time-of-day capability", "", f"- Available: **{result['time_of_day']['available']}**; reliable: **{result['time_of_day']['reliable']}**; distribution={result['time_of_day']['distribution']}.", "", "## Limitations", ""]
    L += [f"- {item}" for item in result["limitations"]]
    return "\n".join(L) + "\n"
