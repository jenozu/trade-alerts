"""Ledger-only analysis for EXP-001 score-band baseline research.

This module deliberately never rebuilds signals or trades.  It measures the
already archived baseline trade ledgers, which keeps the experiment diagnostic
and preserves the three-year control set.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


SCORE_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("<50", -np.inf, 50.0),
    ("50-59", 50.0, 60.0),
    ("60-69", 60.0, 70.0),
    ("70-79", 70.0, 80.0),
    ("80-89", 80.0, 90.0),
    ("90-100", 90.0, 100.0000001),
)

REQUIRED_COLUMNS = {
    "direction", "raw_score", "net_result_points", "net_result_r",
    "tp1_hit", "tp2_hit", "tp3_hit", "tp4_hit", "stop_hit",
    "mfe_points", "mae_points",
}


class ScoreBandResearchError(RuntimeError):
    """Raised when a trade ledger cannot support a defensible EXP-001 run."""


def assign_score_bucket(score: float) -> str:
    for label, lower, upper in SCORE_BUCKETS:
        if lower <= score < upper:
            return label
    raise ScoreBandResearchError(f"raw_score {score!r} falls outside supported 0-100 buckets")


def validate_ledger(trades: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(trades.columns)
    if missing:
        raise ScoreBandResearchError(f"Trade ledger is missing required columns: {sorted(missing)}")
    if trades.empty:
        raise ScoreBandResearchError("Trade ledger is empty.")
    invalid_directions = set(trades["direction"].dropna().astype(str).str.lower()) - {"long", "short"}
    if invalid_directions:
        raise ScoreBandResearchError(f"Unsupported directions: {sorted(invalid_directions)}")
    scores = pd.to_numeric(trades["raw_score"], errors="coerce")
    if scores.isna().any() or ((scores < 0) | (scores > 100)).any():
        raise ScoreBandResearchError("raw_score must be present and between 0 and 100 for every trade.")


def _metrics(group: pd.DataFrame) -> dict[str, Any]:
    if group.empty:
        return {"trades": 0}
    result = pd.to_numeric(group["net_result_points"], errors="coerce")
    winners = result[result > 0]
    losers = result[result < 0]
    gross_loss = abs(float(losers.sum()))
    pf = float(winners.sum()) / gross_loss if gross_loss else np.inf
    payload: dict[str, Any] = {
        "trades": int(len(group)),
        "win_rate": float((result > 0).mean()),
        "expectancy_points": float(result.mean()),
        "expectancy_r": float(pd.to_numeric(group["net_result_r"], errors="coerce").mean()),
        "profit_factor": float(pf),
        "net_points": float(result.sum()),
        "tp1_hit_rate": float(group["tp1_hit"].astype(bool).mean()),
        "tp2_hit_rate": float(group["tp2_hit"].astype(bool).mean()),
        "tp3_hit_rate": float(group["tp3_hit"].astype(bool).mean()),
        "tp4_hit_rate": float(group["tp4_hit"].astype(bool).mean()),
        "stop_rate": float(group["stop_hit"].astype(bool).mean()),
        "average_mfe": float(pd.to_numeric(group["mfe_points"], errors="coerce").mean()),
        "average_mae": float(pd.to_numeric(group["mae_points"], errors="coerce").mean()),
    }
    if "minutes_held" in group.columns:
        payload["average_hold_minutes"] = float(pd.to_numeric(group["minutes_held"], errors="coerce").mean())
    return payload


def analyze_score_bands(year_ledgers: dict[int, pd.DataFrame]) -> dict[str, Any]:
    """Return machine-readable EXP-001 metrics using fixed score buckets."""
    if not year_ledgers:
        raise ScoreBandResearchError("At least one year ledger is required.")
    prepared: list[pd.DataFrame] = []
    for year, ledger in sorted(year_ledgers.items()):
        validate_ledger(ledger)
        frame = ledger.copy()
        frame["year"] = int(year)
        frame["direction"] = frame["direction"].astype(str).str.lower()
        frame["score_bucket"] = pd.to_numeric(frame["raw_score"]).map(assign_score_bucket)
        prepared.append(frame)
    all_trades = pd.concat(prepared, ignore_index=True)

    bands: list[dict[str, Any]] = []
    for label, _, _ in SCORE_BUCKETS:
        group = all_trades[all_trades["score_bucket"] == label]
        if group.empty:
            continue
        band = {"score_bucket": label, "overall": _metrics(group)}
        band["by_year"] = {str(year): _metrics(group[group["year"] == year]) for year in sorted(year_ledgers)}
        band["by_direction"] = {
            direction: _metrics(group[group["direction"] == direction])
            for direction in ("long", "short")
        }
        bands.append(band)

    eligible = [band for band in bands if band["overall"]["trades"] >= 30]
    expectancy = [band["overall"]["expectancy_points"] for band in eligible]
    pf = [band["overall"]["profit_factor"] for band in eligible]
    monotonic = {
        "minimum_trades_per_band": 30,
        "eligible_bands": [band["score_bucket"] for band in eligible],
        "expectancy_non_decreasing": all(a <= b for a, b in zip(expectancy, expectancy[1:])),
        "profit_factor_non_decreasing": all(a <= b for a, b in zip(pf, pf[1:])),
        "conclusion": (
            "insufficient eligible score bands" if len(eligible) < 3 else
            "monotonic on both expectancy and profit factor" if all(a <= b for a, b in zip(expectancy, expectancy[1:])) and all(a <= b for a, b in zip(pf, pf[1:])) else
            "not monotonic on both primary measures"
        ),
    }
    return {
        "experiment_id": "EXP-001_score-bands-baseline",
        "years": sorted(int(year) for year in year_ledgers),
        "overall": _metrics(all_trades),
        "bands": bands,
        "monotonicity": monotonic,
        "sample_size_note": "Bands with fewer than 30 trades are exploratory, not proof.",
    }


def markdown_report(result: dict[str, Any], *, ledger_paths: dict[int, str]) -> str:
    def pct(value: Any) -> str:
        return "—" if value is None or pd.isna(value) else f"{float(value) * 100:.1f}%"
    def num(value: Any, digits: int = 2) -> str:
        if value is None or pd.isna(value): return "—"
        if np.isinf(value): return "∞"
        return f"{float(value):.{digits}f}"
    def row(label: str, metric: dict[str, Any]) -> str:
        return "| " + " | ".join([label, str(metric.get("trades", 0)), pct(metric.get("win_rate")), num(metric.get("expectancy_points")), num(metric.get("expectancy_r"), 3), num(metric.get("profit_factor")), num(metric.get("net_points")), pct(metric.get("tp1_hit_rate")), pct(metric.get("tp2_hit_rate")), pct(metric.get("tp3_hit_rate")), pct(metric.get("tp4_hit_rate")), pct(metric.get("stop_rate")), num(metric.get("average_mfe")), num(metric.get("average_mae")), num(metric.get("average_hold_minutes"))]) + " |"
    header = "| Band | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = ["# EXP-001 — Score-band baseline analysis", "", "## Method", "", "This is a ledger-only diagnostic. It did not rerun the feature or backtest pipeline and did not change score weights, entries, stops, or targets.", "", "## Inputs", ""]
    lines += [f"- {year}: `{ledger_paths[year]}`" for year in sorted(ledger_paths)]
    lines += ["", "## Overall", "", header, row("All scored trades", result["overall"]), "", "## Score buckets", "", header]
    lines += [row(band["score_bucket"], band["overall"]) for band in result["bands"]]
    for band in result["bands"]:
        lines += ["", f"### {band['score_bucket']} segmentation", "", "| Segment | Trades | Win rate | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE | Avg hold min |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        lines += [row(year, metrics) for year, metrics in band["by_year"].items()]
        lines += [row(direction, metrics) for direction, metrics in band["by_direction"].items()]
    mono = result["monotonicity"]
    lines += ["", "## Monotonicity and interpretation", "", f"- Eligible bands (at least {mono['minimum_trades_per_band']} trades): {', '.join(mono['eligible_bands']) or 'none'}.", f"- Expectancy non-decreasing: **{mono['expectancy_non_decreasing']}**.", f"- Profit factor non-decreasing: **{mono['profit_factor_non_decreasing']}**.", f"- Result: **{mono['conclusion']}**.", f"- Sample-size rule: {result['sample_size_note']}", "", "## Decision", "", "Diagnostic only — do not change score weights from this report. The raw 0–100 confluence score remains an ordinal ranking signal, not a win probability; probability calibration requires a separate validated model.", ""]
    return "\n".join(lines)
