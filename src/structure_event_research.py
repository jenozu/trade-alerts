"""EXP-010 — MSS / BOS / CHOCH / structure-shift diagnostics."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class StructureEventResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "bullish_mss",
    "bearish_mss",
    "bullish_choch",
    "bearish_choch",
    "bullish_bos",
    "bearish_bos",
    "recent_bullish_mss",
    "recent_bearish_mss",
    "recent_bullish_choch",
    "recent_bearish_choch",
    "recent_bullish_bos",
    "recent_bearish_bos",
    "bullish_structure_break",
    "bearish_structure_break",
    "recent_bullish_displacement",
    "recent_bearish_displacement",
}


def truthy(v: Any) -> bool:
    if v is None or pd.isna(v):
        return False
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def segment(df, col):
    s = df[col].where(df[col].notna(), "<missing>").astype(str)
    return {
        v: _metrics(df.loc[s == v])
        for v in sorted(s.unique())
    }


def enrich(ledger: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise StructureEventResearchError(
            f"Missing EXP-010 columns: {sorted(missing)}"
        )

    f = features.copy()
    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True, errors="coerce")
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

        for event in ("mss", "choch", "bos"):
            r[f"current_{event}"] = truthy(
                row.get(f"{side}_{event}")
            )
            r[f"recent_{event}"] = truthy(
                row.get(f"recent_{side}_{event}")
            )

        r["current_structure_break"] = truthy(
            row.get(f"{side}_structure_break")
        )
        r["recent_displacement"] = truthy(
            row.get(f"recent_{side}_displacement")
        )

        r["recent_any_structure"] = any(
            r[f"recent_{x}"] for x in ("mss", "choch", "bos")
        )

        r["recent_structure_count"] = sum(
            int(r[f"recent_{x}"])
            for x in ("mss", "choch", "bos")
        )

        r["mss_equals_choch"] = (
            r["recent_mss"] == r["recent_choch"]
        )

        r["sweep_plus_displacement"] = (
            truthy(trade.get("liquidity_sweep"))
            and r["recent_displacement"]
        )

        r["sweep_disp_mss"] = (
            r["sweep_plus_displacement"]
            and r["recent_mss"]
        )

        r["sweep_disp_choch"] = (
            r["sweep_plus_displacement"]
            and r["recent_choch"]
        )

        r["continuation_disp_bos"] = (
            r["setup_family"] == "continuation"
            and r["recent_displacement"]
            and r["recent_bos"]
        )

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames: dict[int, pd.DataFrame]):
    if set(frames) != {2023, 2024, 2025}:
        raise StructureEventResearchError(
            "EXP-010 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-010_structure-events",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "overall": _metrics(df),
        "current_mss": segment(df, "current_mss"),
        "current_choch": segment(df, "current_choch"),
        "current_bos": segment(df, "current_bos"),
        "recent_mss": segment(df, "recent_mss"),
        "recent_choch": segment(df, "recent_choch"),
        "recent_bos": segment(df, "recent_bos"),
        "recent_any_structure": segment(df, "recent_any_structure"),
        "structure_count": segment(df, "recent_structure_count"),
        "structure_break": segment(df, "current_structure_break"),
        "mss_equals_choch": segment(df, "mss_equals_choch"),
        "sweep_plus_displacement": segment(
            df, "sweep_plus_displacement"
        ),
        "sweep_disp_mss": segment(df, "sweep_disp_mss"),
        "sweep_disp_choch": segment(df, "sweep_disp_choch"),
        "continuation_disp_bos": segment(
            df, "continuation_disp_bos"
        ),
        "by_year": {},
        "by_family": {},
        "by_direction": {},
        "cooccurrence": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]
        result["by_year"][str(year)] = {
            "mss": segment(y, "recent_mss"),
            "choch": segment(y, "recent_choch"),
            "bos": segment(y, "recent_bos"),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]
        result["by_family"][family] = {
            "mss": segment(g, "recent_mss"),
            "choch": segment(g, "recent_choch"),
            "bos": segment(g, "recent_bos"),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]
        result["by_direction"][direction] = {
            "mss": segment(g, "recent_mss"),
            "choch": segment(g, "recent_choch"),
            "bos": segment(g, "recent_bos"),
        }

    for a, b in (
        ("recent_mss", "recent_choch"),
        ("recent_mss", "recent_bos"),
        ("recent_choch", "recent_bos"),
    ):
        av = df[a].astype(bool)
        bv = df[b].astype(bool)

        result["cooccurrence"][f"{a}__{b}"] = {
            "agreement_rate": float((av == bv).mean()),
            "both_true": int((av & bv).sum()),
            "a_only": int((av & ~bv).sum()),
            "b_only": int((~av & bv).sum()),
            "neither": int((~av & ~bv).sum()),
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
        "current_mss",
        "current_choch",
        "current_bos",
        "recent_mss",
        "recent_choch",
        "recent_bos",
        "recent_any_structure",
        "structure_count",
        "structure_break",
        "sweep_plus_displacement",
        "sweep_disp_mss",
        "sweep_disp_choch",
        "continuation_disp_bos",
    ):
        add(section, result[section])

    for year, values in result["by_year"].items():
        for event, metrics in values.items():
            add(f"year_{year}_{event}", metrics)

    for family, values in result["by_family"].items():
        for event, metrics in values.items():
            add(f"family_{family}_{event}", metrics)

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
        "# EXP-010 — MSS / BOS / CHOCH / Structure Shift",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    for title, key in (
        ("Recent MSS", "recent_mss"),
        ("Recent CHOCH", "recent_choch"),
        ("Recent BOS", "recent_bos"),
        ("Any recent structure confirmation", "recent_any_structure"),
        ("Recent structure confirmation count", "structure_count"),
        ("Current same-direction structure break", "structure_break"),
        ("Sweep + displacement", "sweep_plus_displacement"),
        ("Sweep + displacement + MSS", "sweep_disp_mss"),
        ("Sweep + displacement + CHOCH", "sweep_disp_choch"),
        ("Continuation + displacement + BOS", "continuation_disp_bos"),
    ):
        lines += [
            f"## {title}",
            "",
            table(result[key]),
            "",
        ]

    lines += ["## Setup-family diagnostics", ""]

    for family, events in result["by_family"].items():
        lines += [f"### {family}", ""]

        for event, values in events.items():
            lines += [
                f"#### {event.upper()}",
                "",
                table(values),
                "",
            ]

    lines += ["## Year diagnostics", ""]

    for year, events in result["by_year"].items():
        lines += [f"### {year}", ""]

        for event, values in events.items():
            lines += [
                f"#### {event.upper()}",
                "",
                table(values),
                "",
            ]

    lines += ["## Redundancy / co-occurrence", ""]

    for pair, stats in result["cooccurrence"].items():
        lines += [
            f"### {pair}",
            "",
            f"- Agreement: {100*stats['agreement_rate']:.1f}%",
            f"- Both true: {stats['both_true']}",
            f"- First only: {stats['a_only']}",
            f"- Second only: {stats['b_only']}",
            f"- Neither: {stats['neither']}",
            "",
        ]

    lines += [
        "## Limitations",
        "",
        "- This is observational baseline decomposition only.",
        "- It does not simulate waiting for a later structure event.",
        "- Entry-price opportunity cost therefore cannot be measured here.",
        "- MSS/CHOCH/BOS may share underlying structure state and must not be assumed independent.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
