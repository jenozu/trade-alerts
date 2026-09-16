"""EXP-021 — Execution / confirmation timeframe diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class ExecutionConfirmationResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "bullish_structure_close_break",
    "bearish_structure_close_break",
    "bullish_structure_wick_break",
    "bearish_structure_wick_break",
    "structure_break_confirmation",
    "structure_break_timestamp",
    "structure_break_available_at",
    "bullish_structure_reclaim_event",
    "bearish_structure_reclaim_event",
    "bullish_fvg_first_touch",
    "bearish_fvg_first_touch",
    "bullish_fvg_retest_hold",
    "bearish_fvg_retest_hold",
    "bullish_reversal_entry_valid_event",
    "bearish_reversal_entry_valid_event",
    "bullish_continuation_entry_valid_event",
    "bearish_continuation_entry_valid_event",
    "bullish_entry_valid_event",
    "bearish_entry_valid_event",
    "entry_valid_direction",
}


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
    s = df[col].where(df[col].notna(), "<missing>").astype(str)
    return {
        value: _metrics(df.loc[s == value])
        for value in s.drop_duplicates().tolist()
    }


def break_mode(close_break, wick_break):
    if close_break and wick_break:
        return "close_and_wick"
    if close_break:
        return "close_only"
    if wick_break:
        return "wick_only"
    return "neither"


def fvg_state(first_touch, retest_hold):
    if first_touch and retest_hold:
        return "first_touch_and_hold"
    if retest_hold:
        return "retest_hold"
    if first_touch:
        return "first_touch_only"
    return "neither"


def delay_bucket(v):
    if v is None or pd.isna(v):
        return "unknown"
    x = float(v)
    if x <= 0:
        return "<=0m"
    if x <= 1:
        return "0-1m"
    if x <= 2:
        return "1-2m"
    if x <= 5:
        return "2-5m"
    return "5m+"


def enrich(ledger, features):
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise ExecutionConfirmationResearchError(
            f"Missing EXP-021 fields: {sorted(missing)}"
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

    out["direction"] = (
        out["direction"].astype(str).str.lower()
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
            close_break = truthy(row.get("bullish_structure_close_break"))
            wick_break = truthy(row.get("bullish_structure_wick_break"))
            reclaim = truthy(row.get("bullish_structure_reclaim_event"))
            first_touch = truthy(row.get("bullish_fvg_first_touch"))
            retest_hold = truthy(row.get("bullish_fvg_retest_hold"))
            reversal_valid = truthy(
                row.get("bullish_reversal_entry_valid_event")
            )
            continuation_valid = truthy(
                row.get("bullish_continuation_entry_valid_event")
            )
            entry_valid = truthy(
                row.get("bullish_entry_valid_event")
            )
        else:
            close_break = truthy(row.get("bearish_structure_close_break"))
            wick_break = truthy(row.get("bearish_structure_wick_break"))
            reclaim = truthy(row.get("bearish_structure_reclaim_event"))
            first_touch = truthy(row.get("bearish_fvg_first_touch"))
            retest_hold = truthy(row.get("bearish_fvg_retest_hold"))
            reversal_valid = truthy(
                row.get("bearish_reversal_entry_valid_event")
            )
            continuation_valid = truthy(
                row.get("bearish_continuation_entry_valid_event")
            )
            entry_valid = truthy(
                row.get("bearish_entry_valid_event")
            )

        r["close_break"] = close_break
        r["wick_break"] = wick_break
        r["break_mode"] = break_mode(close_break, wick_break)

        confirmation = row.get("structure_break_confirmation")
        r["structure_break_confirmation_exp021"] = (
            "none"
            if confirmation is None or pd.isna(confirmation)
            else str(confirmation)
        )

        break_ts = pd.to_datetime(
            row.get("structure_break_timestamp"),
            utc=True,
            errors="coerce",
        )

        available_ts = pd.to_datetime(
            row.get("structure_break_available_at"),
            utc=True,
            errors="coerce",
        )

        if pd.notna(break_ts) and pd.notna(available_ts):
            delay = (
                available_ts - break_ts
            ).total_seconds() / 60.0
        else:
            delay = np.nan

        r["confirmation_delay_minutes"] = delay
        r["confirmation_delay_bucket"] = delay_bucket(delay)

        r["reclaim_event"] = reclaim
        r["fvg_first_touch"] = first_touch
        r["fvg_retest_hold"] = retest_hold
        r["fvg_confirmation_state"] = fvg_state(
            first_touch, retest_hold
        )

        r["directional_entry_valid"] = entry_valid
        r["reversal_entry_valid"] = reversal_valid
        r["continuation_entry_valid"] = continuation_valid

        if reversal_valid and continuation_valid:
            r["entry_valid_family"] = "both"
        elif reversal_valid:
            r["entry_valid_family"] = "reversal"
        elif continuation_valid:
            r["entry_valid_family"] = "continuation"
        else:
            r["entry_valid_family"] = "neither"

        r["entry_valid_direction_exp021"] = str(
            row.get("entry_valid_direction")
        )

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise ExecutionConfirmationResearchError(
            "EXP-021 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-021_execution-confirmation",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "break_mode": segment(df, "break_mode"),
        "confirmation_type": segment(
            df, "structure_break_confirmation_exp021"
        ),
        "confirmation_delay": segment(
            df, "confirmation_delay_bucket"
        ),
        "reclaim": segment(df, "reclaim_event"),
        "fvg_state": segment(df, "fvg_confirmation_state"),
        "entry_valid": segment(df, "directional_entry_valid"),
        "entry_valid_family": segment(df, "entry_valid_family"),
        "by_year": {},
        "by_direction": {},
        "by_family": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "break_mode": segment(g, "break_mode"),
            "confirmation_type": segment(
                g, "structure_break_confirmation_exp021"
            ),
            "confirmation_delay": segment(
                g, "confirmation_delay_bucket"
            ),
            "reclaim": segment(g, "reclaim_event"),
            "fvg_state": segment(
                g, "fvg_confirmation_state"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "break_mode": segment(g, "break_mode"),
            "confirmation_type": segment(
                g, "structure_break_confirmation_exp021"
            ),
            "confirmation_delay": segment(
                g, "confirmation_delay_bucket"
            ),
            "reclaim": segment(g, "reclaim_event"),
            "fvg_state": segment(
                g, "fvg_confirmation_state"
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "break_mode": segment(g, "break_mode"),
            "confirmation_type": segment(
                g, "structure_break_confirmation_exp021"
            ),
            "confirmation_delay": segment(
                g, "confirmation_delay_bucket"
            ),
            "reclaim": segment(g, "reclaim_event"),
            "fvg_state": segment(
                g, "fvg_confirmation_state"
            ),
            "entry_valid_family": segment(
                g, "entry_valid_family"
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
        "break_mode",
        "confirmation_type",
        "confirmation_delay",
        "reclaim",
        "fvg_state",
        "entry_valid",
        "entry_valid_family",
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
            return f"{float(v):.{digits}f}"
        except Exception:
            return "—"

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
        "# EXP-021 — Execution / Confirmation Timeframe",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: "
        f"{result['coverage']['matched']} / "
        f"{result['coverage']['total']}",
        "",
        "## Break mode",
        "",
        table(result["break_mode"]),
        "",
        "## Structure-break confirmation type",
        "",
        table(result["confirmation_type"]),
        "",
        "## Confirmation availability delay",
        "",
        table(result["confirmation_delay"]),
        "",
        "## Structure reclaim",
        "",
        table(result["reclaim"]),
        "",
        "## FVG first-touch / retest-hold state",
        "",
        table(result["fvg_state"]),
        "",
        "## Directional entry-valid state",
        "",
        table(result["entry_valid"]),
        "",
        "## Entry-valid family",
        "",
        table(result["entry_valid_family"]),
        "",
        "## Limitations",
        "",
        "- EXP-021 analyzes confirmation states attached to the existing baseline trades.",
        "- It does not reconstruct hypothetical alternative fills for an earlier immediate entry or a later confirmation entry.",
        "- Therefore performance differences are diagnostic associations, not counterfactual execution simulations.",
        "- Any actual change to entry timing requires a later dedicated backtest with alternate fills and identical stop/target rules.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
