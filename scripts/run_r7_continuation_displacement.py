#!/usr/bin/env python3
"""R7.0 continuation-proxy + same-direction displacement interaction replay.

Research question:
Does requiring same-direction recent displacement improve the existing
continuation-proxy setup family when reversals and every other strategy family
remain untouched?

The setup-family contract is the already-established EXP-003 contract:
- directional recent liquidity sweep present -> reversal
- no directional recent liquidity sweep      -> continuation proxy

This experiment changes only candidate qualification for continuation-proxy
signals. A continuation-proxy candidate must also have same-direction recent
displacement. Reversal candidates are unchanged.

Frozen:
- baseline score weights and threshold-70 eligibility;
- entry timing and slippage;
- untouched CONTROL stop behavior;
- TP1-TP4 / TP100 exit behavior;
- session/time rules;
- maximum holding time;
- one-open-trade path dependence.

The CONTROL replay must reproduce the frozen R4.5 baseline exactly before the
candidate is trusted.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.resume_r45 import (
    CANDIDATE_WEIGHTS,
    FEATURES,
    YEARS,
    load_config,
    model_config,
    read_trades,
)
from scripts.run_r45_chunked import parquet_replay
from scripts.run_r46_threshold_replay import assert_frozen_70
from scripts.run_r5_fixed_stop_sweep import max_drawdown_points, profit_factor
from backtest import calculate_backtest_metrics, run_backtest
from setup_family_research import derive_setup_family

MODEL = "CONTINUATION_DISPLACEMENT"
ELIGIBLE_SCORE_BANDS = {"near_trigger", "high_probability", "a_plus_plus"}

DIRECTION_FIELDS = {
    "long": {
        "candidate": "long_candidate",
        "score_band": "long_score_band",
        "sweep": "recent_sell_side_sweep",
        "displacement": "recent_bullish_displacement",
    },
    "short": {
        "candidate": "short_candidate",
        "score_band": "short_score_band",
        "sweep": "recent_buy_side_sweep",
        "displacement": "recent_bearish_displacement",
    },
}


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise ValueError(
            f"R7.0 requires historical field {column!r}; refusing to invent a proxy"
        )
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(False)
    text = values.astype("string").str.strip().str.lower()
    mapped = text.map(
        {
            "true": True,
            "1": True,
            "yes": True,
            "y": True,
            "false": False,
            "0": False,
            "no": False,
            "n": False,
        }
    )
    mapped = mapped.where(values.notna(), False)
    if mapped.isna().any():
        bad = sorted(text[mapped.isna()].dropna().unique().tolist())
        raise ValueError(
            f"{column} must be boolean-like; unsupported values: {bad[:10]}"
        )
    return mapped.astype(bool)


def _baseline_candidates(frame: pd.DataFrame, direction: str) -> pd.Series:
    fields = DIRECTION_FIELDS[direction]
    candidate = fields["candidate"]
    if candidate in frame.columns:
        return _bool_series(frame, candidate)
    band = fields["score_band"]
    if band not in frame.columns:
        raise ValueError(
            f"R7.0 requires {candidate!r} or {band!r} to preserve frozen eligibility"
        )
    return frame[band].astype("string").isin(ELIGIBLE_SCORE_BANDS)


def apply_continuation_displacement_gate(
    scored: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the single R7.0 qualification change without mutating scores.

    Reversal candidates (directional recent sweep present) remain eligible.
    Continuation-proxy candidates (no directional recent sweep) survive only
    when same-direction recent displacement is present.
    """
    result = scored.copy()
    diagnostics: list[dict] = []

    for direction, fields in DIRECTION_FIELDS.items():
        base = _baseline_candidates(result, direction)
        sweep = _bool_series(result, fields["sweep"])
        displacement = _bool_series(result, fields["displacement"])

        continuation_proxy = base & ~sweep
        pass_gate = base & (sweep | displacement)
        excluded = continuation_proxy & ~displacement

        result[fields["candidate"]] = pass_gate

        diagnostics.append(
            {
                "direction": direction,
                "baseline_eligible_rows": int(base.sum()),
                "reversal_proxy_rows": int((base & sweep).sum()),
                "continuation_proxy_rows": int(continuation_proxy.sum()),
                "continuation_with_displacement_rows": int(
                    (continuation_proxy & displacement).sum()
                ),
                "continuation_without_displacement_rows": int(excluded.sum()),
                "candidate_rows_after_gate": int(pass_gate.sum()),
                "excluded_rows": int(excluded.sum()),
            }
        )

    return result, pd.DataFrame(diagnostics)


def summarize_r7(year: int, model: str, trades: pd.DataFrame) -> dict:
    metrics = calculate_backtest_metrics(trades)
    if trades.empty:
        return {
            "research_year": year,
            "model": model,
            "trades": 0,
            "win_rate": None,
            "expectancy_points": None,
            "expectancy_r": None,
            "profit_factor": None,
            "net_points": 0.0,
            "max_drawdown_points": 0.0,
            "average_mfe_points": None,
            "median_mfe_points": None,
            "average_mae_points": None,
            "median_mae_points": None,
            "tp1_hit_rate": None,
            "tp2_hit_rate": None,
            "tp3_hit_rate": None,
            "tp4_hit_rate": None,
            "stop_hit_rate": None,
            "average_hold_minutes": None,
        }

    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    return {
        "research_year": year,
        "model": model,
        "trades": int(len(trades)),
        "win_rate": float((pnl > 0).mean()),
        "expectancy_points": float(pnl.mean()),
        "expectancy_r": metrics.get("expectancy_r"),
        "profit_factor": profit_factor(trades),
        "net_points": float(pnl.sum()),
        "max_drawdown_points": max_drawdown_points(trades),
        "average_mfe_points": metrics.get("average_mfe_points"),
        "median_mfe_points": metrics.get("median_mfe_points"),
        "average_mae_points": metrics.get("average_mae_points"),
        "median_mae_points": metrics.get("median_mae_points"),
        "tp1_hit_rate": metrics.get("tp1_hit_rate"),
        "tp2_hit_rate": metrics.get("tp2_hit_rate"),
        "tp3_hit_rate": metrics.get("tp3_hit_rate"),
        "tp4_hit_rate": metrics.get("tp4_hit_rate"),
        "stop_hit_rate": metrics.get("stop_hit_rate"),
        "average_hold_minutes": metrics.get("average_hold_minutes"),
    }


def segmented_summary(
    year: int,
    model: str,
    trades: pd.DataFrame,
    dimension: str,
) -> list[dict]:
    if trades.empty:
        return []
    frame = trades.copy()
    if dimension == "setup_family":
        frame["setup_family"] = derive_setup_family(frame)
    if dimension not in frame.columns:
        return []

    rows: list[dict] = []
    for value, group in frame.groupby(dimension, sort=True, dropna=False):
        row = summarize_r7(year, model, group)
        row[dimension] = str(value)
        rows.append(row)
    return rows


def replay_year(
    year: int,
    *,
    batch_rows: int,
    archive: Path,
    output: Path,
) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    base_config = model_config(
        load_config(Path("config/strategy.yaml")),
        CANDIDATE_WEIGHTS["baseline"],
    )
    scored = parquet_replay(FEATURES[year], base_config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R7.0 PARITY GATE: {year} / untouched CONTROL =====", flush=True)
    control = run_backtest(scored, base_config)
    assert_frozen_70(control, frozen)
    print(
        f"EXACT FROZEN CONTROL PARITY PASSED: {len(frozen)} trades",
        flush=True,
    )

    candidate_input, gate_diagnostics = apply_continuation_displacement_gate(scored)
    candidate = run_backtest(candidate_input, base_config)

    year_dir = output / str(year)
    control_dir = year_dir / "control"
    candidate_dir = year_dir / "continuation_displacement"
    control_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    control.to_csv(control_dir / "trades.csv", index=False)
    candidate.to_csv(candidate_dir / "trades.csv", index=False)
    gate_diagnostics.to_csv(year_dir / "eligibility_gate_summary.csv", index=False)

    summaries = [
        summarize_r7(year, "CONTROL", control),
        summarize_r7(year, MODEL, candidate),
    ]
    pd.DataFrame(summaries).to_csv(output / f"summary_{year}.csv", index=False)

    direction_rows: list[dict] = []
    family_rows: list[dict] = []
    for model, trades in (("CONTROL", control), (MODEL, candidate)):
        direction_rows.extend(segmented_summary(year, model, trades, "direction"))
        family_rows.extend(segmented_summary(year, model, trades, "setup_family"))

    pd.DataFrame(direction_rows).to_csv(
        output / f"direction_summary_{year}.csv",
        index=False,
    )
    pd.DataFrame(family_rows).to_csv(
        output / f"setup_family_summary_{year}.csv",
        index=False,
    )

    (candidate_dir / "metrics.json").write_text(
        json.dumps(
            {
                "performance": summaries[1],
                "control": summaries[0],
                "single_change": (
                    "Existing continuation-proxy candidates require "
                    "same-direction recent displacement; reversal candidates unchanged."
                ),
                "setup_family_contract": (
                    "directional recent liquidity sweep => reversal; "
                    "otherwise continuation proxy"
                ),
                "gate_diagnostics": gate_diagnostics.to_dict(orient="records"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    c = summaries[0]
    x = summaries[1]
    print(
        f"R7.0 {year} CONTROL: {c['trades']} trades, "
        f"net={c['net_points']:.2f}, exp={c['expectancy_points']:.4f}, "
        f"PF={c['profit_factor']:.4f}, DD={c['max_drawdown_points']:.2f}",
        flush=True,
    )
    print(
        f"R7.0 {year} {MODEL}: {x['trades']} trades, "
        f"net={x['net_points']:.2f}, exp={x['expectancy_points']:.4f}, "
        f"PF={x['profit_factor']:.4f}, DD={x['max_drawdown_points']:.2f}",
        flush=True,
    )
    print(f"Saved R7.0 {year} outputs under {output}", flush=True)

    del scored, candidate_input
    gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int, choices=YEARS)
    parser.add_argument("--batch-rows", type=int, default=5000)
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("research-archive/R4-05"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R7_continuation_displacement",
    )
    args = parser.parse_args()

    if not (100 <= args.batch_rows <= 20000):
        parser.error("--batch-rows must be between 100 and 20000")

    replay_year(
        args.year,
        batch_rows=args.batch_rows,
        archive=args.archive,
        output=args.output_dir,
    )


if __name__ == "__main__":
    main()
