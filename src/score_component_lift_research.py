"""R4.2 — scoring-component realized lift analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class ScoreComponentLiftError(RuntimeError):
    pass


COMPONENTS = {
    "higher_timeframe_bias": (
        "long_score_higher_timeframe_bias",
        "short_score_higher_timeframe_bias",
    ),
    "liquidity_sweep": (
        "long_score_liquidity_sweep",
        "short_score_liquidity_sweep",
    ),
    "displacement": (
        "long_score_displacement",
        "short_score_displacement",
    ),
    "structure_shift": (
        "long_score_structure_shift",
        "short_score_structure_shift",
    ),
    "fvg_or_retest": (
        "long_score_fvg_or_retest",
        "short_score_fvg_or_retest",
    ),
    "draw_on_liquidity": (
        "long_score_draw_on_liquidity",
        "short_score_draw_on_liquidity",
    ),
    "premium_discount": (
        "long_score_premium_discount",
        "short_score_premium_discount",
    ),
    "relative_volume": (
        "long_score_relative_volume",
        "short_score_relative_volume",
    ),
    "signal_to_noise": (
        "long_score_signal_to_noise",
        "short_score_signal_to_noise",
    ),
    "room_to_target": (
        "long_score_room_to_target",
        "short_score_room_to_target",
    ),
    "key_location": (
        "long_score_key_location",
        "short_score_key_location",
    ),

    # Penalties
    "penalty_data_quality": (
        "long_score_penalty_data_quality",
        "short_score_penalty_data_quality",
    ),
    "penalty_failed_retest": (
        "long_score_penalty_failed_retest",
        "short_score_penalty_failed_retest",
    ),
    "penalty_htf_conflict": (
        "long_score_penalty_htf_conflict",
        "short_score_penalty_htf_conflict",
    ),
    "penalty_major_obstacle": (
        "long_score_penalty_major_obstacle",
        "short_score_penalty_major_obstacle",
    ),
    "penalty_snr_conflict": (
        "long_score_penalty_snr_conflict",
        "short_score_penalty_snr_conflict",
    ),
    "penalty_stale_setup": (
        "long_score_penalty_stale_setup",
        "short_score_penalty_stale_setup",
    ),
}


def safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


def enrich(ledger, features):
    validate_ledger(ledger)

    required = {"timestamp"}

    for long_col, short_col in COMPONENTS.values():
        required.add(long_col)
        required.add(short_col)

    missing = required - set(features.columns)

    if missing:
        raise ScoreComponentLiftError(
            f"Missing R4.2 fields: {sorted(missing)}"
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

        for component, (
            long_col,
            short_col,
        ) in COMPONENTS.items():

            source_col = (
                long_col
                if direction == "long"
                else short_col
            )

            value = safe_float(
                row.get(source_col)
            )

            r[f"{component}_value"] = value

            # Any non-zero score contribution / penalty counts as active.
            r[f"{component}_active"] = (
                False
                if pd.isna(value)
                else abs(value) > 1e-12
            )

        records.append(r)

    return pd.DataFrame(records)


def metric_lift(with_metrics, without_metrics):
    def diff(key):
        a = with_metrics.get(key)
        b = without_metrics.get(key)

        if a is None or b is None:
            return None

        try:
            if np.isnan(a) or np.isnan(b):
                return None
        except TypeError:
            pass

        return float(a) - float(b)

    return {
        "expectancy_points_lift": diff(
            "expectancy_points"
        ),
        "expectancy_r_lift": diff(
            "expectancy_r"
        ),
        "profit_factor_lift": diff(
            "profit_factor"
        ),
        "tp1_lift": diff(
            "tp1_hit_rate"
        ),
        "tp2_lift": diff(
            "tp2_hit_rate"
        ),
        "tp3_lift": diff(
            "tp3_hit_rate"
        ),
        "tp4_lift": diff(
            "tp4_hit_rate"
        ),
        "stop_rate_lift": diff(
            "stop_rate"
        ),
        "avg_mfe_lift": diff(
            "avg_mfe"
        ),
        "avg_mae_lift": diff(
            "avg_mae"
        ),
    }


def component_analysis(df, component):
    active_col = f"{component}_active"

    with_df = df[df[active_col] == True]
    without_df = df[df[active_col] == False]

    with_metrics = _metrics(with_df)
    without_metrics = _metrics(without_df)

    return {
        "with_component": with_metrics,
        "without_component": without_metrics,
        "lift": metric_lift(
            with_metrics,
            without_metrics,
        ),
    }


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise ScoreComponentLiftError(
            "R4.2 requires 2023/2024/2025"
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
        "research_id":
            "R4.2_score_component_lift",

        "coverage": {
            "total": int(len(df)),
            "matched": int(
                df["feature_matched"].sum()
            ),
        },

        "components": {},
    }

    for component in COMPONENTS:
        comp = {
            "overall":
                component_analysis(
                    df,
                    component,
                ),

            "by_year": {},
            "by_direction": {},
            "by_family": {},
        }

        for year in sorted(
            df["year"].unique()
        ):
            comp["by_year"][str(year)] = (
                component_analysis(
                    df[df["year"] == year],
                    component,
                )
            )

        for direction in (
            "long",
            "short",
        ):
            comp["by_direction"][direction] = (
                component_analysis(
                    df[
                        df["direction"]
                        == direction
                    ],
                    component,
                )
            )

        for family in (
            "reversal",
            "continuation",
        ):
            comp["by_family"][family] = (
                component_analysis(
                    df[
                        df["setup_family"]
                        == family
                    ],
                    component,
                )
            )

        result["components"][component] = comp

    return result, df


def summary_frame(result):
    rows = []

    for component, data in (
        result["components"].items()
    ):
        overall = data["overall"]

        with_m = overall["with_component"]
        without_m = overall["without_component"]
        lift = overall["lift"]

        rows.append({
            "component": component,

            "with_trades":
                with_m.get("trades"),

            "without_trades":
                without_m.get("trades"),

            "with_expectancy":
                with_m.get(
                    "expectancy_points"
                ),

            "without_expectancy":
                without_m.get(
                    "expectancy_points"
                ),

            "expectancy_lift":
                lift.get(
                    "expectancy_points_lift"
                ),

            "with_pf":
                with_m.get(
                    "profit_factor"
                ),

            "without_pf":
                without_m.get(
                    "profit_factor"
                ),

            "pf_lift":
                lift.get(
                    "profit_factor_lift"
                ),

            "tp1_lift":
                lift.get("tp1_lift"),

            "tp2_lift":
                lift.get("tp2_lift"),

            "tp3_lift":
                lift.get("tp3_lift"),

            "tp4_lift":
                lift.get("tp4_lift"),

            "stop_rate_lift":
                lift.get(
                    "stop_rate_lift"
                ),

            "avg_mfe_lift":
                lift.get(
                    "avg_mfe_lift"
                ),

            "avg_mae_lift":
                lift.get(
                    "avg_mae_lift"
                ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            "expectancy_lift",
            ascending=False,
            na_position="last",
        )
        .reset_index(drop=True)
    )


def detail_frame(result):
    rows = []

    for component, data in (
        result["components"].items()
    ):
        groups = {
            "overall": {
                "all":
                    data["overall"]
            },

            "year":
                data["by_year"],

            "direction":
                data["by_direction"],

            "family":
                data["by_family"],
        }

        for dimension, values in (
            groups.items()
        ):
            for value, result_block in (
                values.items()
            ):
                with_m = (
                    result_block[
                        "with_component"
                    ]
                )

                without_m = (
                    result_block[
                        "without_component"
                    ]
                )

                lift = (
                    result_block["lift"]
                )

                rows.append({
                    "component":
                        component,

                    "dimension":
                        dimension,

                    "value":
                        value,

                    "with_trades":
                        with_m.get(
                            "trades"
                        ),

                    "without_trades":
                        without_m.get(
                            "trades"
                        ),

                    "with_expectancy":
                        with_m.get(
                            "expectancy_points"
                        ),

                    "without_expectancy":
                        without_m.get(
                            "expectancy_points"
                        ),

                    "expectancy_lift":
                        lift.get(
                            "expectancy_points_lift"
                        ),

                    "with_pf":
                        with_m.get(
                            "profit_factor"
                        ),

                    "without_pf":
                        without_m.get(
                            "profit_factor"
                        ),

                    "pf_lift":
                        lift.get(
                            "profit_factor_lift"
                        ),
                })

    return pd.DataFrame(rows)


def markdown_report(result):
    summary = summary_frame(result)

    lines = [
        "# R4.2 — Score Component Lift Analysis",
        "",
        "Diagnostic calibration research only.",
        "",
        "## Coverage",
        "",
        f"- Matched baseline trades: "
        f"{result['coverage']['matched']} / "
        f"{result['coverage']['total']}",
        "",
        "## Aggregate component lift",
        "",
        "| Component | With n | Without n | With Exp | Without Exp | Exp Lift | With PF | Without PF | PF Lift |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, r in summary.iterrows():
        def f(v):
            if pd.isna(v):
                return "—"
            return f"{float(v):.2f}"

        lines.append(
            f"| {r['component']} | "
            f"{int(r['with_trades'])} | "
            f"{int(r['without_trades'])} | "
            f"{f(r['with_expectancy'])} | "
            f"{f(r['without_expectancy'])} | "
            f"{f(r['expectancy_lift'])} | "
            f"{f(r['with_pf'])} | "
            f"{f(r['without_pf'])} | "
            f"{f(r['pf_lift'])} |"
        )

    lines += [
        "",
        "## Interpretation limits",
        "",
        "- These are realized associations inside the surviving historical baseline trades.",
        "- Components already participate in historical scoring, so component presence is selection-confounded.",
        "- Lift does not prove causal value.",
        "- A component with positive aggregate lift can still be unstable across years or setup families.",
        "- Penalty fields require special interpretation because surviving trades may represent only cases where the overall score remained high enough despite the penalty.",
        "",
        "## Next step",
        "",
        "Use the year/family/direction stability results from this analysis together with the completed EXP-001 through EXP-021 evidence before R4.3 redundancy analysis.",
        "",
        "**No score-weight changes are authorized by R4.2 alone.**",
    ]

    return "\n".join(lines)
