"""EXP-016 — SNR / efficiency diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class SNREfficiencyResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",

    "snr_1m",
    "snr_direction_1m",
    "snr_delta_1m",
    "snr_slope_1m",
    "efficiency_1m",

    "snr_5m",
    "snr_direction_5m",
    "snr_delta_5m",
    "snr_slope_5m",
    "efficiency_5m",

    "snr_15m",
    "snr_direction_15m",
    "snr_delta_15m",
    "snr_slope_15m",
    "efficiency_15m",

    "snr_alignment",
    "snr_composite_quality",
    "snr_quality_class",
    "snr_confidence_modifier_points",
    "snr_confidence_modifier_enabled",

    "long_score_signal_to_noise",
    "short_score_signal_to_noise",
}


def norm(v):
    if v is None or pd.isna(v):
        return None
    return str(v).strip().lower()


def safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def truthy(v):
    if v is None or pd.isna(v):
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


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

    x = df.loc[s.notna()].copy()

    try:
        x["_bucket"] = pd.qcut(
            pd.to_numeric(x[col], errors="coerce"),
            4,
            duplicates="drop",
        ).astype(str)
    except ValueError:
        return {}

    return segment(x, "_bucket")


def direction_alignment(trade_direction, snr_direction):
    d = norm(snr_direction)

    if d in {"bullish", "long", "up", "positive"}:
        return "aligned" if trade_direction == "long" else "opposed"

    if d in {"bearish", "short", "down", "negative"}:
        return "aligned" if trade_direction == "short" else "opposed"

    return "neutral/unknown"


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)

    if missing:
        raise SNREfficiencyResearchError(
            f"Missing EXP-016 columns: {sorted(missing)}"
        )

    f = features.copy()

    f["timestamp"] = pd.to_datetime(
        f["timestamp"],
        utc=True,
        errors="coerce",
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
        out["signal_time"],
        utc=True,
        errors="coerce",
    )

    out["direction"] = (
        out["direction"]
        .astype(str)
        .str.lower()
    )

    out["setup_family"] = derive_setup_family(out)

    records = []

    for _, trade in out.iterrows():
        r = trade.to_dict()

        ts = trade["signal_time"]

        r["feature_matched"] = False

        if pd.isna(ts) or ts not in lookup.index:
            records.append(r)
            continue

        row = f.iloc[int(lookup.loc[ts])]

        r["feature_matched"] = True

        direction = str(trade["direction"])

        for tf in ("1m", "5m", "15m"):
            r[f"snr_{tf}_exp016"] = safe_float(
                row.get(f"snr_{tf}")
            )

            r[f"snr_delta_{tf}_exp016"] = safe_float(
                row.get(f"snr_delta_{tf}")
            )

            r[f"snr_slope_{tf}_exp016"] = safe_float(
                row.get(f"snr_slope_{tf}")
            )

            r[f"efficiency_{tf}_exp016"] = safe_float(
                row.get(f"efficiency_{tf}")
            )

            r[f"snr_direction_{tf}_exp016"] = norm(
                row.get(f"snr_direction_{tf}")
            )

            r[f"snr_trade_alignment_{tf}"] = direction_alignment(
                direction,
                row.get(f"snr_direction_{tf}"),
            )

        r["snr_alignment_exact"] = norm(
            row.get("snr_alignment")
        )

        r["snr_quality_class_exact"] = norm(
            row.get("snr_quality_class")
        )

        r["snr_composite_quality_exp016"] = safe_float(
            row.get("snr_composite_quality")
        )

        r["snr_confidence_modifier_points_exp016"] = safe_float(
            row.get("snr_confidence_modifier_points")
        )

        r["snr_confidence_modifier_enabled_exp016"] = truthy(
            row.get("snr_confidence_modifier_enabled")
        )

        side_score_col = (
            "long_score_signal_to_noise"
            if direction == "long"
            else "short_score_signal_to_noise"
        )

        r["directional_snr_score"] = safe_float(
            row.get(side_score_col)
        )

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise SNREfficiencyResearchError(
            "EXP-016 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-016_snr-efficiency",

        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },

        "snr_1m_quartiles": quartiles(
            df, "snr_1m_exp016"
        ),
        "snr_5m_quartiles": quartiles(
            df, "snr_5m_exp016"
        ),
        "snr_15m_quartiles": quartiles(
            df, "snr_15m_exp016"
        ),

        "efficiency_1m_quartiles": quartiles(
            df, "efficiency_1m_exp016"
        ),
        "efficiency_5m_quartiles": quartiles(
            df, "efficiency_5m_exp016"
        ),
        "efficiency_15m_quartiles": quartiles(
            df, "efficiency_15m_exp016"
        ),

        "snr_delta_1m_quartiles": quartiles(
            df, "snr_delta_1m_exp016"
        ),
        "snr_delta_5m_quartiles": quartiles(
            df, "snr_delta_5m_exp016"
        ),
        "snr_delta_15m_quartiles": quartiles(
            df, "snr_delta_15m_exp016"
        ),

        "snr_slope_1m_quartiles": quartiles(
            df, "snr_slope_1m_exp016"
        ),
        "snr_slope_5m_quartiles": quartiles(
            df, "snr_slope_5m_exp016"
        ),
        "snr_slope_15m_quartiles": quartiles(
            df, "snr_slope_15m_exp016"
        ),

        "alignment_1m": segment(
            df, "snr_trade_alignment_1m"
        ),
        "alignment_5m": segment(
            df, "snr_trade_alignment_5m"
        ),
        "alignment_15m": segment(
            df, "snr_trade_alignment_15m"
        ),

        "production_alignment": segment(
            df, "snr_alignment_exact"
        ),

        "quality_class": segment(
            df, "snr_quality_class_exact"
        ),

        "composite_quality_quartiles": quartiles(
            df, "snr_composite_quality_exp016"
        ),

        "directional_score_quartiles": quartiles(
            df, "directional_snr_score"
        ),

        "confidence_modifier": segment(
            df, "snr_confidence_modifier_enabled_exp016"
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "snr_1m": quartiles(
                g, "snr_1m_exp016"
            ),
            "snr_5m": quartiles(
                g, "snr_5m_exp016"
            ),
            "snr_15m": quartiles(
                g, "snr_15m_exp016"
            ),
            "efficiency_1m": quartiles(
                g, "efficiency_1m_exp016"
            ),
            "quality_class": segment(
                g, "snr_quality_class_exact"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "snr_1m": quartiles(
                g, "snr_1m_exp016"
            ),
            "snr_5m": quartiles(
                g, "snr_5m_exp016"
            ),
            "snr_15m": quartiles(
                g, "snr_15m_exp016"
            ),
            "alignment_1m": segment(
                g, "snr_trade_alignment_1m"
            ),
            "alignment_5m": segment(
                g, "snr_trade_alignment_5m"
            ),
            "alignment_15m": segment(
                g, "snr_trade_alignment_15m"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "snr_1m": quartiles(
                g, "snr_1m_exp016"
            ),
            "snr_5m": quartiles(
                g, "snr_5m_exp016"
            ),
            "snr_15m": quartiles(
                g, "snr_15m_exp016"
            ),
            "efficiency_1m": quartiles(
                g, "efficiency_1m_exp016"
            ),
            "efficiency_5m": quartiles(
                g, "efficiency_5m_exp016"
            ),
            "efficiency_15m": quartiles(
                g, "efficiency_15m_exp016"
            ),
            "quality_class": segment(
                g, "snr_quality_class_exact"
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

    base = (
        "snr_1m_quartiles",
        "snr_5m_quartiles",
        "snr_15m_quartiles",
        "efficiency_1m_quartiles",
        "efficiency_5m_quartiles",
        "efficiency_15m_quartiles",
        "snr_delta_1m_quartiles",
        "snr_delta_5m_quartiles",
        "snr_delta_15m_quartiles",
        "snr_slope_1m_quartiles",
        "snr_slope_5m_quartiles",
        "snr_slope_15m_quartiles",
        "alignment_1m",
        "alignment_5m",
        "alignment_15m",
        "production_alignment",
        "quality_class",
        "composite_quality_quartiles",
        "directional_score_quartiles",
        "confidence_modifier",
    )

    for section in base:
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
        "# EXP-016 — SNR / Efficiency",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        ("1m SNR quartiles", "snr_1m_quartiles"),
        ("5m SNR quartiles", "snr_5m_quartiles"),
        ("15m SNR quartiles", "snr_15m_quartiles"),

        ("1m efficiency quartiles", "efficiency_1m_quartiles"),
        ("5m efficiency quartiles", "efficiency_5m_quartiles"),
        ("15m efficiency quartiles", "efficiency_15m_quartiles"),

        ("1m SNR delta", "snr_delta_1m_quartiles"),
        ("5m SNR delta", "snr_delta_5m_quartiles"),
        ("15m SNR delta", "snr_delta_15m_quartiles"),

        ("1m SNR slope", "snr_slope_1m_quartiles"),
        ("5m SNR slope", "snr_slope_5m_quartiles"),
        ("15m SNR slope", "snr_slope_15m_quartiles"),

        ("Trade alignment with 1m SNR direction", "alignment_1m"),
        ("Trade alignment with 5m SNR direction", "alignment_5m"),
        ("Trade alignment with 15m SNR direction", "alignment_15m"),

        ("Persisted SNR alignment", "production_alignment"),
        ("SNR quality class", "quality_class"),
        ("Composite SNR quality", "composite_quality_quartiles"),
        ("Directional SNR score", "directional_score_quartiles"),
        ("Confidence modifier enabled", "confidence_modifier"),
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
        "## Limitations",
        "",
        "- Existing baseline trades only.",
        "- Quartiles measure association, not causal benefit.",
        "- SNR is already represented in production scoring, so some comparisons are selection-confounded.",
        "- SNR direction, composite quality, and quality class may overlap mathematically and should not automatically receive independent score credit.",
        "- No threshold or score change is authorized.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
