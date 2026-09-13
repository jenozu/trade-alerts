"""EXP-008 breakout / acceptance diagnostics.

Uses existing baseline ledgers and scored feature artifacts only.
Diagnostic only: no strategy rules are changed.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class BreakoutAcceptanceResearchError(RuntimeError):
    pass


REQUIRED_FEATURES = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "bullish_structure_close_break",
    "bearish_structure_close_break",
    "bullish_structure_wick_break",
    "bearish_structure_wick_break",
    "structure_break_direction",
    "structure_break_confirmation",
    "structure_broken_level",
    "structure_broken_timeframe",
    "structure_break_timestamp",
    "structure_break_displacement_score",
    "structure_break_displacement_category",
    "structure_break_rvol",
}


def _truthy(v: Any) -> bool:
    if v is None or pd.isna(v):
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _safe_float(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else None
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


def enrich_continuations(
    ledger: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    validate_ledger(ledger)

    missing = REQUIRED_FEATURES - set(features.columns)
    if missing:
        raise BreakoutAcceptanceResearchError(
            f"Missing EXP-008 feature columns: {sorted(missing)}"
        )

    f = features.copy()
    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True, errors="coerce")
    f["structure_break_timestamp"] = pd.to_datetime(
        f["structure_break_timestamp"], utc=True, errors="coerce"
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

    rows = []

    for _, trade in out.iterrows():
        record = trade.to_dict()

        ts = trade["signal_time"]
        record["feature_matched"] = False

        if pd.isna(ts) or ts not in lookup.index:
            rows.append(record)
            continue

        pos = int(lookup.loc[ts])
        row = f.iloc[pos]
        record["feature_matched"] = True

        direction = str(trade["direction"])
        long_side = direction == "long"

        close_col = (
            "bullish_structure_close_break"
            if long_side
            else "bearish_structure_close_break"
        )
        wick_col = (
            "bullish_structure_wick_break"
            if long_side
            else "bearish_structure_wick_break"
        )

        record["directional_close_break"] = _truthy(row.get(close_col))
        record["directional_wick_break"] = _truthy(row.get(wick_col))

        record["break_confirmation"] = (
            None
            if pd.isna(row.get("structure_break_confirmation"))
            else str(row.get("structure_break_confirmation"))
        )

        record["broken_timeframe"] = (
            None
            if pd.isna(row.get("structure_broken_timeframe"))
            else str(row.get("structure_broken_timeframe"))
        )

        record["break_displacement_category"] = (
            None
            if pd.isna(row.get("structure_break_displacement_category"))
            else str(row.get("structure_break_displacement_category"))
        )

        record["break_displacement_score"] = _safe_float(
            row.get("structure_break_displacement_score")
        )
        record["break_rvol"] = _safe_float(row.get("structure_break_rvol"))
        record["broken_level"] = _safe_float(row.get("structure_broken_level"))

        break_ts = row.get("structure_break_timestamp")
        record["break_timestamp"] = break_ts

        if pd.notna(break_ts):
            delay = (ts - break_ts).total_seconds() / 60.0
            record["minutes_since_break"] = max(0.0, delay)
        else:
            record["minutes_since_break"] = None

        record["retest_present"] = False
        record["retest_hold"] = False
        record["pre_entry_follow_through_points"] = None
        record["completed_5m_close_beyond"] = False

        level = record["broken_level"]

        if level is not None and pd.notna(break_ts):
            seq = f[
                (f["timestamp"] >= break_ts)
                & (f["timestamp"] <= ts)
            ].copy()

            if not seq.empty:
                if long_side:
                    follow = pd.to_numeric(
                        seq["high"], errors="coerce"
                    ).max() - level
                else:
                    follow = level - pd.to_numeric(
                        seq["low"], errors="coerce"
                    ).min()

                if pd.notna(follow):
                    record["pre_entry_follow_through_points"] = max(
                        0.0, float(follow)
                    )

                after_break = seq[seq["timestamp"] > break_ts]

                if not after_break.empty:
                    if long_side:
                        touches = after_break[
                            pd.to_numeric(
                                after_break["low"], errors="coerce"
                            ) <= level
                        ]
                    else:
                        touches = after_break[
                            pd.to_numeric(
                                after_break["high"], errors="coerce"
                            ) >= level
                        ]

                    record["retest_present"] = not touches.empty

                    if not touches.empty:
                        first_touch_ts = touches.iloc[0]["timestamp"]
                        after_touch = after_break[
                            after_break["timestamp"] >= first_touch_ts
                        ]

                        closes = pd.to_numeric(
                            after_touch["close"], errors="coerce"
                        )

                        if long_side:
                            record["retest_hold"] = bool(
                                (closes >= level).all()
                            )
                        else:
                            record["retest_hold"] = bool(
                                (closes <= level).all()
                            )

                # Deterministic 5-minute confirmation:
                # only completed 5m bars ending no later than signal time.
                tmp = seq.set_index("timestamp")[["close"]].copy()
                five = tmp.resample(
                    "5min", label="right", closed="right"
                ).last().dropna()

                five = five[five.index <= ts]

                if not five.empty:
                    closes5 = pd.to_numeric(
                        five["close"], errors="coerce"
                    )

                    if long_side:
                        record["completed_5m_close_beyond"] = bool(
                            (closes5 > level).any()
                        )
                    else:
                        record["completed_5m_close_beyond"] = bool(
                            (closes5 < level).any()
                        )

        rows.append(record)

    return pd.DataFrame(rows)


def analyze_exp008(year_frames: dict[int, pd.DataFrame]):
    if set(year_frames) != {2023, 2024, 2025}:
        raise BreakoutAcceptanceResearchError(
            "EXP-008 requires 2023, 2024, and 2025"
        )

    frames = []

    for year, frame in sorted(year_frames.items()):
        f = frame.copy()
        f["year"] = year
        frames.append(f)

    all_trades = pd.concat(frames, ignore_index=True)

    # EXP-008 specifically studies Break -> Retest -> Continuation.
    df = all_trades[
        all_trades["setup_family"] == "continuation"
    ].copy()

    result = {
        "experiment_id": "EXP-008_breakout-acceptance",
        "coverage": {
            "all_baseline_trades": int(len(all_trades)),
            "continuation_trades": int(len(df)),
            "feature_matched": int(df["feature_matched"].sum()),
        },
        "overall_continuation": _metrics(df),
        "close_break": _segment(df, "directional_close_break"),
        "wick_break": _segment(df, "directional_wick_break"),
        "break_confirmation": _segment(df, "break_confirmation"),
        "five_minute_close": _segment(
            df, "completed_5m_close_beyond"
        ),
        "retest_present": _segment(df, "retest_present"),
        "retest_hold": _segment(df, "retest_hold"),
        "displacement_category": _segment(
            df, "break_displacement_category"
        ),
        "broken_timeframe": _segment(df, "broken_timeframe"),
        "by_year": {},
        "by_direction": {},
        "by_score_band": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "overall": _metrics(y),
            "close_break": _segment(
                y, "directional_close_break"
            ),
            "five_minute_close": _segment(
                y, "completed_5m_close_beyond"
            ),
            "retest_hold": _segment(y, "retest_hold"),
        }

    for direction in ("long", "short"):
        d = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "overall": _metrics(d),
            "close_break": _segment(
                d, "directional_close_break"
            ),
            "five_minute_close": _segment(
                d, "completed_5m_close_beyond"
            ),
            "retest_hold": _segment(d, "retest_hold"),
        }

    for band in sorted(df["score_band"].dropna().unique()):
        b = df[df["score_band"] == band]

        result["by_score_band"][band] = {
            "overall": _metrics(b),
            "close_break": _segment(
                b, "directional_close_break"
            ),
            "retest_hold": _segment(b, "retest_hold"),
        }

    # Numeric buckets
    for col, key in [
        ("minutes_since_break", "break_delay_quartiles"),
        (
            "pre_entry_follow_through_points",
            "follow_through_quartiles",
        ),
        ("break_displacement_score", "displacement_score_quartiles"),
        ("break_rvol", "break_rvol_quartiles"),
    ]:
        s = pd.to_numeric(df[col], errors="coerce")

        if s.notna().sum() >= 20:
            try:
                tmp = df.copy()
                tmp["_bucket"] = pd.qcut(
                    s, 4, duplicates="drop"
                ).astype(str)
                result[key] = _segment(tmp, "_bucket")
            except ValueError:
                result[key] = {}
        else:
            result[key] = {}

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
        "close_break",
        "wick_break",
        "break_confirmation",
        "five_minute_close",
        "retest_present",
        "retest_hold",
        "displacement_category",
        "broken_timeframe",
        "break_delay_quartiles",
        "follow_through_quartiles",
        "displacement_score_quartiles",
        "break_rvol_quartiles",
    ):
        add(section, result.get(section, {}))

    for year, sections in result["by_year"].items():
        for section, values in sections.items():
            if section != "overall":
                add(f"year_{year}_{section}", values)

    for direction, sections in result["by_direction"].items():
        for section, values in sections.items():
            if section != "overall":
                add(f"{direction}_{section}", values)

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
        "# EXP-008 — Breakout / Acceptance Quality",
        "",
        "Diagnostic analysis of existing continuation trades only.",
        "",
        "## Coverage",
        "",
        f"- Baseline trades: {result['coverage']['all_baseline_trades']}",
        f"- Continuation trades: {result['coverage']['continuation_trades']}",
        f"- Feature matched: {result['coverage']['feature_matched']}",
        "",
    ]

    sections = [
        ("Directional 1m close break", "close_break"),
        ("Directional wick break", "wick_break"),
        ("Stored break confirmation", "break_confirmation"),
        ("Completed 5m close beyond broken level", "five_minute_close"),
        ("Retest present before signal", "retest_present"),
        ("Retest hold before signal", "retest_hold"),
        ("Break displacement category", "displacement_category"),
        ("Broken structure timeframe", "broken_timeframe"),
        ("Break-to-signal delay quartiles", "break_delay_quartiles"),
        (
            "Pre-entry follow-through quartiles",
            "follow_through_quartiles",
        ),
        (
            "Break displacement-score quartiles",
            "displacement_score_quartiles",
        ),
        ("Break RVOL quartiles", "break_rvol_quartiles"),
    ]

    for title, key in sections:
        lines += [
            f"## {title}",
            "",
            table(result.get(key, {})),
            "",
        ]

    lines += ["## Year diagnostics", ""]

    for year, sections in result["by_year"].items():
        lines += [
            f"### {year}",
            "",
            "#### Close break",
            "",
            table(sections["close_break"]),
            "",
            "#### Completed 5m close",
            "",
            table(sections["five_minute_close"]),
            "",
            "#### Retest hold",
            "",
            table(sections["retest_hold"]),
            "",
        ]

    lines += [
        "## Operational definitions / limitations",
        "",
        "- EXP-008 analyzes the existing continuation subset; it does not create new trades.",
        "- `retest_present` is derived deterministically from a post-break revisit of `structure_broken_level` before signal time.",
        "- `retest_hold` requires the post-touch closes through signal time to remain on the accepted side of the broken level.",
        "- `completed_5m_close_beyond` uses only completed five-minute closes available by signal time.",
        "- These derived diagnostics are research labels, not new production entry rules.",
        "- No missed-trade opportunity cost can be measured without rerunning alternative entry logic; EXP-008 therefore does not pretend that it can.",
        "- Small cells remain exploratory.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
