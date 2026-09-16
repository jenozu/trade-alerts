"""R4.4 — Offline candidate scoring-model diagnostics.

This module DOES NOT modify production strategy weights.
It re-scores the existing R4.2 classified baseline trades using
persisted component contribution fractions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from directional_research import _metrics


POSITIVE_COMPONENTS = [
    "higher_timeframe_bias",
    "draw_on_liquidity",
    "key_location",
    "liquidity_sweep",
    "displacement",
    "structure_shift",
    "fvg_or_retest",
    "relative_volume",
    "signal_to_noise",
    "premium_discount",
    "room_to_target",
]


CANDIDATE_WEIGHTS = {
    # Current production model — control.
    "baseline": {
        "higher_timeframe_bias": 10,
        "draw_on_liquidity": 10,
        "key_location": 8,
        "liquidity_sweep": 14,
        "displacement": 12,
        "structure_shift": 12,
        "fvg_or_retest": 8,
        "relative_volume": 6,
        "signal_to_noise": 10,
        "premium_discount": 4,
        "room_to_target": 6,
    },

    # Small evidence-based move away from weak components.
    "candidate_conservative": {
        "higher_timeframe_bias": 12,
        "draw_on_liquidity": 10,
        "key_location": 8,
        "liquidity_sweep": 10,
        "displacement": 14,
        "structure_shift": 14,
        "fvg_or_retest": 10,
        "relative_volume": 6,
        "signal_to_noise": 7,
        "premium_discount": 3,
        "room_to_target": 6,
    },

    # Stronger tilt toward components with positive R4.2 lift.
    "candidate_evidence_tilt": {
        "higher_timeframe_bias": 13,
        "draw_on_liquidity": 9,
        "key_location": 8,
        "liquidity_sweep": 8,
        "displacement": 16,
        "structure_shift": 16,
        "fvg_or_retest": 12,
        "relative_volume": 6,
        "signal_to_noise": 5,
        "premium_discount": 2,
        "room_to_target": 5,
    },

    # More aggressively reduces overlapping / weak buckets.
    "candidate_redundancy_reduced": {
        "higher_timeframe_bias": 11,
        "draw_on_liquidity": 8,
        "key_location": 8,
        "liquidity_sweep": 8,
        "displacement": 18,
        "structure_shift": 18,
        "fvg_or_retest": 12,
        "relative_volume": 7,
        "signal_to_noise": 4,
        "premium_discount": 2,
        "room_to_target": 4,
    },
}


PENALTY_COMPONENTS = [
    "penalty_data_quality",
    "penalty_failed_retest",
    "penalty_htf_conflict",
    "penalty_major_obstacle",
    "penalty_snr_conflict",
    "penalty_stale_setup",
]


def validate_candidates():
    for name, weights in CANDIDATE_WEIGHTS.items():
        missing = set(POSITIVE_COMPONENTS) - set(weights)

        if missing:
            raise ValueError(
                f"{name} missing components: {sorted(missing)}"
            )

        total = sum(weights.values())

        if abs(total - 100.0) > 1e-9:
            raise ValueError(
                f"{name} weights total {total}, expected 100"
            )


def load_current_weights(
    config_path="config/strategy.yaml",
):
    config = yaml.safe_load(
        Path(config_path).read_text()
    )

    weights = (
        config["scoring"]["positive_weights"]
    )

    return {
        component: float(weights[component])
        for component in POSITIVE_COMPONENTS
    }


def component_fraction(
    series,
    current_weight,
):
    values = pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0.0)

    if current_weight <= 0:
        return pd.Series(
            0.0,
            index=series.index,
        )

    fraction = values / float(current_weight)

    return fraction.clip(
        lower=0.0,
        upper=1.0,
    )


def penalty_total(df):
    total = pd.Series(
        0.0,
        index=df.index,
    )

    for component in PENALTY_COMPONENTS:
        col = f"{component}_value"

        if col not in df.columns:
            continue

        total = total + pd.to_numeric(
            df[col],
            errors="coerce",
        ).fillna(0.0)

    return total


def rescore(
    df,
    *,
    candidate_weights,
    current_weights,
):
    positive = pd.Series(
        0.0,
        index=df.index,
    )

    for component in POSITIVE_COMPONENTS:
        col = f"{component}_value"

        if col not in df.columns:
            raise ValueError(
                f"Missing persisted contribution: {col}"
            )

        fraction = component_fraction(
            df[col],
            current_weights[component],
        )

        positive = (
            positive
            + fraction
            * float(
                candidate_weights[component]
            )
        )

    penalties = penalty_total(df)

    return (
        positive + penalties
    ).clip(
        lower=0.0,
        upper=100.0,
    )


def score_band(scores):
    return pd.cut(
        scores,
        bins=[
            -0.001,
            39,
            54,
            69,
            79,
            89,
            100.001,
        ],
        labels=[
            "no_trade",
            "watch",
            "developing",
            "near_trigger",
            "high_probability",
            "a_plus_plus",
        ],
        include_lowest=True,
    ).astype(str)


def evaluate_candidate(
    df,
    score_col,
):
    scores = pd.to_numeric(
        df[score_col],
        errors="coerce",
    )

    result = {
        "score_mean":
            float(scores.mean()),

        "score_median":
            float(scores.median()),

        "bands": {},

        "thresholds": {},
    }

    band = score_band(scores)

    for value in [
        "no_trade",
        "watch",
        "developing",
        "near_trigger",
        "high_probability",
        "a_plus_plus",
    ]:
        subset = df[
            band == value
        ]

        result["bands"][value] = (
            _metrics(subset)
        )

    for threshold in (
        70,
        80,
        90,
    ):
        subset = df[
            scores >= threshold
        ]

        result["thresholds"][
            str(threshold)
        ] = _metrics(subset)

    return result


def analyze(df, config_path):
    validate_candidates()

    current_weights = (
        load_current_weights(
            config_path
        )
    )

    work = df.copy()

    for name, weights in (
        CANDIDATE_WEIGHTS.items()
    ):
        work[f"score_{name}"] = rescore(
            work,
            candidate_weights=weights,
            current_weights=current_weights,
        )

    baseline_reconstructed = (
        work["score_baseline"]
    )

    actual = pd.to_numeric(
        work["raw_score"],
        errors="coerce",
    )

    diff = (
        baseline_reconstructed
        - actual
    ).abs()

    reconstruction = {
        "mae":
            float(diff.mean()),

        "median_abs_error":
            float(diff.median()),

        "max_abs_error":
            float(diff.max()),

        "within_1_point_rate":
            float(
                (diff <= 1.0).mean()
            ),
    }

    results = {
        "research_id":
            "R4.4_candidate_scoring_models",

        "trade_count":
            int(len(work)),

        "current_weights":
            current_weights,

        "candidates":
            CANDIDATE_WEIGHTS,

        "baseline_reconstruction":
            reconstruction,

        "performance":
            {},
    }

    for name in CANDIDATE_WEIGHTS:
        results["performance"][name] = (
            evaluate_candidate(
                work,
                f"score_{name}",
            )
        )

    return results, work


def summary_frame(result):
    rows = []

    for name, block in (
        result["performance"].items()
    ):
        for threshold, metrics in (
            block["thresholds"].items()
        ):
            rows.append({
                "model": name,
                "threshold": int(threshold),
                "trades":
                    metrics.get("trades"),
                "expectancy_points":
                    metrics.get(
                        "expectancy_points"
                    ),
                "expectancy_r":
                    metrics.get(
                        "expectancy_r"
                    ),
                "profit_factor":
                    metrics.get(
                        "profit_factor"
                    ),
                "win_rate":
                    metrics.get(
                        "win_rate"
                    ),
                "net_points":
                    metrics.get(
                        "net_points"
                    ),
                "tp1_hit_rate":
                    metrics.get(
                        "tp1_hit_rate"
                    ),
                "tp2_hit_rate":
                    metrics.get(
                        "tp2_hit_rate"
                    ),
                "tp3_hit_rate":
                    metrics.get(
                        "tp3_hit_rate"
                    ),
                "tp4_hit_rate":
                    metrics.get(
                        "tp4_hit_rate"
                    ),
                "stop_rate":
                    metrics.get(
                        "stop_rate"
                    ),
            })

    return pd.DataFrame(rows)


def weights_frame():
    rows = []

    for model, weights in (
        CANDIDATE_WEIGHTS.items()
    ):
        for component, weight in (
            weights.items()
        ):
            rows.append({
                "model": model,
                "component": component,
                "weight": weight,
            })

    return pd.DataFrame(rows)


def markdown_report(result):
    summary = summary_frame(result)

    recon = (
        result[
            "baseline_reconstruction"
        ]
    )

    lines = [
        "# R4.4 — Candidate Scoring Models",
        "",
        "Offline calibration research only.",
        "",
        "Production `strategy.yaml` was not changed.",
        "",
        "## Baseline reconstruction",
        "",
        f"- MAE: {recon['mae']:.3f}",
        f"- Median absolute error: {recon['median_abs_error']:.3f}",
        f"- Maximum absolute error: {recon['max_abs_error']:.3f}",
        f"- Within 1 point: {100*recon['within_1_point_rate']:.1f}%",
        "",
        "## Candidate weights",
        "",
    ]

    for name, weights in (
        result["candidates"].items()
    ):
        lines.append(
            f"### {name}"
        )
        lines.append("")

        for component, weight in (
            weights.items()
        ):
            lines.append(
                f"- {component}: {weight}"
            )

        lines.append("")

    lines += [
        "## Existing-baseline threshold diagnostics",
        "",
        "| Model | Threshold | Trades | Exp pts | Exp R | PF | Win | Net pts | TP1 | TP2 | TP3 | TP4 | Stop |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def f(v, d=2):
        if v is None or pd.isna(v):
            return "—"
        return f"{float(v):.{d}f}"

    def pct(v):
        if v is None or pd.isna(v):
            return "—"
        return f"{100*float(v):.1f}%"

    for _, r in summary.iterrows():
        lines.append(
            f"| {r['model']} | "
            f"{int(r['threshold'])} | "
            f"{int(r['trades'])} | "
            f"{f(r['expectancy_points'])} | "
            f"{f(r['expectancy_r'],3)} | "
            f"{f(r['profit_factor'])} | "
            f"{pct(r['win_rate'])} | "
            f"{f(r['net_points'])} | "
            f"{pct(r['tp1_hit_rate'])} | "
            f"{pct(r['tp2_hit_rate'])} | "
            f"{pct(r['tp3_hit_rate'])} | "
            f"{pct(r['tp4_hit_rate'])} | "
            f"{pct(r['stop_rate'])} |"
        )

    lines += [
        "",
        "## Critical limitation",
        "",
        "These diagnostics re-score only the trades that survived the historical baseline model.",
        "",
        "They do **not** show the true performance of the candidate models because changing weights would also change which historical setups became eligible for entry.",
        "",
        "The candidate models must therefore be tested next against the full scored historical feature universe using the normal causal backtest path.",
        "",
        "**No production score-weight changes are authorized by R4.4.**",
    ]

    return "\n".join(lines)
