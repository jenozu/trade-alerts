"""EXP-009 — Displacement diagnostics.

Uses existing baseline trade ledgers and scored feature artifacts only.
Diagnostic only: no strategy rules are changed.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class DisplacementResearchError(RuntimeError):
    pass


REQUIRED_FEATURES = {
    "timestamp",
    "bullish_displacement",
    "bearish_displacement",
    "displacement_any",
    "displacement_direction",
    "displacement_score",
    "displacement_category",
    "displacement_atr",
    "displacement_body",
    "displacement_range",
    "displacement_body_atr_ratio",
    "displacement_range_atr_ratio",
    "displacement_close_location",
    "displacement_rvol",
    "bullish_structure_break",
    "bearish_structure_break",
    "bullish_mss",
    "bearish_mss",
    "bullish_choch",
    "bearish_choch",
    "bullish_bos",
    "bearish_bos",
    "bullish_fvg_created",
    "bearish_fvg_created",
}


def _truthy(v: Any) -> bool:
    if v is None or pd.isna(v):
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _segment(df: pd.DataFrame, column: str):
    if column not in df.columns:
        return {}

    s = df[column].where(df[column].notna(), "<missing>").astype(str)

    return {
        value: _metrics(df.loc[s == value])
        for value in sorted(s.unique())
    }


def enrich_displacement_context(
    ledger: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    validate_ledger(ledger)

    missing = REQUIRED_FEATURES - set(features.columns)
    if missing:
        raise DisplacementResearchError(
            f"Missing EXP-009 feature columns: {sorted(missing)}"
        )

    f = features.copy()
    f["timestamp"] = pd.to_datetime(
        f["timestamp"], utc=True, errors="coerce"
    )

    f = (
        f.dropna(subset=["timestamp"])
        .sort_values("timestamp", kind="stable")
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
        record = trade.to_dict()

        ts = trade["signal_time"]
        record["feature_matched"] = False

        if pd.isna(ts) or ts not in lookup.index:
            records.append(record)
            continue

        row = f.iloc[int(lookup.loc[ts])]
        record["feature_matched"] = True

        direction = str(trade["direction"])
        long_side = direction == "long"

        dir_disp_col = (
            "bullish_displacement"
            if long_side
            else "bearish_displacement"
        )
        opposite_disp_col = (
            "bearish_displacement"
            if long_side
            else "bullish_displacement"
        )

        record["directional_displacement"] = _truthy(
            row.get(dir_disp_col)
        )
        record["opposite_displacement"] = _truthy(
            row.get(opposite_disp_col)
        )
        record["displacement_any_exact"] = _truthy(
            row.get("displacement_any")
        )

        direction_value = row.get("displacement_direction")
        record["displacement_direction_exact"] = (
            None
            if direction_value is None or pd.isna(direction_value)
            else str(direction_value)
        )

        category = row.get("displacement_category")
        record["displacement_category_exact"] = (
            None
            if category is None or pd.isna(category)
            else str(category)
        )

        numeric_cols = [
            "displacement_score",
            "displacement_atr",
            "displacement_body",
            "displacement_range",
            "displacement_body_atr_ratio",
            "displacement_range_atr_ratio",
            "displacement_close_location",
            "displacement_rvol",
        ]

        for col in numeric_cols:
            record[col] = _safe_float(row.get(col))

        if long_side:
            record["structure_break_same_direction"] = _truthy(
                row.get("bullish_structure_break")
            )
            record["mss_same_direction"] = _truthy(
                row.get("bullish_mss")
            )
            record["choch_same_direction"] = _truthy(
                row.get("bullish_choch")
            )
            record["bos_same_direction"] = _truthy(
                row.get("bullish_bos")
            )
            record["fvg_same_direction"] = _truthy(
                row.get("bullish_fvg_created")
            )
        else:
            record["structure_break_same_direction"] = _truthy(
                row.get("bearish_structure_break")
            )
            record["mss_same_direction"] = _truthy(
                row.get("bearish_mss")
            )
            record["choch_same_direction"] = _truthy(
                row.get("bearish_choch")
            )
            record["bos_same_direction"] = _truthy(
                row.get("bearish_bos")
            )
            record["fvg_same_direction"] = _truthy(
                row.get("bearish_fvg_created")
            )

        records.append(record)

    return pd.DataFrame(records)


def _quartile_segment(df: pd.DataFrame, column: str):
    s = pd.to_numeric(df[column], errors="coerce")

    if s.notna().sum() < 20:
        return {}

    tmp = df.loc[s.notna()].copy()

    try:
        tmp["_bucket"] = pd.qcut(
            pd.to_numeric(tmp[column], errors="coerce"),
            4,
            duplicates="drop",
        ).astype(str)
    except ValueError:
        return {}

    return _segment(tmp, "_bucket")


def analyze_displacement(
    year_frames: dict[int, pd.DataFrame],
):
    if set(year_frames) != {2023, 2024, 2025}:
        raise DisplacementResearchError(
            "EXP-009 requires exactly 2023, 2024, 2025"
        )

    frames = []

    for year, frame in sorted(year_frames.items()):
        f = frame.copy()
        f["year"] = year
        frames.append(f)

    df = pd.concat(frames, ignore_index=True)

    result = {
        "experiment_id": "EXP-009_displacement",
        "coverage": {
            "total_trades": int(len(df)),
            "feature_matched": int(df["feature_matched"].sum()),
        },
        "overall": _metrics(df),
        "directional_displacement": _segment(
            df, "directional_displacement"
        ),
        "opposite_displacement": _segment(
            df, "opposite_displacement"
        ),
        "category": _segment(
            df, "displacement_category_exact"
        ),
        "direction": _segment(
            df, "displacement_direction_exact"
        ),
        "structure_break": _segment(
            df, "structure_break_same_direction"
        ),
        "mss": _segment(
            df, "mss_same_direction"
        ),
        "choch": _segment(
            df, "choch_same_direction"
        ),
        "bos": _segment(
            df, "bos_same_direction"
        ),
        "fvg": _segment(
            df, "fvg_same_direction"
        ),
        "by_year": {},
        "by_trade_direction": {},
        "by_setup_family": {},
        "by_score_band": {},
        "numeric": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]
        result["by_year"][str(year)] = {
            "overall": _metrics(y),
            "directional_displacement": _segment(
                y, "directional_displacement"
            ),
            "category": _segment(
                y, "displacement_category_exact"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]
        result["by_trade_direction"][direction] = {
            "overall": _metrics(g),
            "directional_displacement": _segment(
                g, "directional_displacement"
            ),
            "category": _segment(
                g, "displacement_category_exact"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]
        result["by_setup_family"][family] = {
            "overall": _metrics(g),
            "directional_displacement": _segment(
                g, "directional_displacement"
            ),
            "category": _segment(
                g, "displacement_category_exact"
            ),
        }

    for band in sorted(df["score_band"].dropna().unique()):
        g = df[df["score_band"] == band]
        result["by_score_band"][band] = {
            "overall": _metrics(g),
            "directional_displacement": _segment(
                g, "directional_displacement"
            ),
        }

    numeric_cols = [
        "displacement_score",
        "displacement_body_atr_ratio",
        "displacement_range_atr_ratio",
        "displacement_close_location",
        "displacement_rvol",
        "displacement_body",
        "displacement_range",
    ]

    displaced = df[df["directional_displacement"]].copy()

    for col in numeric_cols:
        result["numeric"][col] = _quartile_segment(
            displaced,
            col,
        )

    # Combination diagnostics among directionally aligned displacement.
    combos = displaced.copy()

    combos["disp_plus_structure_break"] = (
        combos["structure_break_same_direction"]
    )
    combos["disp_plus_mss"] = combos["mss_same_direction"]
    combos["disp_plus_choch"] = combos["choch_same_direction"]
    combos["disp_plus_bos"] = combos["bos_same_direction"]
    combos["disp_plus_fvg"] = combos["fvg_same_direction"]

    result["combinations"] = {
        col: _segment(combos, col)
        for col in (
            "disp_plus_structure_break",
            "disp_plus_mss",
            "disp_plus_choch",
            "disp_plus_bos",
            "disp_plus_fvg",
        )
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
        "directional_displacement",
        "opposite_displacement",
        "category",
        "direction",
        "structure_break",
        "mss",
        "choch",
        "bos",
        "fvg",
    ):
        add(section, result.get(section, {}))

    for year, sections in result["by_year"].items():
        for section, values in sections.items():
            if section != "overall":
                add(f"year_{year}_{section}", values)

    for direction, sections in result["by_trade_direction"].items():
        for section, values in sections.items():
            if section != "overall":
                add(f"direction_{direction}_{section}", values)

    for family, sections in result["by_setup_family"].items():
        for section, values in sections.items():
            if section != "overall":
                add(f"family_{family}_{section}", values)

    for col, values in result["numeric"].items():
        add(f"quartile_{col}", values)

    for col, values in result["combinations"].items():
        add(col, values)

    return pd.DataFrame(rows)


def markdown_report(result):
    def num(v, d=2):
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
        "# EXP-009 — Displacement",
        "",
        "Diagnostic only. Existing baseline trades/features only.",
        "",
        "## Coverage",
        "",
        (
            f"- Feature matched: "
            f"{result['coverage']['feature_matched']} / "
            f"{result['coverage']['total_trades']}"
        ),
        "",
    ]

    sections = [
        ("Directional displacement present / absent",
         "directional_displacement"),
        ("Opposite displacement", "opposite_displacement"),
        ("Displacement category", "category"),
        ("Displacement direction", "direction"),
        ("Same-direction structure break", "structure_break"),
        ("Same-direction MSS", "mss"),
        ("Same-direction CHOCH", "choch"),
        ("Same-direction BOS", "bos"),
        ("Same-direction FVG creation", "fvg"),
    ]

    for title, key in sections:
        lines += [
            f"## {title}",
            "",
            table(result.get(key, {})),
            "",
        ]

    lines += ["## Year-by-year displacement", ""]

    for year, sections in result["by_year"].items():
        lines += [
            f"### {year}",
            "",
            table(sections["directional_displacement"]),
            "",
        ]

    lines += ["## Long vs short", ""]

    for direction, sections in result["by_trade_direction"].items():
        lines += [
            f"### {direction}",
            "",
            table(sections["directional_displacement"]),
            "",
        ]

    lines += ["## Reversal vs continuation", ""]

    for family, sections in result["by_setup_family"].items():
        lines += [
            f"### {family}",
            "",
            table(sections["directional_displacement"]),
            "",
        ]

    lines += ["## Numeric displacement diagnostics", ""]

    for col, values in result["numeric"].items():
        lines += [
            f"### {col}",
            "",
            table(values),
            "",
        ]

    lines += ["## Displacement + confirmation interaction", ""]

    for col, values in result["combinations"].items():
        lines += [
            f"### {col}",
            "",
            table(values),
            "",
        ]

    lines += [
        "## Limitations",
        "",
        "- EXP-009 analyzes surviving baseline trades; it does not simulate alternative displacement thresholds.",
        "- Quartiles describe observed associations and are not proposed production cutoffs.",
        "- Feature co-occurrence does not prove independent causal lift.",
        "- MSS/CHOCH/BOS overlap will be examined more directly in EXP-010.",
        "- FVG interaction receives dedicated analysis in EXP-011.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
