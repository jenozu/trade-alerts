"""EXP-019 — Room-to-target diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class RoomToTargetResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",

    "dol_distance_points",
    "dol_primary_distance_points",
    "dol_target_category",
    "dol_primary_target_category",

    "distance_to_unswept_liquidity_above",
    "distance_to_unswept_liquidity_below",

    "long_score_room_to_target",
    "short_score_room_to_target",

    "long_score_penalty_major_obstacle",
    "short_score_penalty_major_obstacle",
}


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


def truthy(v):
    if v is None or pd.isna(v):
        return False

    if isinstance(v, (bool, np.bool_)):
        return bool(v)

    try:
        return float(v) != 0
    except (TypeError, ValueError):
        return str(v).strip().lower() in {
            "true", "yes", "y"
        }


def segment(df, col):
    if col not in df.columns:
        return {}

    s = (
        df[col]
        .where(df[col].notna(), "<missing>")
        .astype(str)
    )

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
            pd.to_numeric(
                x[col],
                errors="coerce",
            ),
            4,
            duplicates="drop",
        ).astype(str)

    except ValueError:
        return {}

    return segment(x, "_bucket")


def room_bucket(v):
    x = safe_float(v)

    if x is None:
        return "unknown"

    x = abs(x)

    if x < 25:
        return "<25"

    if x < 50:
        return "25-49"

    if x < 75:
        return "50-74"

    if x < 100:
        return "75-99"

    return "100+"


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)

    if missing:
        raise RoomToTargetResearchError(
            f"Missing EXP-019 fields: {sorted(missing)}"
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
        .drop_duplicates(
            "timestamp",
            keep="last",
        )
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

        primary = safe_float(
            row.get("dol_primary_distance_points")
        )

        if primary is None:
            primary = safe_float(
                row.get("dol_distance_points")
            )

        if primary is not None:
            primary = abs(primary)

        r["dol_room_points"] = primary
        r["dol_room_bucket"] = room_bucket(primary)

        target_category = norm(
            row.get("dol_primary_target_category")
        )

        if target_category is None:
            target_category = norm(
                row.get("dol_target_category")
            )

        r["dol_target_category_exp019"] = target_category

        if direction == "long":
            unswept = safe_float(
                row.get(
                    "distance_to_unswept_liquidity_above"
                )
            )

            score = safe_float(
                row.get("long_score_room_to_target")
            )

            obstacle = truthy(
                row.get(
                    "long_score_penalty_major_obstacle"
                )
            )

        else:
            unswept = safe_float(
                row.get(
                    "distance_to_unswept_liquidity_below"
                )
            )

            score = safe_float(
                row.get("short_score_room_to_target")
            )

            obstacle = truthy(
                row.get(
                    "short_score_penalty_major_obstacle"
                )
            )

        if unswept is not None:
            unswept = abs(unswept)

        r["unswept_room_points"] = unswept
        r["unswept_room_bucket"] = room_bucket(
            unswept
        )

        r["directional_room_score"] = score
        r["major_obstacle"] = obstacle

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):

    if set(frames) != {2023, 2024, 2025}:
        raise RoomToTargetResearchError(
            "EXP-019 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(
        joined,
        ignore_index=True,
    )

    result = {
        "experiment_id":
            "EXP-019_room-to-target",

        "coverage": {
            "total": int(len(df)),
            "matched": int(
                df["feature_matched"].sum()
            ),
        },

        "dol_room_buckets": segment(
            df,
            "dol_room_bucket",
        ),

        "unswept_room_buckets": segment(
            df,
            "unswept_room_bucket",
        ),

        "dol_room_quartiles": quartiles(
            df,
            "dol_room_points",
        ),

        "unswept_room_quartiles": quartiles(
            df,
            "unswept_room_points",
        ),

        "room_score_quartiles": quartiles(
            df,
            "directional_room_score",
        ),

        "major_obstacle": segment(
            df,
            "major_obstacle",
        ),

        "target_category": segment(
            df,
            "dol_target_category_exp019",
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(
        df["year"].unique()
    ):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "dol_room": segment(
                g,
                "dol_room_bucket",
            ),
            "unswept_room": segment(
                g,
                "unswept_room_bucket",
            ),
            "major_obstacle": segment(
                g,
                "major_obstacle",
            ),
        }

    for direction in (
        "long",
        "short",
    ):
        g = df[
            df["direction"] == direction
        ]

        result["by_direction"][direction] = {
            "dol_room": segment(
                g,
                "dol_room_bucket",
            ),
            "unswept_room": segment(
                g,
                "unswept_room_bucket",
            ),
            "major_obstacle": segment(
                g,
                "major_obstacle",
            ),
            "room_score": quartiles(
                g,
                "directional_room_score",
            ),
        }

    for family in (
        "reversal",
        "continuation",
    ):
        g = df[
            df["setup_family"] == family
        ]

        result["by_family"][family] = {
            "dol_room": segment(
                g,
                "dol_room_bucket",
            ),
            "unswept_room": segment(
                g,
                "unswept_room_bucket",
            ),
            "major_obstacle": segment(
                g,
                "major_obstacle",
            ),
            "room_score": quartiles(
                g,
                "directional_room_score",
            ),
        }

    return result, df


def metrics_frame(result):

    rows = []

    def add(section, values):

        for value, metrics in values.items():

            if (
                isinstance(metrics, dict)
                and "trades" in metrics
            ):
                rows.append({
                    "section": section,
                    "value": value,
                    **metrics,
                })

    for section in (
        "dol_room_buckets",
        "unswept_room_buckets",
        "dol_room_quartiles",
        "unswept_room_quartiles",
        "room_score_quartiles",
        "major_obstacle",
        "target_category",
    ):
        add(
            section,
            result[section],
        )

    for year, sections in (
        result["by_year"].items()
    ):
        for section, values in (
            sections.items()
        ):
            add(
                f"year_{year}_{section}",
                values,
            )

    for direction, sections in (
        result["by_direction"].items()
    ):
        for section, values in (
            sections.items()
        ):
            add(
                f"direction_{direction}_{section}",
                values,
            )

    for family, sections in (
        result["by_family"].items()
    ):
        for section, values in (
            sections.items()
        ):
            add(
                f"family_{family}_{section}",
                values,
            )

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
            "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]

        for label, m in values.items():

            lines.append(
                f"| {label} | "
                f"{m.get('trades',0)} | "
                f"{pct(m.get('win_rate'))} | "
                f"{num(m.get('expectancy_points'))} | "
                f"{num(m.get('expectancy_r'),3)} | "
                f"{num(m.get('profit_factor'))} | "
                f"{num(m.get('net_points'))} | "
                f"{pct(m.get('tp1_hit_rate'))} | "
                f"{pct(m.get('tp2_hit_rate'))} | "
                f"{pct(m.get('tp3_hit_rate'))} | "
                f"{pct(m.get('tp4_hit_rate'))} | "
                f"{pct(m.get('stop_rate'))} | "
                f"{num(m.get('avg_mfe'))} | "
                f"{num(m.get('avg_mae'))} |"
            )

        return "\n".join(lines)

    lines = [
        "# EXP-019 — Room to Target",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: "
        f"{result['coverage']['matched']} / "
        f"{result['coverage']['total']}",
        "",
    ]

    sections = (
        (
            "Distance to primary DOL target",
            "dol_room_buckets",
        ),
        (
            "Distance to nearest unswept liquidity in trade direction",
            "unswept_room_buckets",
        ),
        (
            "Primary DOL distance quartiles",
            "dol_room_quartiles",
        ),
        (
            "Unswept-liquidity distance quartiles",
            "unswept_room_quartiles",
        ),
        (
            "Persisted room-to-target score quartiles",
            "room_score_quartiles",
        ),
        (
            "Persisted major-obstacle flag",
            "major_obstacle",
        ),
        (
            "DOL target category",
            "target_category",
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

    for family, sections in (
        result["by_family"].items()
    ):

        lines += [
            f"### {family}",
            "",
        ]

        for name, values in (
            sections.items()
        ):

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

    for direction, sections in (
        result["by_direction"].items()
    ):

        lines += [
            f"### {direction}",
            "",
        ]

        for name, values in (
            sections.items()
        ):

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

    for year, sections in (
        result["by_year"].items()
    ):

        lines += [
            f"### {year}",
            "",
        ]

        for name, values in (
            sections.items()
        ):

            lines += [
                f"#### {name}",
                "",
                table(values),
                "",
            ]

    lines += [
        "## Limitations",
        "",
        "- DOL target distance and nearest-unswept-liquidity distance measure related but different concepts.",
        "- Distance is analyzed as absolute point magnitude; no new directional target-selection rule is invented.",
        "- The persisted room-to-target score already participates in historical scoring and is therefore selection-confounded.",
        "- Major-obstacle is analyzed exactly as stored; EXP-019 does not infer a new obstacle definition.",
        "- Existing baseline trades only; no hypothetical blocked trades are reconstructed.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
