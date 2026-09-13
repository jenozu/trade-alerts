"""EXP-011 — FVG / IFVG diagnostics from archived ledgers/features."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class FVGResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "bullish_fvg_created",
    "bearish_fvg_created",
    "bullish_fvg_size_points",
    "bearish_fvg_size_points",
    "bullish_fvg_first_touch",
    "bearish_fvg_first_touch",
    "bullish_fvg_retest_hold",
    "bearish_fvg_retest_hold",
    "bullish_fvg_full_fill",
    "bearish_fvg_full_fill",
    "bullish_ifvg_created",
    "bearish_ifvg_created",
    "bullish_ifvg_created_recent",
    "bearish_ifvg_created_recent",
    "bullish_ifvg_respected_recent",
    "bearish_ifvg_respected_recent",
    "bullish_ifvg_disrespected_recent",
    "bearish_ifvg_disrespected_recent",
    "bullish_core_plus_fvg",
    "bearish_core_plus_fvg",
    "bullish_core_plus_fvg_retest",
    "bearish_core_plus_fvg_retest",
    "nearest_active_bullish_fvg_lower",
    "nearest_active_bullish_fvg_upper",
    "nearest_active_bearish_fvg_lower",
    "nearest_active_bearish_fvg_upper",
    "distance_to_bullish_fvg",
    "distance_to_bearish_fvg",
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


def enrich(ledger: pd.DataFrame, features: pd.DataFrame):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise FVGResearchError(
            f"Missing EXP-011 feature columns: {sorted(missing)}"
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
    out["score_band"] = pd.to_numeric(
        out["raw_score"], errors="coerce"
    ).map(_score_band)

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

        long_side = str(trade["direction"]) == "long"
        side = "bullish" if long_side else "bearish"

        r["directional_fvg_created"] = truthy(
            row.get(f"{side}_fvg_created")
        )

        r["directional_fvg_first_touch"] = truthy(
            row.get(f"{side}_fvg_first_touch")
        )

        r["directional_fvg_retest_hold"] = truthy(
            row.get(f"{side}_fvg_retest_hold")
        )

        r["directional_fvg_full_fill"] = truthy(
            row.get(f"{side}_fvg_full_fill")
        )

        r["directional_ifvg_created"] = truthy(
            row.get(f"{side}_ifvg_created")
        )

        r["recent_ifvg_created"] = truthy(
            row.get(f"{side}_ifvg_created_recent")
        )

        r["recent_ifvg_respected"] = truthy(
            row.get(f"{side}_ifvg_respected_recent")
        )

        r["recent_ifvg_disrespected"] = truthy(
            row.get(f"{side}_ifvg_disrespected_recent")
        )

        r["core_plus_fvg"] = truthy(
            row.get(f"{side}_core_plus_fvg")
        )

        r["core_plus_fvg_retest"] = truthy(
            row.get(f"{side}_core_plus_fvg_retest")
        )

        r["directional_fvg_size"] = safe_float(
            row.get(f"{side}_fvg_size_points")
        )

        if long_side:
            lower = safe_float(
                row.get("nearest_active_bullish_fvg_lower")
            )
            upper = safe_float(
                row.get("nearest_active_bullish_fvg_upper")
            )
            distance = safe_float(
                row.get("distance_to_bullish_fvg")
            )
        else:
            lower = safe_float(
                row.get("nearest_active_bearish_fvg_lower")
            )
            upper = safe_float(
                row.get("nearest_active_bearish_fvg_upper")
            )
            distance = safe_float(
                row.get("distance_to_bearish_fvg")
            )

        r["active_directional_fvg"] = (
            lower is not None and upper is not None
        )
        r["distance_to_directional_fvg"] = distance

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise FVGResearchError(
            "EXP-011 requires 2023/2024/2025"
        )

    all_frames = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        all_frames.append(x)

    df = pd.concat(all_frames, ignore_index=True)

    result = {
        "experiment_id": "EXP-011_fvg-ifvg",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "overall": _metrics(df),
        "fvg_created": segment(df, "directional_fvg_created"),
        "active_fvg": segment(df, "active_directional_fvg"),
        "first_touch": segment(df, "directional_fvg_first_touch"),
        "retest_hold": segment(df, "directional_fvg_retest_hold"),
        "full_fill": segment(df, "directional_fvg_full_fill"),
        "ifvg_created": segment(df, "directional_ifvg_created"),
        "recent_ifvg_created": segment(df, "recent_ifvg_created"),
        "recent_ifvg_respected": segment(df, "recent_ifvg_respected"),
        "recent_ifvg_disrespected": segment(
            df, "recent_ifvg_disrespected"
        ),
        "core_plus_fvg": segment(df, "core_plus_fvg"),
        "core_plus_fvg_retest": segment(
            df, "core_plus_fvg_retest"
        ),
        "fvg_size_quartiles": quartiles(
            df[df["directional_fvg_created"]],
            "directional_fvg_size",
        ),
        "distance_quartiles": quartiles(
            df[df["active_directional_fvg"]],
            "distance_to_directional_fvg",
        ),
        "by_year": {},
        "by_family": {},
        "by_direction": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "fvg_created": segment(
                y, "directional_fvg_created"
            ),
            "retest_hold": segment(
                y, "directional_fvg_retest_hold"
            ),
            "ifvg_created": segment(
                y, "recent_ifvg_created"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "fvg_created": segment(
                g, "directional_fvg_created"
            ),
            "retest_hold": segment(
                g, "directional_fvg_retest_hold"
            ),
            "core_plus_fvg": segment(
                g, "core_plus_fvg"
            ),
            "ifvg_created": segment(
                g, "recent_ifvg_created"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "fvg_created": segment(
                g, "directional_fvg_created"
            ),
            "retest_hold": segment(
                g, "directional_fvg_retest_hold"
            ),
            "ifvg_created": segment(
                g, "recent_ifvg_created"
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
        "fvg_created",
        "active_fvg",
        "first_touch",
        "retest_hold",
        "full_fill",
        "ifvg_created",
        "recent_ifvg_created",
        "recent_ifvg_respected",
        "recent_ifvg_disrespected",
        "core_plus_fvg",
        "core_plus_fvg_retest",
        "fvg_size_quartiles",
        "distance_quartiles",
    ):
        add(section, result[section])

    for year, sections in result["by_year"].items():
        for section, values in sections.items():
            add(f"year_{year}_{section}", values)

    for family, sections in result["by_family"].items():
        for section, values in sections.items():
            add(f"family_{family}_{section}", values)

    for direction, sections in result["by_direction"].items():
        for section, values in sections.items():
            add(f"direction_{direction}_{section}", values)

    return pd.DataFrame(rows)


def markdown_report(result):
    def n(v, d=2):
        if v is None:
            return "—"
        try:
            if np.isinf(v):
                return "∞"
            if np.isnan(v):
                return "—"
        except TypeError:
            pass
        return f"{float(v):.{d}f}"

    def p(v):
        return "—" if v is None else f"{100*float(v):.1f}%"

    def table(values):
        lines = [
            "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]

        for label, m in values.items():
            lines.append(
                f"| {label} | {m.get('trades',0)} | "
                f"{p(m.get('win_rate'))} | "
                f"{n(m.get('expectancy_points'))} | "
                f"{n(m.get('expectancy_r'),3)} | "
                f"{n(m.get('profit_factor'))} | "
                f"{n(m.get('net_points'))} | "
                f"{p(m.get('tp1_hit_rate'))} | "
                f"{p(m.get('tp2_hit_rate'))} | "
                f"{p(m.get('tp3_hit_rate'))} | "
                f"{p(m.get('tp4_hit_rate'))} | "
                f"{p(m.get('stop_rate'))} |"
            )

        return "\n".join(lines)

    lines = [
        "# EXP-011 — FVG / IFVG",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        ("Directional FVG created", "fvg_created"),
        ("Active directional FVG", "active_fvg"),
        ("FVG first touch", "first_touch"),
        ("FVG retest hold", "retest_hold"),
        ("FVG full fill", "full_fill"),
        ("Directional IFVG created", "ifvg_created"),
        ("Recent IFVG created", "recent_ifvg_created"),
        ("Recent IFVG respected", "recent_ifvg_respected"),
        ("Recent IFVG disrespected", "recent_ifvg_disrespected"),
        ("Core + FVG", "core_plus_fvg"),
        ("Core + FVG retest", "core_plus_fvg_retest"),
        ("FVG size quartiles", "fvg_size_quartiles"),
        ("Distance to active FVG quartiles", "distance_quartiles"),
    )

    for title, key in sections:
        lines += [
            f"## {title}",
            "",
            table(result[key]),
            "",
        ]

    lines += ["## Setup-family diagnostics", ""]

    for family, data in result["by_family"].items():
        lines += [f"### {family}", ""]

        for name, values in data.items():
            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += ["## Year diagnostics", ""]

    for year, data in result["by_year"].items():
        lines += [f"### {year}", ""]

        for name, values in data.items():
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
        "- FVG time-to-retest is not reported because a reliable FVG-creation timestamp is not persisted in the inspected feature contract.",
        "- Current-row FVG creation and broader active/recent FVG context answer different questions.",
        "- Small IFVG and retest cells must remain exploratory.",
        "- No score or entry logic changes are authorized.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
