"""EXP-014 — Draw on Liquidity diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class DOLResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "draw_on_liquidity_direction",
    "dol_direction",
    "dol_target_type",
    "dol_target_category",
    "dol_target_price",
    "dol_distance_points",
    "dol_confidence",
    "dol_primary_direction",
    "dol_primary_target_type",
    "dol_primary_target_category",
    "dol_primary_target_price",
    "dol_primary_distance_points",
    "dol_primary_confidence",
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


def segment(df, col):
    s = df[col].where(df[col].notna(), "<missing>").astype(str)
    return {
        v: _metrics(df.loc[s == v])
        for v in sorted(s.unique())
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


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise DOLResearchError(
            f"Missing EXP-014 columns: {sorted(missing)}"
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

        dol = norm(row.get("dol_primary_direction"))
        if dol is None:
            dol = norm(row.get("dol_direction"))
        if dol is None:
            dol = norm(row.get("draw_on_liquidity_direction"))

        direction = str(trade["direction"])
        r["dol_direction_exp014"] = dol

        if dol in {"bullish", "long", "up"}:
            r["dol_alignment"] = (
                "aligned" if direction == "long" else "opposed"
            )
        elif dol in {"bearish", "short", "down"}:
            r["dol_alignment"] = (
                "aligned" if direction == "short" else "opposed"
            )
        else:
            r["dol_alignment"] = "neutral/unknown"

        r["dol_target_type"] = norm(
            row.get("dol_primary_target_type")
        ) or norm(row.get("dol_target_type"))

        r["dol_target_category"] = norm(
            row.get("dol_primary_target_category")
        ) or norm(row.get("dol_target_category"))

        r["dol_distance_points_exp014"] = (
            safe_float(row.get("dol_primary_distance_points"))
            if safe_float(row.get("dol_primary_distance_points")) is not None
            else safe_float(row.get("dol_distance_points"))
        )

        r["dol_confidence_exp014"] = (
            safe_float(row.get("dol_primary_confidence"))
            if safe_float(row.get("dol_primary_confidence")) is not None
            else safe_float(row.get("dol_confidence"))
        )

        rows.append(r)

    return pd.DataFrame(rows)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise DOLResearchError(
            "EXP-014 requires 2023/2024/2025"
        )

    all_frames = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        all_frames.append(x)

    df = pd.concat(all_frames, ignore_index=True)

    result = {
        "experiment_id": "EXP-014_draw-on-liquidity",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "alignment": segment(df, "dol_alignment"),
        "target_type": segment(df, "dol_target_type"),
        "target_category": segment(df, "dol_target_category"),
        "confidence_quartiles": quartiles(
            df, "dol_confidence_exp014"
        ),
        "distance_quartiles": quartiles(
            df, "dol_distance_points_exp014"
        ),
        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]
        result["by_year"][str(year)] = {
            "alignment": segment(y, "dol_alignment"),
            "target_category": segment(
                y, "dol_target_category"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]
        result["by_direction"][direction] = {
            "alignment": segment(g, "dol_alignment"),
            "target_category": segment(
                g, "dol_target_category"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]
        result["by_family"][family] = {
            "alignment": segment(g, "dol_alignment"),
            "target_category": segment(
                g, "dol_target_category"
            ),
        }

    return result, df


def metrics_frame(result):
    rows = []

    def add(section, values):
        for value, m in values.items():
            if isinstance(m, dict) and "trades" in m:
                rows.append({
                    "section": section,
                    "value": value,
                    **m,
                })

    for section in (
        "alignment",
        "target_type",
        "target_category",
        "confidence_quartiles",
        "distance_quartiles",
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
    def n(v, d=2):
        if v is None:
            return "—"
        try:
            if np.isnan(v):
                return "—"
            if np.isinf(v):
                return "∞"
        except TypeError:
            pass
        return f"{float(v):.{d}f}"

    def p(v):
        return "—" if v is None else f"{100*float(v):.1f}%"

    def table(values):
        lines = [
            "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]

        for label, m in values.items():
            lines.append(
                f"| {label} | {m.get('trades',0)} | "
                f"{p(m.get('win_rate'))} | "
                f"{n(m.get('expectancy_points'))} | "
                f"{n(m.get('expectancy_r'),3)} | "
                f"{n(m.get('profit_factor'))} | "
                f"{n(m.get('net_points'))} |"
            )

        return "\n".join(lines)

    lines = [
        "# EXP-014 — Draw on Liquidity",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    for title, key in (
        ("Trade alignment with DOL", "alignment"),
        ("DOL target type", "target_type"),
        ("DOL target category", "target_category"),
        ("DOL confidence quartiles", "confidence_quartiles"),
        ("Distance to primary DOL target quartiles", "distance_quartiles"),
    ):
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
        "- Opposed-DOL baseline sample may be extremely small because DOL already participates in scoring/selection.",
        "- Target cleanliness/untouched status is reported only if encoded by target type/category; no new classification is invented.",
        "- No strategy change is authorized.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
