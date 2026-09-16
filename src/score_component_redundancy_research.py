"""R4.3 — score-component redundancy / double-counting diagnostics."""

from __future__ import annotations

import itertools
import numpy as np
import pandas as pd

from directional_research import _metrics
from score_component_lift_research import COMPONENTS


class ScoreComponentRedundancyError(RuntimeError):
    pass


def phi_binary(a: pd.Series, b: pd.Series):
    x = a.astype(bool).astype(int)
    y = b.astype(bool).astype(int)

    if x.nunique() < 2 or y.nunique() < 2:
        return np.nan

    return float(x.corr(y))


def jaccard(a: pd.Series, b: pd.Series):
    x = a.astype(bool)
    y = b.astype(bool)

    union = (x | y).sum()

    if union == 0:
        return np.nan

    return float((x & y).sum() / union)


def conditional_overlap(a: pd.Series, b: pd.Series):
    x = a.astype(bool)
    y = b.astype(bool)

    a_count = x.sum()
    b_count = y.sum()

    both = (x & y).sum()

    return {
        "a_when_b": (
            float(both / b_count)
            if b_count
            else np.nan
        ),
        "b_when_a": (
            float(both / a_count)
            if a_count
            else np.nan
        ),
    }


def pair_metrics(df, a, b):
    a_col = f"{a}_active"
    b_col = f"{b}_active"

    if a_col not in df.columns or b_col not in df.columns:
        raise ScoreComponentRedundancyError(
            f"Missing active columns for {a}, {b}"
        )

    x = df[a_col].fillna(False).astype(bool)
    y = df[b_col].fillna(False).astype(bool)

    neither = df[~x & ~y]
    a_only = df[x & ~y]
    b_only = df[~x & y]
    both = df[x & y]

    overlap = conditional_overlap(x, y)

    return {
        "component_a": a,
        "component_b": b,

        "phi": phi_binary(x, y),
        "jaccard": jaccard(x, y),

        "a_active": int(x.sum()),
        "b_active": int(y.sum()),
        "both_active": int((x & y).sum()),

        "a_when_b": overlap["a_when_b"],
        "b_when_a": overlap["b_when_a"],

        "neither": _metrics(neither),
        "a_only": _metrics(a_only),
        "b_only": _metrics(b_only),
        "both": _metrics(both),
    }


def incremental_value(block):
    def exp(section):
        v = block[section].get("expectancy_points")
        return np.nan if v is None else float(v)

    def pf(section):
        v = block[section].get("profit_factor")
        return np.nan if v is None else float(v)

    return {
        "a_added_to_b_expectancy":
            exp("both") - exp("b_only"),

        "b_added_to_a_expectancy":
            exp("both") - exp("a_only"),

        "a_added_to_b_pf":
            pf("both") - pf("b_only"),

        "b_added_to_a_pf":
            pf("both") - pf("a_only"),
    }


def analyze(df):
    required = [
        f"{component}_active"
        for component in COMPONENTS
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ScoreComponentRedundancyError(
            f"Missing component-active fields: {missing}"
        )

    pairs = []

    for a, b in itertools.combinations(
        COMPONENTS.keys(),
        2,
    ):
        block = pair_metrics(df, a, b)

        pairs.append({
            **block,
            "incremental":
                incremental_value(block),
        })

    return {
        "research_id":
            "R4.3_component_redundancy",
        "trade_count": int(len(df)),
        "pairs": pairs,
    }


def summary_frame(result):
    rows = []

    for p in result["pairs"]:
        inc = p["incremental"]

        rows.append({
            "component_a":
                p["component_a"],

            "component_b":
                p["component_b"],

            "phi":
                p["phi"],

            "jaccard":
                p["jaccard"],

            "a_active":
                p["a_active"],

            "b_active":
                p["b_active"],

            "both_active":
                p["both_active"],

            "a_when_b":
                p["a_when_b"],

            "b_when_a":
                p["b_when_a"],

            "neither_expectancy":
                p["neither"].get(
                    "expectancy_points"
                ),

            "a_only_expectancy":
                p["a_only"].get(
                    "expectancy_points"
                ),

            "b_only_expectancy":
                p["b_only"].get(
                    "expectancy_points"
                ),

            "both_expectancy":
                p["both"].get(
                    "expectancy_points"
                ),

            "a_added_to_b_expectancy":
                inc[
                    "a_added_to_b_expectancy"
                ],

            "b_added_to_a_expectancy":
                inc[
                    "b_added_to_a_expectancy"
                ],

            "a_added_to_b_pf":
                inc[
                    "a_added_to_b_pf"
                ],

            "b_added_to_a_pf":
                inc[
                    "b_added_to_a_pf"
                ],
        })

    df = pd.DataFrame(rows)

    df["abs_phi"] = df["phi"].abs()

    return df.sort_values(
        ["abs_phi", "jaccard"],
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


def markdown_report(result):
    df = summary_frame(result)

    lines = [
        "# R4.3 — Score Component Redundancy",
        "",
        "Diagnostic calibration research only.",
        "",
        f"- Baseline trades: {result['trade_count']}",
        "",
        "## Strongest activation relationships",
        "",
        "| A | B | Phi | Jaccard | Both n | A when B | B when A | Both Exp | A-only Exp | B-only Exp |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, r in df.head(30).iterrows():

        def f(v):
            if pd.isna(v):
                return "—"
            return f"{float(v):.2f}"

        def pct(v):
            if pd.isna(v):
                return "—"
            return f"{100 * float(v):.1f}%"

        lines.append(
            f"| {r['component_a']} | "
            f"{r['component_b']} | "
            f"{f(r['phi'])} | "
            f"{f(r['jaccard'])} | "
            f"{int(r['both_active'])} | "
            f"{pct(r['a_when_b'])} | "
            f"{pct(r['b_when_a'])} | "
            f"{f(r['both_expectancy'])} | "
            f"{f(r['a_only_expectancy'])} | "
            f"{f(r['b_only_expectancy'])} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "- High activation correlation alone does not prove two components are redundant.",
        "- Redundancy is more credible when activation overlap is high AND the second component adds little incremental expectancy/PF when the first is already present.",
        "- A correlated pair can still deserve separate scoring if the combined state materially outperforms either component alone.",
        "- Sparse penalties and rare components must not drive weight changes.",
        "",
        "## Calibration rule",
        "",
        "Do not alter score weights from R4.3 alone. Combine these results with R4.2 realized lift and EXP-001 through EXP-021 evidence.",
    ]

    return "\n".join(lines)
