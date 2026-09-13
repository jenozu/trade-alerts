"""EXP-015 — Volume / RVOL diagnostics from archived ledgers/features."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class VolumeRVOLResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "volume",
    "volume_percentile_rolling",
    "rvol_rolling",
    "volume_zscore",
    "rvol_time_of_day",
    "rvol_rolling_high",
    "rvol_time_of_day_high",
    "volume_zscore_high",
    "volume_spike_rolling",
    "volume_spike_time_of_day",
    "volume_spike_both",
    "volume_spike_any",
    "rvol_agreement",
    "bullish_volume_context",
    "bearish_volume_context",
    "bullish_volume_breakout",
    "bearish_volume_breakout",
    "bullish_volume_rejection",
    "bearish_volume_rejection",
    "bullish_pullback_low_volume",
    "bearish_pullback_low_volume",
    "volume_context",
    "displacement_rvol",
    "structure_break_rvol",
}


def truthy(v: Any) -> bool:
    if v is None or pd.isna(v):
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def norm(v):
    if v is None or pd.isna(v):
        return None
    return str(v).strip().lower()


def segment(df, col):
    if col not in df.columns:
        return {}

    s = df[col].where(df[col].notna(), "<missing>").astype(str)

    return {
        value: _metrics(df.loc[s == value])
        for value in sorted(s.unique())
    }


def quartiles(df, col):
    s = pd.to_numeric(df[col], errors="coerce")

    if s.notna().sum() < 20:
        return {}

    tmp = df.loc[s.notna()].copy()

    try:
        tmp["_bucket"] = pd.qcut(
            pd.to_numeric(tmp[col], errors="coerce"),
            4,
            duplicates="drop",
        ).astype(str)
    except ValueError:
        return {}

    return segment(tmp, "_bucket")


def threshold_segments(df, col, thresholds):
    values = pd.to_numeric(df[col], errors="coerce")
    result = {}

    for threshold in thresholds:
        label = f">={threshold:.2f}"
        mask = values >= threshold

        if mask.sum() > 0:
            result[label] = _metrics(df.loc[mask])

        below = values < threshold
        if below.sum() > 0:
            result[f"<{threshold:.2f}"] = _metrics(df.loc[below])

    return result


def enrich(ledger: pd.DataFrame, features: pd.DataFrame):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise VolumeRVOLResearchError(
            f"Missing EXP-015 columns: {sorted(missing)}"
        )

    f = features.copy()
    f["timestamp"] = pd.to_datetime(
        f["timestamp"], utc=True, errors="coerce"
    )
    f = (
        f.dropna(subset=["timestamp"])
        .sort_values("timestamp")
        .drop_duplicates("timestamp", keep="last")
        .reset_index(drop=True)
    )

    lookup = pd.Series(f.index, index=f["timestamp"])

    out = ledger.copy()
    out["signal_time"] = pd.to_datetime(
        out["signal_time"], utc=True, errors="coerce"
    )
    out["direction"] = out["direction"].astype(str).str.lower()
    out["setup_family"] = derive_setup_family(out)

    rows = []

    for _, trade in out.iterrows():
        r = trade.to_dict()
        ts = trade["signal_time"]
        r["feature_matched"] = False

        if pd.isna(ts) or ts not in lookup.index:
            rows.append(r)
            continue

        row = f.iloc[int(lookup.loc[ts])]
        r["feature_matched"] = True

        direction = str(trade["direction"])
        side = "bullish" if direction == "long" else "bearish"

        for col in (
            "volume",
            "volume_percentile_rolling",
            "rvol_rolling",
            "volume_zscore",
            "rvol_time_of_day",
            "displacement_rvol",
            "structure_break_rvol",
        ):
            r[col] = safe_float(row.get(col))

        for col in (
            "rvol_rolling_high",
            "rvol_time_of_day_high",
            "volume_zscore_high",
            "volume_spike_rolling",
            "volume_spike_time_of_day",
            "volume_spike_both",
            "volume_spike_any",
            "rvol_agreement",
        ):
            r[col] = truthy(row.get(col))

        r["directional_volume_context"] = truthy(
            row.get(f"{side}_volume_context")
        )
        r["directional_volume_breakout"] = truthy(
            row.get(f"{side}_volume_breakout")
        )
        r["directional_volume_rejection"] = truthy(
            row.get(f"{side}_volume_rejection")
        )
        r["directional_pullback_low_volume"] = truthy(
            row.get(f"{side}_pullback_low_volume")
        )

        r["volume_context_exact"] = norm(
            row.get("volume_context")
        )

        rows.append(r)

    return pd.DataFrame(rows)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise VolumeRVOLResearchError(
            "EXP-015 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-015_volume-rvol",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "overall": _metrics(df),

        "rvol_rolling_quartiles": quartiles(
            df, "rvol_rolling"
        ),
        "rvol_tod_quartiles": quartiles(
            df, "rvol_time_of_day"
        ),
        "volume_percentile_quartiles": quartiles(
            df, "volume_percentile_rolling"
        ),
        "volume_zscore_quartiles": quartiles(
            df, "volume_zscore"
        ),
        "displacement_rvol_quartiles": quartiles(
            df, "displacement_rvol"
        ),
        "structure_break_rvol_quartiles": quartiles(
            df, "structure_break_rvol"
        ),

        "rvol_rolling_thresholds": threshold_segments(
            df,
            "rvol_rolling",
            (1.0, 1.2, 1.5, 2.0),
        ),
        "rvol_tod_thresholds": threshold_segments(
            df,
            "rvol_time_of_day",
            (1.0, 1.2, 1.5, 2.0),
        ),

        "volume_spike_any": segment(
            df, "volume_spike_any"
        ),
        "volume_spike_rolling": segment(
            df, "volume_spike_rolling"
        ),
        "volume_spike_tod": segment(
            df, "volume_spike_time_of_day"
        ),
        "volume_spike_both": segment(
            df, "volume_spike_both"
        ),
        "rvol_agreement": segment(
            df, "rvol_agreement"
        ),

        "directional_volume_context": segment(
            df, "directional_volume_context"
        ),
        "directional_breakout_volume": segment(
            df, "directional_volume_breakout"
        ),
        "directional_rejection_volume": segment(
            df, "directional_volume_rejection"
        ),
        "directional_pullback_low_volume": segment(
            df, "directional_pullback_low_volume"
        ),
        "volume_context": segment(
            df, "volume_context_exact"
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "rvol_rolling_quartiles": quartiles(
                g, "rvol_rolling"
            ),
            "rvol_tod_quartiles": quartiles(
                g, "rvol_time_of_day"
            ),
            "volume_spike_any": segment(
                g, "volume_spike_any"
            ),
            "breakout_volume": segment(
                g, "directional_volume_breakout"
            ),
            "rejection_volume": segment(
                g, "directional_volume_rejection"
            ),
            "pullback_low_volume": segment(
                g, "directional_pullback_low_volume"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "rvol_rolling_quartiles": quartiles(
                g, "rvol_rolling"
            ),
            "rvol_tod_quartiles": quartiles(
                g, "rvol_time_of_day"
            ),
            "volume_spike_any": segment(
                g, "volume_spike_any"
            ),
            "breakout_volume": segment(
                g, "directional_volume_breakout"
            ),
            "rejection_volume": segment(
                g, "directional_volume_rejection"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "rvol_rolling_quartiles": quartiles(
                g, "rvol_rolling"
            ),
            "rvol_tod_quartiles": quartiles(
                g, "rvol_time_of_day"
            ),
            "volume_spike_any": segment(
                g, "volume_spike_any"
            ),
            "breakout_volume": segment(
                g, "directional_volume_breakout"
            ),
            "rejection_volume": segment(
                g, "directional_volume_rejection"
            ),
            "pullback_low_volume": segment(
                g, "directional_pullback_low_volume"
            ),
        }

    return result, df


def metrics_frame(result):
    rows = []

    def add(section, values):
        for value, metrics in values.items():
            if isinstance(metrics, dict) and "trades" in metrics:
                rows.append({
                    "section": section,
                    "value": value,
                    **metrics,
                })

    base_sections = (
        "rvol_rolling_quartiles",
        "rvol_tod_quartiles",
        "volume_percentile_quartiles",
        "volume_zscore_quartiles",
        "displacement_rvol_quartiles",
        "structure_break_rvol_quartiles",
        "rvol_rolling_thresholds",
        "rvol_tod_thresholds",
        "volume_spike_any",
        "volume_spike_rolling",
        "volume_spike_tod",
        "volume_spike_both",
        "rvol_agreement",
        "directional_volume_context",
        "directional_breakout_volume",
        "directional_rejection_volume",
        "directional_pullback_low_volume",
        "volume_context",
    )

    for section in base_sections:
        add(section, result[section])

    for year, sections in result["by_year"].items():
        for section, values in sections.items():
            add(f"year_{year}_{section}", values)

    for direction, sections in result["by_direction"].items():
        for section, values in sections.items():
            add(f"direction_{direction}_{section}", values)

    for family, sections in result["by_family"].items():
        for section, values in sections.items():
            add(f"family_{family}_{section}", values)

    return pd.DataFrame(rows)


def markdown_report(result):
    def num(v, digits=2):
        if v is None:
            return "—"
        try:
            if np.isnan(v):
                return "—"
            if np.isinf(v):
                return "∞"
        except TypeError:
            pass
        return f"{float(v):.{digits}f}"

    def pct(v):
        return "—" if v is None else f"{100*float(v):.1f}%"

    def table(values):
        lines = [
            "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]

        for label, m in values.items():
            lines.append(
                f"| {label} | {m.get('trades',0)} | "
                f"{pct(m.get('win_rate'))} | "
                f"{num(m.get('expectancy_points'))} | "
                f"{num(m.get('expectancy_r'),3)} | "
                f"{num(m.get('profit_factor'))} | "
                f"{num(m.get('net_points'))} | "
                f"{pct(m.get('tp1_hit_rate'))} | "
                f"{pct(m.get('tp2_hit_rate'))} | "
                f"{pct(m.get('tp3_hit_rate'))} | "
                f"{pct(m.get('tp4_hit_rate'))} | "
                f"{pct(m.get('stop_rate'))} |"
            )

        return "\n".join(lines)

    lines = [
        "# EXP-015 — Volume / RVOL",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        ("Rolling RVOL quartiles", "rvol_rolling_quartiles"),
        ("Time-of-day RVOL quartiles", "rvol_tod_quartiles"),
        ("Rolling volume percentile", "volume_percentile_quartiles"),
        ("Volume z-score", "volume_zscore_quartiles"),
        ("Displacement RVOL", "displacement_rvol_quartiles"),
        ("Structure-break RVOL", "structure_break_rvol_quartiles"),
        ("Rolling RVOL thresholds", "rvol_rolling_thresholds"),
        ("Time-of-day RVOL thresholds", "rvol_tod_thresholds"),
        ("Any volume spike", "volume_spike_any"),
        ("Rolling volume spike", "volume_spike_rolling"),
        ("Time-of-day volume spike", "volume_spike_tod"),
        ("Both spike definitions", "volume_spike_both"),
        ("RVOL agreement", "rvol_agreement"),
        ("Directional volume context", "directional_volume_context"),
        ("Directional breakout volume", "directional_breakout_volume"),
        ("Directional rejection volume", "directional_rejection_volume"),
        ("Low-volume pullback", "directional_pullback_low_volume"),
        ("Persisted volume context", "volume_context"),
    )

    for title, key in sections:
        lines += [
            f"## {title}",
            "",
            table(result[key]),
            "",
        ]

    lines += ["## Setup-family diagnostics", ""]

    for family, sections in result["by_family"].items():
        lines += [f"### {family}", ""]

        for name, values in sections.items():
            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += ["## Year diagnostics", ""]

    for year, sections in result["by_year"].items():
        lines += [f"### {year}", ""]

        for name, values in sections.items():
            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += [
        "## Research discipline",
        "",
        "- RVOL thresholds are diagnostic comparisons, not proposed production cutoffs.",
        "- Breakout, rejection, and low-volume-pullback fields use persisted directional features only.",
        "- Retest-volume behavior is not separately invented if no explicit retest-volume feature exists.",
        "- No score weights, entries, stops, targets, or filters changed.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
