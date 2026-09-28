#!/usr/bin/env python3
"""R4.6 descriptive threshold audit of immutable R4.5 executed-trade ledgers.

IMPORTANT: Filtering an executed-trade ledger cannot simulate changing the
entry threshold: removed trades may free capital or change position overlap,
changing which subsequent signals execute. Counts are percentages of already
executed trades, NOT percentages of all opportunities. Do not rank or deploy
thresholds from this audit. No trades or historical features are regenerated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

YEARS = (2023, 2024, 2025)
MODELS = (
    "baseline", "candidate_conservative",
    "candidate_evidence_tilt", "candidate_redundancy_reduced",
)
THRESHOLDS = (60, 65, 70, 75, 80, 85)
REQUIRED = {
    "raw_score", "net_result_points", "net_result_r",
    "tp1_hit", "tp2_hit", "tp3_hit", "tp4_hit", "stop_hit",
    "direction", "session_date",
}


def load_ledgers(root: Path):
    frames = []
    for year in YEARS:
        for model in MODELS:
            path = root / str(year) / model / "trades.csv"
            if not path.is_file():
                raise FileNotFoundError(path)
            frame = pd.read_csv(path)
            missing = REQUIRED - set(frame.columns)
            if missing:
                raise ValueError(f"{path}: missing columns {sorted(missing)}")
            frame["research_year"] = year
            frame["model"] = model
            if frame[list(REQUIRED)].isna().any().any():
                # Blank descriptive RVOL and other optional fields are
                # permitted, but never silently fill missing core metrics.
                raise ValueError(f"{path}: missing core trade fields")
            frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def cohort_metrics(frame: pd.DataFrame, denominator: int):
    n = len(frame)
    if not n:
        return dict(
            trades=0, executed_trade_retention=0.0,
            net_points=0.0, expectancy_points=None, expectancy_r=None,
            profit_factor=None, max_loss_run_points=None,
            tp1_hit_rate=None, tp2_hit_rate=None,
            tp3_hit_rate=None, tp4_hit_rate=None, stop_hit_rate=None,
        )
    pnl = pd.to_numeric(frame["net_result_points"], errors="raise")
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    # This hypothetical *subsequence* drawdown is a descriptive statistic,
    # not the drawdown of a newly simulated higher-threshold strategy.
    equity = pnl.cumsum().to_numpy(dtype=float)
    drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return dict(
        trades=n,
        executed_trade_retention=round(n / denominator, 6) if denominator else None,
        net_points=round(float(pnl.sum()), 4),
        expectancy_points=round(float(pnl.mean()), 6),
        expectancy_r=round(float(frame["net_result_r"].mean()), 6),
        profit_factor=(
            round(float(gross_profit / gross_loss), 6) if gross_loss > 0
            else None
        ),
        max_loss_run_points=round(float(drawdown.max()), 4),
        **{
            f"{col}_rate": round(float(frame[col].astype(bool).mean()), 6)
            for col in ("tp1_hit", "tp2_hit", "tp3_hit", "tp4_hit", "stop_hit")
        },
    )


def analyze(frame: pd.DataFrame):
    output = []
    for model in MODELS:
        for year in YEARS:
            one = frame[
                (frame["model"] == model)
                & (frame["research_year"] == year)
            ].sort_values("entry_time", kind="stable")
            n = len(one)
            for threshold in THRESHOLDS:
                qualifying = one.loc[one["raw_score"] >= threshold]
                output.append({
                    "model": model, "research_year": year,
                    "threshold": threshold, "scope": "single_year",
                    **cohort_metrics(qualifying, n),
                })
        pooled = frame.loc[frame["model"] == model].sort_values(
            ["research_year", "entry_time"], kind="stable"
        )
        for threshold in THRESHOLDS:
            qualifying = pooled.loc[pooled["raw_score"] >= threshold]
            output.append({
                "model": model, "research_year": "all",
                "threshold": threshold, "scope": "pooled",
                **cohort_metrics(qualifying, len(pooled)),
            })
    return pd.DataFrame(output)


def build_report(data: pd.DataFrame, ledgers: pd.DataFrame) -> str:
    pooled = data[data["scope"] == "pooled"]
    per_year = data[data["scope"] == "single_year"]
    lines = [
        "# R4.6 — Descriptive Score-Threshold Diagnostics",
        "",
        "## Scope and interpretation",
        "",
        "Existing **executed trades only**, from independently verified R4.5 ledgers.",
        "No score weights or production settings have been changed.",
        "Filtering historical trades does **not** backtest a new threshold:",
        "a changed threshold can change which later signals become executable.",
        "`executed_trade_retention` is relative to the model's historical",
        "executed trades, **not** all generated signals or market opportunities.",
        "`max_loss_run_points` is a descriptive drawdown of a filtered",
        "subsequence, **not** simulated strategy drawdown.",
        "",
        "## Samples",
        "",
    ]
    counts = ledgers.groupby(["research_year", "model"]).size().rename(
        "executed_trades"
    ).reset_index()
    lines.extend(["```", counts.to_string(index=False), "```", ""])
    lines.extend(["## Pooled threshold cohorts", "", "```",
                  pooled[[
                      "model", "threshold", "trades",
                      "executed_trade_retention", "expectancy_points",
                      "profit_factor", "net_points", "stop_hit_rate",
                  ]].to_string(index=False), "```", ""])
    lines.extend(["## Individual research-year cohorts", "", "```",
                  per_year[[
                      "model", "research_year", "threshold", "trades",
                      "executed_trade_retention", "expectancy_points",
                      "profit_factor", "net_points", "stop_hit_rate",
                  ]].to_string(index=False), "```", ""])
    lines.extend([
        "## Outstanding calibration requirements",
        "",
        "- Re-simulate each candidate threshold against the **full scored signal",
        "  sequence**, including rejected candidates, for actual trade counts,",
        "  position overlap and path-dependent drawdown.",
        "- Evaluate stability by year and a genuinely untouched validation period.",
        "- Setup-family breakdown is **not available** in these R4.5 ledgers:",
        "  no `setup_family` column was recorded. Do not infer family from",
        "  direction or score band; produce it in a separately validated replay.",
        "- Analyze stop_hit using the recorded boolean; the earlier",
        "  consolidated summary's `stop_rate` was missing, not zero.",
        "- Evaluate threshold bands with adequate samples and reject",
        "  overfit-looking differences rather than selecting a pooled maximum.",
        "- Research-year labels refer to existing archive partitions, which",
        "  may begin in October of the previous calendar year.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, default=Path("research-archive/R4-05")
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/reports/R4-06_threshold_diagnostics"),
    )
    a = parser.parse_args()
    ledger = load_ledgers(a.archive)
    table = analyze(ledger)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(a.output_dir / "threshold_cohorts.csv", index=False)
    (a.output_dir / "R4-06_Threshold-Diagnostics.md").write_text(
        build_report(table, ledger) + "\n"
    )
    (a.output_dir / "run_metadata.json").write_text(
        json.dumps({
            "source": str(a.archive),
            "rows": len(ledger),
            "models": list(MODELS),
            "years": list(YEARS),
            "thresholds": list(THRESHOLDS),
            "descriptive_only": True,
            "full_signal_replay_required": True,
        }, indent=2) + "\n"
    )
    print(table[table.scope == "pooled"][
        ["model", "threshold", "trades", "expectancy_points",
         "profit_factor", "stop_hit_rate"]
    ].to_string(index=False))
    print(f"R4.6 descriptive diagnostic saved to {a.output_dir}", flush=True)


if __name__ == "__main__":
    main()
