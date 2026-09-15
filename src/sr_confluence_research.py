"""EXP-018 — Support / resistance confluence diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class SRConfluenceResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "long_score_detail_key_location_confluence_aligned",
    "short_score_detail_key_location_confluence_aligned",
    "long_score_detail_key_location_confluence_score",
    "short_score_detail_key_location_confluence_score",
    "internal_swing_high_equal_cluster_count",
    "internal_swing_low_equal_cluster_count",
    "external_swing_high_equal_cluster_count",
    "external_swing_low_equal_cluster_count",
}


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
    try:
        return float(v) != 0.0
    except (TypeError, ValueError):
        return str(v).strip().lower() in {"true", "yes", "y"}


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


def score_bands(df):
    s = pd.to_numeric(
        df["directional_confluence_score"],
        errors="coerce",
    )

    x = df.loc[s.notna()].copy()

    if x.empty:
        return {}

    bins = [-np.inf, 30, 50, 60, 70, 80, 90, np.inf]
    labels = [
        "<=30",
        "30-50",
        "50-60",
        "60-70",
        "70-80",
        "80-90",
        "90+",
    ]

    x["_confluence_band"] = pd.cut(
        pd.to_numeric(
            x["directional_confluence_score"],
            errors="coerce",
        ),
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=True,
    ).astype(str)

    return segment(x, "_confluence_band")


def count_bucket(v):
    x = safe_float(v)

    if x is None:
        return "unknown"

    if x <= 0:
        return "0"

    if x == 1:
        return "1"

    if x == 2:
        return "2"

    return "3+"


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)

    if missing:
        raise SRConfluenceResearchError(
            f"Missing EXP-018 fields: {sorted(missing)}"
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

    lookup = pd.Series(
        f.index,
        index=f["timestamp"],
    )

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

        if direction == "long":
            aligned_col = (
                "long_score_detail_key_location_confluence_aligned"
            )
            score_col = (
                "long_score_detail_key_location_confluence_score"
            )
        else:
            aligned_col = (
                "short_score_detail_key_location_confluence_aligned"
            )
            score_col = (
                "short_score_detail_key_location_confluence_score"
            )

        r["directional_confluence_aligned"] = truthy(
            row.get(aligned_col)
        )

        r["directional_confluence_score"] = safe_float(
            row.get(score_col)
        )

        cluster_cols = [
            "internal_swing_high_equal_cluster_count",
            "internal_swing_low_equal_cluster_count",
            "external_swing_high_equal_cluster_count",
            "external_swing_low_equal_cluster_count",
        ]

        total = 0

        for col in cluster_cols:
            value = safe_float(row.get(col))

            r[col] = value

            if value is not None:
                total += int(value)

            r[f"{col}_bucket"] = count_bucket(value)

        r["equal_cluster_total"] = total
        r["equal_cluster_total_bucket"] = count_bucket(total)

        # These are raw persisted cluster counts only.
        # We deliberately do NOT reinterpret them as a custom S/R score.

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise SRConfluenceResearchError(
            "EXP-018 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-018_sr-confluence",

        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },

        "aligned": segment(
            df,
            "directional_confluence_aligned",
        ),

        "score_quartiles": quartiles(
            df,
            "directional_confluence_score",
        ),

        "score_bands": score_bands(df),

        "equal_cluster_total": segment(
            df,
            "equal_cluster_total_bucket",
        ),

        "internal_high_cluster": segment(
            df,
            "internal_swing_high_equal_cluster_count_bucket",
        ),

        "internal_low_cluster": segment(
            df,
            "internal_swing_low_equal_cluster_count_bucket",
        ),

        "external_high_cluster": segment(
            df,
            "external_swing_high_equal_cluster_count_bucket",
        ),

        "external_low_cluster": segment(
            df,
            "external_swing_low_equal_cluster_count_bucket",
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "aligned": segment(
                g,
                "directional_confluence_aligned",
            ),
            "score_quartiles": quartiles(
                g,
                "directional_confluence_score",
            ),
            "score_bands": score_bands(g),
            "equal_cluster_total": segment(
                g,
                "equal_cluster_total_bucket",
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "aligned": segment(
                g,
                "directional_confluence_aligned",
            ),
            "score_quartiles": quartiles(
                g,
                "directional_confluence_score",
            ),
            "score_bands": score_bands(g),
            "equal_cluster_total": segment(
                g,
                "equal_cluster_total_bucket",
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "aligned": segment(
                g,
                "directional_confluence_aligned",
            ),
            "score_quartiles": quartiles(
                g,
                "directional_confluence_score",
            ),
            "score_bands": score_bands(g),
            "equal_cluster_total": segment(
                g,
                "equal_cluster_total_bucket",
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

    for section in (
        "aligned",
        "score_quartiles",
        "score_bands",
        "equal_cluster_total",
        "internal_high_cluster",
        "internal_low_cluster",
        "external_high_cluster",
        "external_low_cluster",
    ):
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
        if v is None:
            return "—"
        return f"{100 * float(v):.1f}%"

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
        "# EXP-018 — Support / Resistance Confluence",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        (
            "Persisted directional confluence alignment",
            "aligned",
        ),
        (
            "Persisted directional confluence-score quartiles",
            "score_quartiles",
        ),
        (
            "Persisted directional confluence-score bands",
            "score_bands",
        ),
        (
            "Total persisted equal-high/low cluster count",
            "equal_cluster_total",
        ),
        (
            "Internal swing-high equal-cluster count",
            "internal_high_cluster",
        ),
        (
            "Internal swing-low equal-cluster count",
            "internal_low_cluster",
        ),
        (
            "External swing-high equal-cluster count",
            "external_high_cluster",
        ),
        (
            "External swing-low equal-cluster count",
            "external_low_cluster",
        ),
    )

    for title, key in sections:
        lines += [
            f"## {title}",
            "",
            table(result[key]),
            "",
        ]

    lines += [
        "## Setup-family diagnostics",
        "",
    ]

    for family, sections in result["by_family"].items():
        lines += [
            f"### {family}",
            "",
        ]

        for name, values in sections.items():
            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += [
        "## Direction diagnostics",
        "",
    ]

    for direction, sections in result["by_direction"].items():
        lines += [
            f"### {direction}",
            "",
        ]

        for name, values in sections.items():
            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += [
        "## Year diagnostics",
        "",
    ]

    for year, sections in result["by_year"].items():
        lines += [
            f"### {year}",
            "",
        ]

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
        "- The persisted directional confluence score is analyzed as stored; EXP-018 does not reverse-engineer or redefine it.",
        "- Equal-high/low cluster counts are separate structural diagnostics and are not treated as equivalent to the persisted confluence score.",
        "- No new proximity-based S/R formula is invented.",
        "- If source-level decomposition is not encoded separately in the persisted confluence field, EXP-018 cannot identify every source contribution independently.",
        "- Association does not prove independent causal lift because confluence already participates in historical scoring.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
