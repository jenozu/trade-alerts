"""EXP-013 — Premium / Discount diagnostics."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class PremiumDiscountResearchError(RuntimeError):
    pass


REQUIRED = {
    "timestamp",
    "internal_premium_discount",
    "external_premium_discount",
    "internal_dealing_range_high",
    "internal_dealing_range_low",
    "internal_dealing_equilibrium",
    "internal_dealing_percentile",
    "internal_dealing_location",
    "internal_dealing_distance_to_equilibrium",
    "internal_dealing_valid",
    "external_dealing_range_high",
    "external_dealing_range_low",
    "external_dealing_equilibrium",
    "external_dealing_percentile",
    "external_dealing_location",
    "external_dealing_distance_to_equilibrium",
    "external_dealing_valid",
    "draw_on_liquidity_direction",
    "dol_direction",
    "dol_primary_direction",
    "dol_primary_confidence",
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


def _norm(v):
    if v is None or pd.isna(v):
        return None
    return str(v).strip().lower()


def _segment(df: pd.DataFrame, col: str):
    s = df[col].where(df[col].notna(), "<missing>").astype(str)
    return {
        v: _metrics(df.loc[s == v])
        for v in sorted(s.unique())
    }


def _quartiles(df: pd.DataFrame, col: str):
    s = pd.to_numeric(df[col], errors="coerce")
    if s.notna().sum() < 20:
        return {}

    tmp = df.loc[s.notna()].copy()

    try:
        tmp["_bucket"] = pd.qcut(
            pd.to_numeric(tmp[col], errors="coerce"),
            4,
            duplicates="drop",
        ).astype(str)
    except ValueError:
        return {}

    return _segment(tmp, "_bucket")


def enrich(ledger: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    validate_ledger(ledger)

    missing = REQUIRED - set(features.columns)
    if missing:
        raise PremiumDiscountResearchError(
            f"Missing EXP-013 columns: {sorted(missing)}"
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

        direction = str(trade["direction"])

        r["internal_pd"] = _norm(
            row.get("internal_premium_discount")
        )
        r["external_pd"] = _norm(
            row.get("external_premium_discount")
        )

        r["internal_location"] = _norm(
            row.get("internal_dealing_location")
        )
        r["external_location"] = _norm(
            row.get("external_dealing_location")
        )

        r["internal_valid"] = _truthy(
            row.get("internal_dealing_valid")
        )
        r["external_valid"] = _truthy(
            row.get("external_dealing_valid")
        )

        for col in (
            "internal_dealing_percentile",
            "internal_dealing_distance_to_equilibrium",
            "external_dealing_percentile",
            "external_dealing_distance_to_equilibrium",
        ):
            r[col] = _safe_float(row.get(col))

        # Direction-relative premium/discount classification.
        # Longs from discount and shorts from premium are "favorable";
        # longs from premium and shorts from discount are "unfavorable".
        ipd = r["internal_pd"]
        epd = r["external_pd"]

        def classify(pd_value):
            if pd_value not in {"premium", "discount", "equilibrium"}:
                return "unknown"

            if pd_value == "equilibrium":
                return "equilibrium"

            if direction == "long":
                return (
                    "favorable"
                    if pd_value == "discount"
                    else "unfavorable"
                )

            return (
                "favorable"
                if pd_value == "premium"
                else "unfavorable"
            )

        r["internal_directional_pd"] = classify(ipd)
        r["external_directional_pd"] = classify(epd)

        # Internal/external agreement.
        if ipd in {"premium", "discount", "equilibrium"} and epd in {
            "premium", "discount", "equilibrium"
        }:
            r["pd_agreement"] = (
                "agree" if ipd == epd else "disagree"
            )
        else:
            r["pd_agreement"] = "unknown"

        dol = _norm(row.get("dol_primary_direction"))
        if dol is None:
            dol = _norm(row.get("dol_direction"))
        if dol is None:
            dol = _norm(row.get("draw_on_liquidity_direction"))

        r["dol_direction_exp013"] = dol
        r["dol_confidence_exp013"] = _safe_float(
            row.get("dol_primary_confidence")
        )

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

        records.append(r)

    return pd.DataFrame(records)


def analyze(frames: dict[int, pd.DataFrame]):
    if set(frames) != {2023, 2024, 2025}:
        raise PremiumDiscountResearchError(
            "EXP-013 requires 2023/2024/2025"
        )

    all_frames = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        all_frames.append(x)

    df = pd.concat(all_frames, ignore_index=True)

    result = {
        "experiment_id": "EXP-013_premium-discount",
        "coverage": {
            "total": int(len(df)),
            "matched": int(df["feature_matched"].sum()),
        },
        "overall": _metrics(df),
        "internal_pd": _segment(df, "internal_pd"),
        "external_pd": _segment(df, "external_pd"),
        "internal_directional_pd": _segment(
            df, "internal_directional_pd"
        ),
        "external_directional_pd": _segment(
            df, "external_directional_pd"
        ),
        "pd_agreement": _segment(df, "pd_agreement"),
        "dol_alignment": _segment(df, "dol_alignment"),
        "internal_percentile_quartiles": _quartiles(
            df[df["internal_valid"]],
            "internal_dealing_percentile",
        ),
        "external_percentile_quartiles": _quartiles(
            df[df["external_valid"]],
            "external_dealing_percentile",
        ),
        "internal_eq_distance_quartiles": _quartiles(
            df[df["internal_valid"]],
            "internal_dealing_distance_to_equilibrium",
        ),
        "external_eq_distance_quartiles": _quartiles(
            df[df["external_valid"]],
            "external_dealing_distance_to_equilibrium",
        ),
        "by_year": {},
        "by_direction": {},
        "by_family": {},
        "controlled_by_dol": {},
    }

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "internal_directional_pd": _segment(
                y, "internal_directional_pd"
            ),
            "external_directional_pd": _segment(
                y, "external_directional_pd"
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "internal_pd": _segment(g, "internal_pd"),
            "external_pd": _segment(g, "external_pd"),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "internal_directional_pd": _segment(
                g, "internal_directional_pd"
            ),
            "external_directional_pd": _segment(
                g, "external_directional_pd"
            ),
        }

    # DOL-controlled slices: compare P/D within each DOL state.
    for dol_state in (
        "aligned",
        "opposed",
        "neutral/unknown",
    ):
        g = df[df["dol_alignment"] == dol_state]

        result["controlled_by_dol"][dol_state] = {
            "internal_directional_pd": _segment(
                g, "internal_directional_pd"
            ),
            "external_directional_pd": _segment(
                g, "external_directional_pd"
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
        "internal_pd",
        "external_pd",
        "internal_directional_pd",
        "external_directional_pd",
        "pd_agreement",
        "dol_alignment",
        "internal_percentile_quartiles",
        "external_percentile_quartiles",
        "internal_eq_distance_quartiles",
        "external_eq_distance_quartiles",
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

    for dol, sections in result["controlled_by_dol"].items():
        for section, values in sections.items():
            add(f"dol_{dol}_{section}", values)

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
        "# EXP-013 — Premium / Discount",
        "",
        "Diagnostic only.",
        "",
        "## Coverage",
        "",
        f"- Feature matched: {result['coverage']['matched']} / {result['coverage']['total']}",
        "",
    ]

    sections = (
        ("Internal premium / discount", "internal_pd"),
        ("External premium / discount", "external_pd"),
        (
            "Internal direction-relative P/D",
            "internal_directional_pd",
        ),
        (
            "External direction-relative P/D",
            "external_directional_pd",
        ),
        ("Internal/external P/D agreement", "pd_agreement"),
        ("DOL alignment", "dol_alignment"),
        (
            "Internal dealing percentile quartiles",
            "internal_percentile_quartiles",
        ),
        (
            "External dealing percentile quartiles",
            "external_percentile_quartiles",
        ),
        (
            "Internal distance-to-equilibrium quartiles",
            "internal_eq_distance_quartiles",
        ),
        (
            "External distance-to-equilibrium quartiles",
            "external_eq_distance_quartiles",
        ),
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

    lines += ["## Direction diagnostics", ""]

    for direction, sections in result["by_direction"].items():
        lines += [f"### {direction}", ""]

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

    lines += ["## DOL-controlled diagnostics", ""]

    for dol_state, sections in result["controlled_by_dol"].items():
        lines += [f"### {dol_state}", ""]

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
        "- Premium/discount classifications are the persisted historical feature outputs; they are not reconstructed from hindsight.",
        "- DOL control is observational, not causal.",
        "- No score or entry rules are changed.",
        "",
        "## Decision discipline",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
