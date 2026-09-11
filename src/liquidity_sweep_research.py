"""EXP-007 liquidity-sweep diagnostics from existing trade ledgers + scored features.

Diagnostic only. No historical pipeline stages or strategy rules are rerun/changed.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from directional_research import _metrics, _score_band, validate_ledger
from setup_family_research import derive_setup_family


class LiquiditySweepResearchError(RuntimeError):
    pass


REQUIRED_FEATURES = {
    "timestamp",
    "buy_side_liquidity_sweep",
    "sell_side_liquidity_sweep",
    "buy_side_sweep_source",
    "sell_side_sweep_source",
    "buy_side_sweep_level",
    "sell_side_sweep_level",
    "high",
    "low",
}

CONFIRMATION_COLUMNS = {
    "long": {
        "displacement": ("bullish_displacement", "recent_bullish_displacement"),
        "mss": ("bullish_mss", "recent_bullish_mss"),
        "choch": ("bullish_choch", "recent_bullish_choch"),
        "bos": ("bullish_bos", "recent_bullish_bos"),
        "fvg": (
            "bullish_fvg_created",
            "bullish_fvg_retest_hold",
            "bullish_core_plus_fvg",
            "bullish_core_plus_fvg_retest",
        ),
    },
    "short": {
        "displacement": ("bearish_displacement", "recent_bearish_displacement"),
        "mss": ("bearish_mss", "recent_bearish_mss"),
        "choch": ("bearish_choch", "recent_bearish_choch"),
        "bos": ("bearish_bos", "recent_bearish_bos"),
        "fvg": (
            "bearish_fvg_created",
            "bearish_fvg_retest_hold",
            "bearish_core_plus_fvg",
            "bearish_core_plus_fvg_retest",
        ),
    },
}


def _truthy(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _window_any(frame: pd.DataFrame, columns: tuple[str, ...]) -> bool:
    for col in columns:
        if col not in frame.columns:
            continue
        if frame[col].map(_truthy).any():
            return True
    return False


def _event_for_trade(
    features: pd.DataFrame,
    pos: int,
    direction: str,
    lookback: int,
) -> tuple[int | None, str | None, str | None, float | None]:
    if direction == "long":
        event_col = "sell_side_liquidity_sweep"
        source_col = "sell_side_sweep_source"
        level_col = "sell_side_sweep_level"
        side = "sell_side"
    else:
        event_col = "buy_side_liquidity_sweep"
        source_col = "buy_side_sweep_source"
        level_col = "buy_side_sweep_level"
        side = "buy_side"

    start = max(0, pos - lookback + 1)
    window = features.iloc[start : pos + 1]

    for idx in range(len(window) - 1, -1, -1):
        row = window.iloc[idx]
        if not _truthy(row.get(event_col)):
            continue

        event_pos = start + idx

        source = row.get(source_col)
        source = None if source is None or pd.isna(source) else str(source)

        try:
            level = float(row.get(level_col))
            if not np.isfinite(level):
                level = None
        except (TypeError, ValueError):
            level = None

        return event_pos, side, source, level

    return None, None, None, None


def enrich_trades_with_sweep_context(
    ledger: pd.DataFrame,
    features: pd.DataFrame,
    *,
    lookback: int = 10,
) -> pd.DataFrame:
    validate_ledger(ledger)

    missing = REQUIRED_FEATURES - set(features.columns)
    if missing:
        raise LiquiditySweepResearchError(
            f"Feature artifact missing EXP-007 columns: {sorted(missing)}"
        )

    if lookback < 1:
        raise LiquiditySweepResearchError("lookback must be >= 1")

    f = features.copy()
    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True, errors="coerce")
    f = (
        f.dropna(subset=["timestamp"])
        .sort_values("timestamp", kind="stable")
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

    matched = []
    event_positions = []
    sweep_present = []
    sweep_side = []
    sweep_source = []
    sweep_level = []
    penetration = []
    bars_since = []

    displacement_after = []
    mss_after = []
    choch_after = []
    bos_after = []
    fvg_after = []

    for _, trade in out.iterrows():
        ts = trade["signal_time"]
        if pd.isna(ts) or ts not in lookup.index:
            matched.append(False)
            event_positions.append(None)
            sweep_present.append(False)
            sweep_side.append(None)
            sweep_source.append(None)
            sweep_level.append(None)
            penetration.append(None)
            bars_since.append(None)
            displacement_after.append(False)
            mss_after.append(False)
            choch_after.append(False)
            bos_after.append(False)
            fvg_after.append(False)
            continue

        matched.append(True)
        pos = int(lookup.loc[ts])
        direction = str(trade["direction"])

        event_pos, side, source, level = _event_for_trade(
            f, pos, direction, lookback
        )

        present = event_pos is not None
        sweep_present.append(present)
        event_positions.append(event_pos)
        sweep_side.append(side)
        sweep_source.append(source)
        sweep_level.append(level)

        if not present:
            penetration.append(None)
            bars_since.append(None)
            displacement_after.append(False)
            mss_after.append(False)
            choch_after.append(False)
            bos_after.append(False)
            fvg_after.append(False)
            continue

        event_row = f.iloc[event_pos]

        try:
            if direction == "long":
                dist = float(level) - float(event_row["low"])
            else:
                dist = float(event_row["high"]) - float(level)

            penetration.append(
                max(0.0, dist) if np.isfinite(dist) else None
            )
        except (TypeError, ValueError):
            penetration.append(None)

        bars_since.append(pos - event_pos)

        sequence = f.iloc[event_pos : pos + 1]
        definitions = CONFIRMATION_COLUMNS[direction]

        displacement_after.append(
            _window_any(sequence, definitions["displacement"])
        )
        mss_after.append(
            _window_any(sequence, definitions["mss"])
        )
        choch_after.append(
            _window_any(sequence, definitions["choch"])
        )
        bos_after.append(
            _window_any(sequence, definitions["bos"])
        )
        fvg_after.append(
            _window_any(sequence, definitions["fvg"])
        )

    out["feature_matched"] = matched
    out["sweep_event_position"] = event_positions
    out["sweep_present_exact"] = sweep_present
    out["sweep_side"] = sweep_side
    out["sweep_source"] = sweep_source
    out["sweep_level"] = sweep_level
    out["sweep_penetration_points"] = penetration
    out["bars_since_sweep"] = bars_since

    out["sweep_then_displacement"] = displacement_after
    out["sweep_then_mss"] = mss_after
    out["sweep_then_choch"] = choch_after
    out["sweep_then_bos"] = bos_after
    out["sweep_then_fvg"] = fvg_after

    # The production liquidity sweep contract itself requires a close
    # back through the level. Therefore "wick-only sweep reclaim" is not
    # a separate truthful category in these artifacts.
    out["sweep_requires_close_reclaim"] = out["sweep_present_exact"]

    return out


def _segment(df: pd.DataFrame, column: str) -> dict[str, dict[str, Any]]:
    if column not in df.columns:
        return {}

    values = df[column].where(df[column].notna(), "<missing>").astype(str)
    result = {}

    for value in sorted(values.unique()):
        result[value] = _metrics(df.loc[values == value])

    return result


def _year_segment(df: pd.DataFrame, column: str) -> dict[str, Any]:
    result = {}

    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]
        result[str(year)] = _segment(y, column)

    return result


def analyze_liquidity_sweeps(
    year_frames: dict[int, pd.DataFrame],
) -> dict[str, Any]:
    if set(year_frames) != {2023, 2024, 2025}:
        raise LiquiditySweepResearchError(
            "EXP-007 requires exactly 2023, 2024, and 2025"
        )

    frames = []
    for year, frame in sorted(year_frames.items()):
        f = frame.copy()
        f["year"] = year
        frames.append(f)

    df = pd.concat(frames, ignore_index=True)

    matched = int(df["feature_matched"].sum())

    result: dict[str, Any] = {
        "experiment_id": "EXP-007_liquidity-sweep",
        "coverage": {
            "total_trades": int(len(df)),
            "matched": matched,
            "match_rate": matched / len(df),
        },
        "overall": _metrics(df),
        "sweep_present_vs_absent": _segment(
            df, "sweep_present_exact"
        ),
        "by_year": _year_segment(
            df, "sweep_present_exact"
        ),
        "by_direction": {},
        "by_setup_family": {},
        "by_score_band": {},
        "sweep_side": _segment(
            df[df["sweep_present_exact"]], "sweep_side"
        ),
        "sweep_source": _segment(
            df[df["sweep_present_exact"]], "sweep_source"
        ),
        "confirmations": {},
        "capabilities": {
            "close_reclaim_required_by_sweep_definition": True,
            "wick_only_reclaim_category_available": False,
            "reclaim_speed_separate_from_sweep_bar": False,
            "note": (
                "The production liquidity-sweep definition requires "
                "price to penetrate the level and close back through it "
                "on the sweep bar. A separate wick-only reclaim class "
                "would therefore be invented and is not reported."
            ),
        },
    }

    for direction in ("long", "short"):
        d = df[df["direction"] == direction]
        result["by_direction"][direction] = _segment(
            d, "sweep_present_exact"
        )

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]
        result["by_setup_family"][family] = _segment(
            g, "sweep_present_exact"
        )

    for band in sorted(df["score_band"].dropna().unique()):
        g = df[df["score_band"] == band]
        result["by_score_band"][band] = _segment(
            g, "sweep_present_exact"
        )

    swept = df[df["sweep_present_exact"]].copy()

    for column in (
        "sweep_then_displacement",
        "sweep_then_mss",
        "sweep_then_choch",
        "sweep_then_bos",
        "sweep_then_fvg",
    ):
        result["confirmations"][column] = _segment(
            swept, column
        )

    penetration = pd.to_numeric(
        swept["sweep_penetration_points"], errors="coerce"
    )

    if penetration.notna().sum() >= 20:
        try:
            swept["penetration_bucket"] = pd.qcut(
                penetration,
                4,
                duplicates="drop",
            ).astype(str)
            result["penetration_quartiles"] = _segment(
                swept, "penetration_bucket"
            )
        except ValueError:
            result["penetration_quartiles"] = {}
    else:
        result["penetration_quartiles"] = {}

    bars = pd.to_numeric(
        swept["bars_since_sweep"], errors="coerce"
    )

    if bars.notna().any():
        swept["sweep_recency"] = pd.cut(
            bars,
            bins=[-1, 0, 2, 5, 9, np.inf],
            labels=[
                "same_bar",
                "1-2_bars",
                "3-5_bars",
                "6-9_bars",
                "10+_bars",
            ],
        ).astype(str)
        result["sweep_recency"] = _segment(
            swept, "sweep_recency"
        )
    else:
        result["sweep_recency"] = {}

    return result


def metrics_frame(result: dict[str, Any]) -> pd.DataFrame:
    rows = []

    def add(section: str, values: dict[str, Any]):
        for key, metrics in values.items():
            if isinstance(metrics, dict) and "trades" in metrics:
                rows.append({
                    "section": section,
                    "value": key,
                    **metrics,
                })

    add(
        "sweep_present_vs_absent",
        result["sweep_present_vs_absent"],
    )
    add("sweep_side", result["sweep_side"])
    add("sweep_source", result["sweep_source"])
    add("penetration_quartile", result["penetration_quartiles"])
    add("sweep_recency", result["sweep_recency"])

    for name, values in result["confirmations"].items():
        add(name, values)

    for year, values in result["by_year"].items():
        add(f"year_{year}", values)

    for direction, values in result["by_direction"].items():
        add(f"direction_{direction}", values)

    for family, values in result["by_setup_family"].items():
        add(f"family_{family}", values)

    for band, values in result["by_score_band"].items():
        add(f"score_band_{band}", values)

    return pd.DataFrame(rows)


def markdown_report(
    result: dict[str, Any],
    ledger_paths: dict[int, str],
    feature_paths: dict[int, str],
) -> str:
    def num(v, digits=2):
        if v is None:
            return "—"
        try:
            if np.isnan(v):
                return "—"
            if np.isinf(v):
                return "∞"
        except TypeError:
            pass
        return f"{float(v):.{digits}f}"

    def pct(v):
        if v is None:
            return "—"
        return f"{100 * float(v):.1f}%"

    def row(label, m):
        return (
            f"| {label} | {m.get('trades',0)} | "
            f"{pct(m.get('win_rate'))} | "
            f"{num(m.get('expectancy_points'))} | "
            f"{num(m.get('expectancy_r'),3)} | "
            f"{num(m.get('profit_factor'))} | "
            f"{num(m.get('net_points'))} | "
            f"{pct(m.get('tp1_hit_rate'))} | "
            f"{pct(m.get('tp2_hit_rate'))} | "
            f"{pct(m.get('tp3_hit_rate'))} | "
            f"{pct(m.get('tp4_hit_rate'))} | "
            f"{pct(m.get('stop_rate'))} |"
        )

    header = (
        "| Segment | Trades | Win | Exp pts | Exp R | PF | "
        "Net pts | TP1 | TP2 | TP3 | TP4 | Stop |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    lines = [
        "# EXP-007 — Liquidity Sweep Contribution",
        "",
        "Diagnostic only. Existing baseline ledgers and scored feature artifacts only.",
        "",
        "## Coverage",
        "",
        (
            f"- Exact feature match: "
            f"**{result['coverage']['matched']}/"
            f"{result['coverage']['total_trades']} "
            f"({100*result['coverage']['match_rate']:.1f}%)**"
        ),
        "",
        "## Sweep present vs absent",
        "",
        header,
    ]

    for value, metrics in result["sweep_present_vs_absent"].items():
        lines.append(row(value, metrics))

    lines += ["", "## By year", ""]
    for year, values in result["by_year"].items():
        lines += [f"### {year}", "", header]
        for value, metrics in values.items():
            lines.append(row(value, metrics))
        lines.append("")

    lines += ["## By direction", ""]
    for direction, values in result["by_direction"].items():
        lines += [f"### {direction}", "", header]
        for value, metrics in values.items():
            lines.append(row(value, metrics))
        lines.append("")

    lines += ["## By setup family", ""]
    for family, values in result["by_setup_family"].items():
        lines += [f"### {family}", "", header]
        for value, metrics in values.items():
            lines.append(row(value, metrics))
        lines.append("")

    lines += ["## Sweep side", "", header]
    for value, metrics in result["sweep_side"].items():
        lines.append(row(value, metrics))

    lines += ["", "## Sweep source", "", header]
    for value, metrics in result["sweep_source"].items():
        lines.append(row(value, metrics))

    lines += ["", "## Confirmation after sweep", ""]
    for name, values in result["confirmations"].items():
        lines += [f"### {name}", "", header]
        for value, metrics in values.items():
            lines.append(row(value, metrics))
        lines.append("")

    lines += ["## Sweep penetration quartiles", "", header]
    for value, metrics in result["penetration_quartiles"].items():
        lines.append(row(value, metrics))

    lines += ["", "## Sweep recency", "", header]
    for value, metrics in result["sweep_recency"].items():
        lines.append(row(value, metrics))

    lines += [
        "",
        "## Score-band interaction",
        "",
    ]

    for band, values in result["by_score_band"].items():
        lines += [f"### {band}", "", header]
        for value, metrics in values.items():
            lines.append(row(value, metrics))
        lines.append("")

    lines += [
        "## Capability / definition notes",
        "",
        (
            "- Production liquidity sweep requires penetration and a "
            "**close back through the level on the sweep bar**."
        ),
        (
            "- Therefore a separate `wick-only reclaim sweep` category "
            "is not available and is not invented."
        ),
        (
            "- `bars_since_sweep` measures how recently the qualifying "
            "sweep occurred before the trade signal; it is not a separate "
            "reclaim-speed measurement."
        ),
        "",
        "## Inputs",
        "",
    ]

    for year in sorted(ledger_paths):
        lines.append(f"- {year} ledger: `{ledger_paths[year]}`")
        lines.append(f"- {year} features: `{feature_paths[year]}`")

    lines += [
        "",
        "## Research discipline",
        "",
        "- EXP-007 is diagnostic only.",
        "- No score weights, entries, stops, targets, or setup logic changed.",
        "- Small cells should be treated as exploratory.",
    ]

    return "\n".join(lines)
