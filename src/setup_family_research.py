"""Ledger-only diagnostics for EXP-003 setup-family research.

The historical backtest ledger does not persist an explicit setup-family field.
For current baseline ledgers, family is derived from the same directional sweep
context used by the production planner:

    directional opposite-side recent sweep -> reversal
    otherwise                              -> continuation

The backtest ledger's ``liquidity_sweep`` field is exactly that directional
recent sweep context. The liquidity rolling flag includes the current bar, and
production reversal sequences are initiated by the same sweep context. This
module refuses to classify if that field is absent rather than inventing a
proxy.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from directional_research import (
    SCORE_BUCKETS,
    _alignment,
    _metrics,
    _numeric_summary,
    _score_band,
    _segments,
    _time_bucket,
    validate_ledger,
)

FAMILIES = ("reversal", "continuation")
NUMERIC_CONTEXT = ("snr_1m", "snr_5m", "snr_15m", "rvol_rolling", "rvol_time_of_day")
OPTIONAL_CONTEXT = (
    "displacement",
    "structure_shift",
    "fvg_context",
    "htf_bias",
    "dol_direction",
    "level_type",
    "trigger_level_type",
    "liquidity_level_type",
    "volatility_regime",
)


class SetupFamilyResearchError(RuntimeError):
    pass


def _truth_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    text = series.astype(str).str.strip().str.lower()
    mapped = text.map({
        "true": True, "1": True, "yes": True, "y": True,
        "false": False, "0": False, "no": False, "n": False,
    })
    if mapped.isna().any():
        bad = sorted(text[mapped.isna()].dropna().unique().tolist())
        raise SetupFamilyResearchError(
            "liquidity_sweep must be boolean-like for deterministic family derivation; "
            f"unsupported values: {bad[:10]}"
        )
    return mapped.astype(bool)


def derive_setup_family(df: pd.DataFrame) -> pd.Series:
    """Derive the planner-equivalent family from the archived trade ledger."""
    if "setup_family" in df.columns:
        family = df["setup_family"].astype(str).str.strip().str.lower()
        allowed = set(family.dropna().unique())
        if not allowed <= set(FAMILIES):
            raise SetupFamilyResearchError(
                f"Unsupported explicit setup_family values: {sorted(allowed-set(FAMILIES))}"
            )
        return family
    if "liquidity_sweep" not in df.columns:
        raise SetupFamilyResearchError(
            "Trade ledger has no explicit setup_family and lacks liquidity_sweep, "
            "so reversal vs continuation cannot be derived truthfully."
        )
    sweep = _truth_series(df["liquidity_sweep"])
    return pd.Series(np.where(sweep, "reversal", "continuation"), index=df.index)


def _family_metrics(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {family: _metrics(df[df.setup_family == family]) for family in FAMILIES}


def _family_segments(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if column not in df.columns:
        return []
    values = df[column].where(df[column].notna(), "<missing>").astype(str)
    rows: list[dict[str, Any]] = []
    for value in sorted(values.unique()):
        mask = values == value
        rows.append({
            "value": value,
            **{family: _metrics(df[mask & (df.setup_family == family)]) for family in FAMILIES},
        })
    return rows


def _numeric_by_family(df: pd.DataFrame, column: str) -> dict[str, Any] | None:
    if column not in df.columns:
        return None
    x = pd.to_numeric(df[column], errors="coerce")
    if not x.notna().any():
        return None
    summary: dict[str, Any] = {"by_family": {}}
    for family in FAMILIES:
        v = x[df.setup_family == family].dropna()
        summary["by_family"][family] = {
            "count": int(len(v)),
            "mean": float(v.mean()) if len(v) else None,
            "median": float(v.median()) if len(v) else None,
            "q25": float(v.quantile(.25)) if len(v) else None,
            "q75": float(v.quantile(.75)) if len(v) else None,
        }
    if x.nunique(dropna=True) >= 4:
        try:
            tmp = df.copy()
            tmp["numeric_bucket"] = pd.qcut(x, 4, duplicates="drop").astype(str)
            summary["quartile_performance"] = _family_segments(tmp, "numeric_bucket")
        except ValueError:
            summary["quartile_performance"] = []
    else:
        summary["quartile_performance"] = []
    return summary


def analyze_setup_families(year_ledgers: dict[int, pd.DataFrame]) -> dict[str, Any]:
    if set(year_ledgers) != {2023, 2024, 2025}:
        raise SetupFamilyResearchError(
            "EXP-003 control set must contain exactly 2023, 2024, and 2025 ledgers."
        )

    frames: list[pd.DataFrame] = []
    explicit_family_years: list[int] = []
    derived_family_years: list[int] = []
    for year, ledger in sorted(year_ledgers.items()):
        validate_ledger(ledger)
        frame = ledger.copy()
        frame["direction"] = frame.direction.astype(str).str.lower()
        if "setup_family" in frame.columns:
            explicit_family_years.append(year)
        else:
            derived_family_years.append(year)
        frame["setup_family"] = derive_setup_family(frame)
        frame["year"] = year
        frame["score_band_exp003"] = pd.to_numeric(frame.raw_score).map(_score_band)
        frames.append(frame)

    all_ = pd.concat(frames, ignore_index=True)
    time_bucket = _time_bucket(all_)
    if time_bucket is not None:
        all_["time_bucket_exp003"] = time_bucket

    overall = _family_metrics(all_)
    by_year = {
        str(year): _family_metrics(all_[all_.year == year])
        for year in sorted(year_ledgers)
    }
    by_direction = {
        direction: _family_metrics(all_[all_.direction == direction])
        for direction in ("long", "short")
    }
    score_bands = {
        label: _family_metrics(all_[all_.score_band_exp003 == label])
        for label, _, _ in SCORE_BUCKETS
        if (all_.score_band_exp003 == label).any()
    }
    score_distribution: dict[str, Any] = {}
    for family in FAMILIES:
        group = all_[all_.setup_family == family]
        score = pd.to_numeric(group.raw_score, errors="coerce")
        score_distribution[family] = {
            "count": int(len(group)),
            "mean": float(score.mean()),
            "median": float(score.median()),
            "std": float(score.std(ddof=1)) if len(group) > 1 else None,
            "band_counts": group.score_band_exp003.value_counts().sort_index().to_dict(),
        }

    contexts: dict[str, Any] = {}
    for column in OPTIONAL_CONTEXT:
        if column in all_.columns:
            contexts[column] = _family_segments(all_, column)
    alignment_rows = _alignment(all_)
    if alignment_rows:
        # _alignment returns long/short metrics, so recreate family segmentation
        bias = all_.htf_bias.astype(str).str.lower()
        direction = all_.direction
        status = np.where(
            ((direction == "long") & bias.str.contains("bull|long", regex=True))
            | ((direction == "short") & bias.str.contains("bear|short", regex=True)),
            "aligned",
            np.where(
                bias.str.contains("neutral|unknown|none|nan", regex=True),
                "neutral/unknown",
                "conflicting",
            ),
        )
        tmp = all_.copy()
        tmp["htf_alignment_exp003"] = status
        contexts["htf_alignment"] = _family_segments(tmp, "htf_alignment_exp003")
    if "time_bucket_exp003" in all_.columns:
        contexts["time_bucket"] = _family_segments(all_, "time_bucket_exp003")

    numeric = {
        column: item
        for column in NUMERIC_CONTEXT
        if (item := _numeric_by_family(all_, column)) is not None
    }

    capabilities = {
        "explicit_setup_family": bool(explicit_family_years),
        "family_derivation": "explicit setup_family when present; otherwise planner-equivalent directional liquidity_sweep context",
        "level_type_available": any(c in all_.columns for c in ("level_type", "trigger_level_type", "liquidity_level_type")),
        "volatility_regime_available": "volatility_regime" in all_.columns,
        "acceptance_available": any("accept" in c.lower() for c in all_.columns),
        "retest_quality_available": any("retest" in c.lower() for c in all_.columns),
        "bos_separate_available": any(c in all_.columns for c in ("bullish_bos", "bearish_bos", "recent_bullish_bos", "recent_bearish_bos")),
        "mss_choch_separate_available": any("mss" in c.lower() or "choch" in c.lower() for c in all_.columns),
    }

    return {
        "experiment_id": "EXP-003_setup-family-comparison",
        "years": [2023, 2024, 2025],
        "classification": {
            "explicit_family_years": explicit_family_years,
            "derived_family_years": derived_family_years,
            "rule": "reversal if directional liquidity_sweep context is true; otherwise continuation",
            "source_contract": "trade_planner reversal_context / backtest TradeResult.liquidity_sweep",
        },
        "overall": overall,
        "by_year": by_year,
        "by_direction": by_direction,
        "score_distribution": score_distribution,
        "score_bands": score_bands,
        "contexts": contexts,
        "numeric_context": numeric,
        "capabilities": capabilities,
        "sample_size_note": "Treat categorical cells under 30 trades and numeric quartiles under 30 trades as exploratory. Family-level conclusions must also be checked across years and directions.",
    }


def flatten_tables(result: dict[str, Any]) -> dict[str, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for family, metrics in result["overall"].items():
        rows.append({"segment": "overall", "value": family, "setup_family": family, **metrics})
    for year, families in result["by_year"].items():
        for family, metrics in families.items():
            rows.append({"segment": "year", "value": year, "setup_family": family, **metrics})
    for direction, families in result["by_direction"].items():
        for family, metrics in families.items():
            rows.append({"segment": "direction", "value": direction, "setup_family": family, **metrics})
    for band, families in result["score_bands"].items():
        for family, metrics in families.items():
            rows.append({"segment": "score_band", "value": band, "setup_family": family, **metrics})
    for context, values in result["contexts"].items():
        for item in values:
            for family in FAMILIES:
                rows.append({"segment": context, "value": item["value"], "setup_family": family, **item[family]})
    return {"setup_family_metrics": pd.DataFrame(rows)}


def markdown_report(result: dict[str, Any], ledger_paths: dict[int, str]) -> str:
    def n(value: Any, digits: int = 2) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "—"
        if isinstance(value, float) and np.isinf(value):
            return "∞"
        return f"{float(value):.{digits}f}"

    def pct(value: Any) -> str:
        return "—" if value is None else f"{100 * float(value):.1f}%"

    def row(label: str, metrics: dict[str, Any]) -> str:
        return (
            f"| {label} | {metrics.get('trades', 0)} | {pct(metrics.get('win_rate'))} | "
            f"{n(metrics.get('expectancy_points'))} | {n(metrics.get('expectancy_r'), 3)} | "
            f"{n(metrics.get('profit_factor'))} | {n(metrics.get('net_points'))} | "
            f"{pct(metrics.get('tp1_hit_rate'))} | {pct(metrics.get('tp2_hit_rate'))} | "
            f"{pct(metrics.get('tp3_hit_rate'))} | {pct(metrics.get('tp4_hit_rate'))} | "
            f"{pct(metrics.get('stop_rate'))} | {n(metrics.get('average_mfe'))} | "
            f"{n(metrics.get('median_mfe'))} | {n(metrics.get('average_mae'))} | "
            f"{n(metrics.get('median_mae'))} | {n(metrics.get('average_hold_minutes'))} |"
        )

    header = "| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Med MFE | Avg MAE | Med MAE | Avg hold |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [
        "# EXP-003 — Setup-Family Comparison",
        "",
        "Ledger-only diagnostic. No historical pipeline rerun and no strategy/scoring changes.",
        "",
        "## Classification contract",
        "",
        f"- Rule: `{result['classification']['rule']}`.",
        "- This is the existing production planner family-selection contract, not a new research heuristic.",
        f"- Explicit-family years: {result['classification']['explicit_family_years'] or 'none'}.",
        f"- Ledger-derived years: {result['classification']['derived_family_years'] or 'none'}.",
        "",
        "## Inputs",
        "",
    ]
    lines += [f"- {year}: `{path}`" for year, path in sorted(ledger_paths.items())]
    lines += ["", "## Overall", "", header]
    for family in FAMILIES:
        lines.append(row(family.upper(), result["overall"][family]))

    lines += ["", "## Year-by-year", "", header]
    for year, families in result["by_year"].items():
        for family in FAMILIES:
            lines.append(row(f"{year} {family}", families[family]))

    lines += ["", "## Long vs short within family", "", header]
    for direction, families in result["by_direction"].items():
        for family in FAMILIES:
            lines.append(row(f"{direction.upper()} {family}", families[family]))

    lines += ["", "## Score distribution", ""]
    for family, summary in result["score_distribution"].items():
        lines.append(
            f"- {family}: n={summary['count']}, mean={n(summary['mean'])}, median={n(summary['median'])}, "
            f"std={n(summary['std'])}, bands={summary['band_counts']}."
        )

    lines += ["", "## Score-band performance", "", header]
    for band, families in result["score_bands"].items():
        for family in FAMILIES:
            lines.append(row(f"{band} {family}", families[family]))

    lines += ["", "## Context diagnostics", ""]
    for context, items in result["contexts"].items():
        lines += [f"### {context}", ""]
        for item in items:
            r = item["reversal"]
            c = item["continuation"]
            lines.append(
                f"- `{item['value']}` — reversal n={r.get('trades',0)}, exp={n(r.get('expectancy_points'))}, PF={n(r.get('profit_factor'))}; "
                f"continuation n={c.get('trades',0)}, exp={n(c.get('expectancy_points'))}, PF={n(c.get('profit_factor'))}."
            )
        lines.append("")

    lines += ["## SNR / RVOL diagnostics", ""]
    for column, item in result["numeric_context"].items():
        by = item["by_family"]
        lines.append(
            f"- {column}: reversal mean {n(by['reversal']['mean'])} / median {n(by['reversal']['median'])} (n={by['reversal']['count']}); "
            f"continuation mean {n(by['continuation']['mean'])} / median {n(by['continuation']['median'])} (n={by['continuation']['count']})."
        )

    cap = result["capabilities"]
    lines += [
        "",
        "## Capability / limitation flags",
        "",
        f"- Level type available in ledger: **{cap['level_type_available']}**.",
        f"- Explicit volatility regime available in ledger: **{cap['volatility_regime_available']}**.",
        f"- Acceptance detail available in ledger: **{cap['acceptance_available']}**.",
        f"- Retest-quality detail available in ledger: **{cap['retest_quality_available']}**.",
        f"- BOS separately available in ledger: **{cap['bos_separate_available']}**.",
        f"- MSS/CHOCH separately available in ledger: **{cap['mss_choch_separate_available']}**.",
        "- If these are false, EXP-003 must not invent those sub-classifications; later component experiments can use richer scored/structure artifacts.",
        "",
        "## Sample-size discipline",
        "",
        f"- {result['sample_size_note']}",
        "",
    ]
    return "\n".join(lines)
