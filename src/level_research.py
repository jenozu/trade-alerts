"""EXP-005 important-liquidity-level diagnostics from baseline trade ledgers plus scored feature artifacts.

No historical pipeline stages are rerun. Trades are joined to their exact signal-time
feature row. Reversal trigger sources come from the most recent directional sweep
inside the production liquidity recent-context window. Continuation trigger sources
come only from an exact match between structure_broken_level and known level columns;
otherwise the trade remains unclassified rather than guessing.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family

STATIC_HIGH = ("pdh", "pmh", "onh", "loh", "ash", "week_high")
STATIC_LOW = ("pdl", "pml", "onl", "lol", "asl", "week_low")
SWING_HIGH = ("active_internal_swing_high", "active_external_swing_high")
SWING_LOW = ("active_internal_swing_low", "active_external_swing_low")
EQUAL_HIGH = ("internal_swing_high_equal_cluster_level", "external_swing_high_equal_cluster_level")
EQUAL_LOW = ("internal_swing_low_equal_cluster_level", "external_swing_low_equal_cluster_level")
REQUIRED_FEATURE_COLUMNS = {"timestamp", "structure_broken_level", "buy_side_sweep_source", "sell_side_sweep_source", "buy_side_sweep_level", "sell_side_sweep_level"}
SOURCE_GROUPS = {
    "pdh": "PDH/PDL", "pdl": "PDH/PDL",
    "pmh": "PMH/PML", "pml": "PMH/PML",
    "onh": "overnight high/low", "onl": "overnight high/low",
    "loh": "London high/low", "lol": "London high/low",
    "ash": "Asia high/low", "asl": "Asia high/low",
    "week_high": "weekly high/low", "week_low": "weekly high/low",
    "active_internal_swing_high": "internal swing", "active_internal_swing_low": "internal swing",
    "active_external_swing_high": "external swing", "active_external_swing_low": "external swing",
    "internal_swing_high_equal_cluster_level": "equal highs/lows",
    "internal_swing_low_equal_cluster_level": "equal highs/lows",
    "external_swing_high_equal_cluster_level": "equal highs/lows",
    "external_swing_low_equal_cluster_level": "equal highs/lows",
}


class LevelResearchError(RuntimeError):
    pass


def _norm_source(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().lower()
    aliases = {
        "internal_swing_high": "active_internal_swing_high",
        "internal_swing_low": "active_internal_swing_low",
        "external_swing_high": "active_external_swing_high",
        "external_swing_low": "active_external_swing_low",
    }
    return aliases.get(text, text) or None


def _candidate_columns(direction: str) -> tuple[str, ...]:
    return (STATIC_HIGH + SWING_HIGH + EQUAL_HIGH) if direction == "long" else (STATIC_LOW + SWING_LOW + EQUAL_LOW)


def _match_level_sources(row: pd.Series, level: float | None, direction: str, *, tolerance: float = 1e-6) -> list[str]:
    if level is None or not np.isfinite(level):
        return []
    matches: list[str] = []
    for col in _candidate_columns(direction):
        if col not in row.index:
            continue
        try:
            value = float(row[col])
        except (TypeError, ValueError):
            continue
        if np.isfinite(value) and np.isclose(value, level, atol=tolerance, rtol=0.0):
            matches.append(col)
    return matches


def _recent_sweep_source(features: pd.DataFrame, pos: int, direction: str, lookback: int) -> tuple[str | None, float | None]:
    source_col = "sell_side_sweep_source" if direction == "long" else "buy_side_sweep_source"
    level_col = "sell_side_sweep_level" if direction == "long" else "buy_side_sweep_level"
    start = max(0, pos - lookback + 1)
    window = features.iloc[start : pos + 1]
    for _, row in window.iloc[::-1].iterrows():
        source = _norm_source(row.get(source_col))
        if source:
            try:
                level = float(row.get(level_col))
                if not np.isfinite(level): level = None
            except (TypeError, ValueError):
                level = None
            return source, level
    return None, None


def enrich_trades_with_levels(ledger: pd.DataFrame, features: pd.DataFrame, *, recent_sweep_lookback: int = 10) -> pd.DataFrame:
    validate_ledger(ledger)
    missing = REQUIRED_FEATURE_COLUMNS - set(features.columns)
    if missing:
        raise LevelResearchError(f"Feature artifact missing EXP-005 columns: {sorted(missing)}")
    if recent_sweep_lookback < 1:
        raise LevelResearchError("recent_sweep_lookback must be >= 1")

    f = features.copy()
    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True, errors="coerce")
    f = f.dropna(subset=["timestamp"]).sort_values("timestamp", kind="stable").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    lookup = pd.Series(f.index, index=f["timestamp"])

    out = ledger.copy()
    out["signal_time"] = pd.to_datetime(out["signal_time"], utc=True, errors="coerce")
    out["direction"] = out["direction"].astype(str).str.lower()
    out["setup_family"] = derive_setup_family(out)

    feature_pos: list[int | None] = []
    level_source: list[str | None] = []
    level_value: list[float | None] = []
    matched_sources: list[str] = []
    classification_method: list[str] = []

    for _, trade in out.iterrows():
        ts = trade["signal_time"]
        if pd.isna(ts) or ts not in lookup.index:
            feature_pos.append(None); level_source.append(None); level_value.append(None); matched_sources.append(""); classification_method.append("signal_time_not_found")
            continue
        pos = int(lookup.loc[ts])
        row = f.iloc[pos]
        direction = str(trade["direction"])
        family = str(trade["setup_family"])
        source: str | None = None
        level: float | None = None
        matches: list[str] = []
        method = "unclassified"

        if family == "reversal":
            source, level = _recent_sweep_source(f, pos, direction, recent_sweep_lookback)
            if source:
                matches = _match_level_sources(row, level, direction)
                if source not in matches: matches.insert(0, source)
                method = "recent_directional_sweep_source"
            else:
                method = "recent_sweep_source_missing"
        else:
            try:
                raw = float(row.get("structure_broken_level"))
                level = raw if np.isfinite(raw) else None
            except (TypeError, ValueError):
                level = None
            matches = _match_level_sources(row, level, direction)
            if matches:
                source = matches[0]
                method = "exact_structure_broken_level_match"
            else:
                method = "structure_level_unmatched"

        feature_pos.append(pos)
        level_source.append(source)
        level_value.append(level)
        matched_sources.append("|".join(matches))
        classification_method.append(method)

    out["feature_row_position"] = feature_pos
    out["level_source"] = level_source
    out["level_group"] = pd.Series(level_source, index=out.index).map(lambda x: SOURCE_GROUPS.get(x, "other/unknown") if x else "unclassified")
    out["trigger_level"] = level_value
    out["matched_level_sources"] = matched_sources
    out["level_match_count"] = pd.Series(matched_sources, index=out.index).map(lambda x: 0 if not x else len(x.split("|")))
    out["multi_level_confluence"] = out["level_match_count"] >= 2
    out["level_classification_method"] = classification_method

    pm_width: list[float | None] = []
    for pos in feature_pos:
        if pos is None:
            pm_width.append(None); continue
        row = f.iloc[pos]
        try:
            width = float(row.get("pmh")) - float(row.get("pml"))
            pm_width.append(width if np.isfinite(width) and width >= 0 else None)
        except (TypeError, ValueError):
            pm_width.append(None)
    out["pm_range_points"] = pm_width
    return out


def _segments(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for col in columns:
        if col not in frame.columns: continue
        vals = frame[col].where(frame[col].notna(), "<missing>").astype(str)
        for value in sorted(vals.unique()):
            rows.append({"segment": col, "value": value, **_metrics(frame[vals == value])})
    return rows


def analyze_level_performance(year_frames: dict[int, pd.DataFrame]) -> dict[str, Any]:
    if not year_frames:
        raise LevelResearchError("No enriched trade frames supplied")
    all_ = pd.concat([f.assign(year=year) for year, f in sorted(year_frames.items())], ignore_index=True)
    classified = all_[all_["level_source"].notna()].copy()
    coverage = {
        "total_trades": int(len(all_)),
        "classified_trades": int(len(classified)),
        "classification_rate": float(len(classified) / len(all_)) if len(all_) else 0.0,
        "by_year": {str(y): {"total": int(len(f)), "classified": int(f["level_source"].notna().sum())} for y, f in sorted(year_frames.items())},
        "by_family": {fam: {"total": int((all_.setup_family == fam).sum()), "classified": int(((all_.setup_family == fam) & all_.level_source.notna()).sum())} for fam in ("reversal", "continuation")},
        "methods": {str(k): int(v) for k, v in all_["level_classification_method"].value_counts(dropna=False).items()},
    }
    segments = _segments(classified, ["level_source", "level_group", "setup_family", "direction", "multi_level_confluence"])

    crossed: list[dict[str, Any]] = []
    for dims in (("level_group", "setup_family"), ("level_group", "direction"), ("level_group", "year"), ("level_source", "year")):
        for keys, group in classified.groupby(list(dims), dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            crossed.append({"segment": " x ".join(dims), "value": " | ".join(str(x) for x in keys), **_metrics(group)})

    pm = all_[pd.to_numeric(all_["pm_range_points"], errors="coerce").notna()].copy()
    pm_buckets: list[dict[str, Any]] = []
    if len(pm) >= 4:
        q = pd.to_numeric(pm["pm_range_points"], errors="coerce")
        try:
            pm["pm_range_quartile"] = pd.qcut(q, 4, labels=["Q1 narrow", "Q2", "Q3", "Q4 wide"], duplicates="drop")
            for value, group in pm.groupby("pm_range_quartile", observed=True):
                pm_buckets.append({"bucket": str(value), "min_points": float(group.pm_range_points.min()), "max_points": float(group.pm_range_points.max()), **_metrics(group)})
        except ValueError:
            pass

    return {
        "experiment_id": "EXP-005_important-liquidity-level",
        "coverage": coverage,
        "segments": segments,
        "cross_segments": crossed,
        "pm_range_buckets": pm_buckets,
        "sample_size_note": "Cells under 30 trades are exploratory. Unclassified trades are retained in coverage but excluded from level-performance comparisons. Classification is deterministic and never inferred from nearest price when no exact/source contract exists.",
    }


def metrics_frame(result: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(result["segments"] + result["cross_segments"])


def markdown_report(result: dict[str, Any], ledger_paths: dict[int, str], feature_paths: dict[int, str]) -> str:
    def n(v: Any, d: int = 2) -> str:
        if v is None: return "—"
        try:
            x=float(v)
            if np.isnan(x): return "—"
            if np.isinf(x): return "∞"
            return f"{x:.{d}f}"
        except (TypeError, ValueError): return str(v)
    def pct(v: Any) -> str: return "—" if v is None else f"{100*float(v):.1f}%"
    def row(label: str, m: dict[str, Any]) -> str:
        return f"| {label} | {m.get('trades',0)} | {pct(m.get('win_rate'))} | {n(m.get('expectancy_points'))} | {n(m.get('expectancy_r'),3)} | {n(m.get('profit_factor'))} | {n(m.get('net_points'))} | {pct(m.get('tp1_hit_rate'))} | {pct(m.get('tp2_hit_rate'))} | {pct(m.get('tp3_hit_rate'))} | {pct(m.get('tp4_hit_rate'))} | {pct(m.get('stop_rate'))} | {n(m.get('average_mfe'))} | {n(m.get('median_mfe'))} | {n(m.get('average_mae'))} | {n(m.get('median_mae'))} |"
    header="| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    L=["# EXP-005 — Important Liquidity Level", "", "Diagnostic only; existing trade ledgers are joined to existing scored feature artifacts. No historical pipeline rerun and no strategy change.", "", "## Inputs", ""]
    for y in sorted(ledger_paths): L += [f"- {y} ledger: `{ledger_paths[y]}`", f"- {y} features: `{feature_paths[y]}`"]
    c=result["coverage"]
    L += ["", "## Classification coverage", "", f"- Classified: **{c['classified_trades']}/{c['total_trades']} ({100*c['classification_rate']:.1f}%)**", f"- By family: {c['by_family']}", f"- Methods: {c['methods']}", ""]
    for title, segment in (("Level group performance","level_group"),("Exact level-source performance","level_source")):
        L += [f"## {title}", "", header]
        for item in result["segments"]:
            if item["segment"] == segment: L.append(row(item["value"], item))
        L.append("")
    for title, segment in (("Level group × setup family","level_group x setup_family"),("Level group × direction","level_group x direction"),("Level group × year","level_group x year")):
        L += [f"## {title}", "", header]
        for item in result["cross_segments"]:
            if item["segment"] == segment: L.append(row(item["value"], item))
        L.append("")
    L += ["## Multi-level confluence", "", header]
    for item in result["segments"]:
        if item["segment"] == "multi_level_confluence": L.append(row(item["value"], item))
    L += ["", "## Premarket-range width quartiles", ""]
    if result["pm_range_buckets"]:
        L.append("| Bucket | Range pts | Trades | Exp pts | PF | Net pts |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for x in result["pm_range_buckets"]: L.append(f"| {x['bucket']} | {n(x['min_points'])}–{n(x['max_points'])} | {x.get('trades',0)} | {n(x.get('expectancy_points'))} | {n(x.get('profit_factor'))} | {n(x.get('net_points'))} |")
    else: L.append("- Insufficient variation/sample to form quartiles.")
    L += ["", "## Sample-size / truthfulness rule", "", f"- {result['sample_size_note']}"]
    return "\n".join(L)+"\n"
