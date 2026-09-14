"""EXP-017 — VWAP diagnostics from archived baseline trades/features."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class VWAPResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "vwap",
    "vwap_distance_points",
    "vwap_distance_pct",
    "vwap_position",
    "vwap_bullish_cross",
    "vwap_bearish_cross",
    "vwap_slope_points_per_bar",
    "vwap_slope_direction",
}


def safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def norm(v: Any):
    if v is None or pd.isna(v):
        return None
    return str(v).strip().lower()


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


def directional_position(trade_direction, position, distance):
    p = norm(position)

    if p in {"above", "above_vwap", "premium"}:
        side = "above"
    elif p in {"below", "below_vwap", "discount"}:
        side = "below"
    else:
        # Only use numeric sign as fallback.
        if distance is None:
            return "unknown"
        if distance > 0:
            side = "above"
        elif distance < 0:
            side = "below"
        else:
            return "at_vwap"

    if trade_direction == "long":
        return "with_side" if side == "above" else "against_side"

    return "with_side" if side == "below" else "against_side"


def directional_slope_alignment(trade_direction, slope_direction, slope_value):
    s = norm(slope_direction)

    if s in {"bullish", "up", "rising", "positive"}:
        slope_side = "bullish"
    elif s in {"bearish", "down", "falling", "negative"}:
        slope_side = "bearish"
    else:
        if slope_value is None:
            return "neutral/unknown"
        if slope_value > 0:
            slope_side = "bullish"
        elif slope_value < 0:
            slope_side = "bearish"
        else:
            return "neutral/unknown"

    if trade_direction == "long":
        return "aligned" if slope_side == "bullish" else "opposed"

    return "aligned" if slope_side == "bearish" else "opposed"


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise VWAPResearchError(
            f"Missing EXP-017 columns: {sorted(missing)}"
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

        distance = safe_float(
            row.get("vwap_distance_points")
        )

        distance_pct = safe_float(
            row.get("vwap_distance_pct")
        )

        slope = safe_float(
            row.get("vwap_slope_points_per_bar")
        )

        r["vwap_distance_points_exp017"] = distance
        r["vwap_abs_distance_points_exp017"] = (
            abs(distance)
            if distance is not None
            else None
        )

        r["vwap_distance_pct_exp017"] = distance_pct
        r["vwap_abs_distance_pct_exp017"] = (
            abs(distance_pct)
            if distance_pct is not None
            else None
        )

        r["vwap_position_exact"] = norm(
            row.get("vwap_position")
        )

        r["vwap_directional_position"] = directional_position(
            direction,
            row.get("vwap_position"),
            distance,
        )

        r["vwap_slope_exp017"] = slope

        r["vwap_slope_direction_exact"] = norm(
            row.get("vwap_slope_direction")
        )

        r["vwap_slope_alignment"] = directional_slope_alignment(
            direction,
            row.get("vwap_slope_direction"),
            slope,
        )

        bullish_cross = truthy(
            row.get("vwap_bullish_cross")
        )

        bearish_cross = truthy(
            row.get("vwap_bearish_cross")
        )

        r["vwap_bullish_cross_exp017"] = bullish_cross
        r["vwap_bearish_cross_exp017"] = bearish_cross

        if direction == "long":
            r["directional_vwap_cross"] = bullish_cross
            r["opposite_vwap_cross"] = bearish_cross
        else:
            r["directional_vwap_cross"] = bearish_cross
            r["opposite_vwap_cross"] = bullish_cross

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise VWAPResearchError(
            "EXP-017 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-017_vwap",

        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },

        "position": segment(
            df,
            "vwap_position_exact",
        ),

        "directional_position": segment(
            df,
            "vwap_directional_position",
        ),

        "directional_cross": segment(
            df,
            "directional_vwap_cross",
        ),

        "opposite_cross": segment(
            df,
            "opposite_vwap_cross",
        ),

        "slope_direction": segment(
            df,
            "vwap_slope_direction_exact",
        ),

        "slope_alignment": segment(
            df,
            "vwap_slope_alignment",
        ),

        "signed_distance_quartiles": quartiles(
            df,
            "vwap_distance_points_exp017",
        ),

        "absolute_distance_quartiles": quartiles(
            df,
            "vwap_abs_distance_points_exp017",
        ),

        "absolute_distance_pct_quartiles": quartiles(
            df,
            "vwap_abs_distance_pct_exp017",
        ),

        "slope_quartiles": quartiles(
            df,
            "vwap_slope_exp017",
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "directional_position": segment(
                g,
                "vwap_directional_position",
            ),
            "slope_alignment": segment(
                g,
                "vwap_slope_alignment",
            ),
            "directional_cross": segment(
                g,
                "directional_vwap_cross",
            ),
            "absolute_distance": quartiles(
                g,
                "vwap_abs_distance_points_exp017",
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "position": segment(
                g,
                "vwap_position_exact",
            ),
            "slope_alignment": segment(
                g,
                "vwap_slope_alignment",
            ),
            "directional_cross": segment(
                g,
                "directional_vwap_cross",
            ),
            "absolute_distance": quartiles(
                g,
                "vwap_abs_distance_points_exp017",
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "directional_position": segment(
                g,
                "vwap_directional_position",
            ),
            "slope_alignment": segment(
                g,
                "vwap_slope_alignment",
            ),
            "directional_cross": segment(
                g,
                "directional_vwap_cross",
            ),
            "absolute_distance": quartiles(
                g,
                "vwap_abs_distance_points_exp017",
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
        "position",
        "directional_position",
        "directional_cross",
        "opposite_cross",
        "slope_direction",
        "slope_alignment",
        "signed_distance_quartiles",
        "absolute_distance_quartiles",
        "absolute_distance_pct_quartiles",
        "slope_quartiles",
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
        "# EXP-017 — VWAP",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        ("Persisted VWAP position", "position"),
        (
            "Trade direction relative to VWAP side",
            "directional_position",
        ),
        (
            "Same-direction VWAP cross at signal",
            "directional_cross",
        ),
        (
            "Opposite-direction VWAP cross at signal",
            "opposite_cross",
        ),
        (
            "VWAP slope direction",
            "slope_direction",
        ),
        (
            "Trade alignment with VWAP slope",
            "slope_alignment",
        ),
        (
            "Signed distance from VWAP quartiles",
            "signed_distance_quartiles",
        ),
        (
            "Absolute distance from VWAP quartiles",
            "absolute_distance_quartiles",
        ),
        (
            "Absolute percent distance from VWAP quartiles",
            "absolute_distance_pct_quartiles",
        ),
        (
            "VWAP slope quartiles",
            "slope_quartiles",
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
        "- Existing baseline trades only.",
        "- VWAP cross fields are signal-time observations, not simulated delayed-entry rules.",
        "- VWAP reclaim/rejection is not invented because no explicit persisted reclaim/rejection field exists.",
        "- Position and distance may overlap mathematically and should not be assumed independent.",
        "- No scoring, entry, stop, or target change is authorized.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
