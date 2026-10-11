#!/usr/bin/env python3
"""Read-only Pine vs canonical Python MSS/FVG event audit on matching 1m bars.

Inputs are TradingView's *chart data* CSV (including plotted Data Window
series), not the Strategy Report's trade-list CSV. Derivation imports the
unchanged canonical src/swings.py, src/structure.py, src/fvg.py on main.

By default Python events are derived from exactly the same chart OHLC bars.
Optionally --reference-bars supplies independently collected MNQ 1m bars,
with a strict UTC + OHLC parity gate before comparing event flags.

This script does not evaluate event ordering/linked setup families, broker
fills, profitability or live execution.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
PINE_FIELDS = {
    "bullish_mss": "Bullish MSS proxy",
    "bearish_mss": "Bearish MSS proxy",
    "bullish_fvg_created": "Bullish FVG created",
    "bearish_fvg_created": "Bearish FVG created",
}
OHLC = ("open", "high", "low", "close")


class AuditInputError(ValueError):
    """Fail closed rather than silently align unlike data."""


def read_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise AuditInputError(f"File not found: {path}")
    if path.suffix.lower() in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False)
    raise AuditInputError("Expected .csv or .parquet input")


def column(df: pd.DataFrame, title: str) -> str:
    """Find a unique Data Window series name even with a TV script prefix."""
    exact = [c for c in df.columns if str(c).strip() == title]
    if len(exact) == 1:
        return exact[0]
    suffix = [c for c in df.columns if re.search(
        r"(?:^|[.:])\s*" + re.escape(title) + r"\s*$", str(c)
    )]
    if len(suffix) == 1:
        return suffix[0]
    if not exact and not suffix:
        raise AuditInputError(
            f"Missing '{title}' in chart CSV. Use TradingView Export chart data "
            "with MNQ V2 Diagnostics added; the trade-list CSV is insufficient. "
            f"Available columns: {list(df.columns)[:28]}"
        )
    raise AuditInputError(f"Ambiguous '{title}' series among chart CSV columns: {suffix or exact}")


def timestamps(values: pd.Series, name: str) -> pd.Series:
    """UTC-aware bar-open stamps only; never guess timezone of naïve strings."""
    if pd.api.types.is_datetime64_any_dtype(values):
        if getattr(values.dt, "tz", None) is None:
            raise AuditInputError(f"{name} timestamps are timezone-naive. Provide UTC/offset-aware values.")
        parsed = values.dt.tz_convert("UTC")
    else:
        raw = values.astype("string").str.strip()
        if raw.isna().any() or (raw == "").any():
            raise AuditInputError(f"{name} has missing timestamps")
        if raw.str.fullmatch(r"\d{10}").all():
            parsed = pd.to_datetime(raw.astype("int64"), unit="s", utc=True, errors="coerce")
        elif raw.str.fullmatch(r"\d{13}").all():
            parsed = pd.to_datetime(raw.astype("int64"), unit="ms", utc=True, errors="coerce")
        elif raw.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", case=False, regex=True).all():
            parsed = pd.to_datetime(raw, utc=True, errors="coerce", format="mixed")
        else:
            raise AuditInputError(
                f"{name} contains timestamps without a numeric UTC offset. "
                "Explicitly convert source timestamps to ISO-8601 UTC first; "
                "never assume chart timezone or DST."
            )
    if parsed.isna().any():
        raise AuditInputError(f"{name} has unparseable timestamps")
    return pd.Series(parsed, index=values.index)


def prepare_bars(source: pd.DataFrame, *, chart: bool) -> pd.DataFrame:
    time_col = next((c for c in ("timestamp", "time", "Time", "datetime") if c in source.columns), None)
    if time_col is None:
        raise AuditInputError("Missing timestamp/time column (UTC ISO-8601, epoch seconds or milliseconds)")
    result = pd.DataFrame({"timestamp": timestamps(source[time_col], time_col)})
    for name in OHLC:
        key = column(source, name) if chart else name
        if key not in source.columns:
            raise AuditInputError(f"Missing source OHLC column: {key}")
        result[name] = pd.to_numeric(source[key], errors="coerce")
        if result[name].isna().any():
            raise AuditInputError(f"OHLC {key} contains missing/non-numeric data")
    if result.timestamp.duplicated().any():
        examples = result.loc[result.timestamp.duplicated(), "timestamp"].head(3).tolist()
        raise AuditInputError(f"Duplicate 1-minute bar-open timestamps: {examples}")
    result = result.sort_values("timestamp").reset_index(drop=True)
    if (result["high"] < result["low"]).any():
        raise AuditInputError("OHLC contains high < low")
    if (result["high"] < result[["open", "close"]].max(axis=1)).any():
        raise AuditInputError("OHLC high below open/close")
    if (result["low"] > result[["open", "close"]].min(axis=1)).any():
        raise AuditInputError("OHLC low above open/close")
    return result


def bool_series(values: pd.Series, label: str) -> pd.Series:
    # Strict 0/1 flags: blanks and string 'na' are *unknown*, not false.
    text = values.astype("string").str.strip().str.lower()
    if text.isna().any() or not text.isin(("0", "1", "0.0", "1.0", "true", "false")).all():
        raise AuditInputError(f"{label}: expected explicit 0/1 or true/false in every exported bar")
    return text.isin(("1", "1.0", "true"))


def python_reference(bars: pd.DataFrame, settings: dict[str, Any]) -> pd.DataFrame:
    """Apply genuine canonical raw-event functions, not a hand-coded imitation."""
    sys.path.insert(0, str(REPO / "src"))
    from swings import enrich_swings
    from structure import (
        add_internal_structure_trend,
        build_structure_settings,
        classify_structure_events,
        deduplicate_breaks,
        detect_structure_breaks,
    )
    from fvg import build_fvg_settings, detect_fvg_creation

    df = enrich_swings(bars, settings)
    df = add_internal_structure_trend(df)
    df = detect_structure_breaks(df, settings=build_structure_settings(settings))
    df = deduplicate_breaks(df)
    df = classify_structure_events(df, settings=build_structure_settings(settings))
    df = detect_fvg_creation(df, settings=build_fvg_settings(settings))
    return df[["timestamp", *OHLC, *PINE_FIELDS.keys()]].copy()


def audit(
    chart_source: pd.DataFrame,
    *,
    settings: dict[str, Any],
    reference_bars: pd.DataFrame | None = None,
    warmup_bars: int = 40,
    min_shared_bars: int = 100,
    max_samples: int = 20,
) -> dict[str, Any]:
    if warmup_bars < 0 or min_shared_bars <= 0 or max_samples < 0:
        raise AuditInputError("warmup>=0, min_shared_bars>=1 and max_samples>=0 required")
    pine_bars = prepare_bars(chart_source, chart=True)
    raw_time_col = next((c for c in ("timestamp", "time", "Time", "datetime") if c in chart_source.columns), None)
    if raw_time_col is None:
        raise AuditInputError("Chart export has no bar-open timestamp column")
    pine_events = pd.DataFrame({"timestamp": timestamps(chart_source[raw_time_col], raw_time_col)})
    for name, plot_title in PINE_FIELDS.items():
        pine_events[name] = bool_series(chart_source[column(chart_source, plot_title)], plot_title)
    pine_events = pine_events.sort_values("timestamp").reset_index(drop=True)

    model_bars = prepare_bars(reference_bars, chart=False) if reference_bars is not None else pine_bars
    python_events = python_reference(model_bars, settings)
    merged = pine_events.merge(
        python_events,
        on="timestamp",
        how="inner",
        suffixes=("_pine", "_python"),
        validate="one_to_one",
    )
    merged = merged.merge(pine_bars, on="timestamp", how="left", validate="one_to_one",
                          suffixes=("_reference", "_pineohlc"))
    if len(merged) < min_shared_bars + warmup_bars:
        raise AuditInputError(
            f"Only {len(merged)} shared 1m candles; require at least "
            f"{min_shared_bars} + warmup {warmup_bars}. Check contract, dates and timezone."
        )
    # If a distinct reference source was supplied, confirm *every* overlapping
    # OHLC bar before any event conclusions. For a continuous futures mismatch,
    # even similar event counts are not comparable.
    price_mismatches = []
    if reference_bars is not None:
        for name in OHLC:
            mismatch = (merged[f"{name}_reference"] - merged[f"{name}_pineohlc"]).abs() > 0.125
            price_mismatches.extend(
                [{"timestamp_utc": t.isoformat(), "field": name}
                 for t in merged.loc[mismatch, "timestamp"].head(max_samples)]
            )
        if price_mismatches:
            raise AuditInputError(
                "Independent MNQ prices do not align to within half a tick "
                "(0.125 index points). Check contract roll, back-adjustment and "
                "timestamp convention. Examples: " + json.dumps(price_mismatches[:max_samples])
            )

    compared = merged.iloc[warmup_bars:].reset_index(drop=True)
    fields = {}
    mismatches = []
    for name in PINE_FIELDS:
        p = compared[f"{name}_pine"].astype(bool)
        y = compared[name].astype(bool)
        mismatch = p != y
        fields[name] = {
            "pine_events": int(p.sum()),
            "python_events": int(y.sum()),
            "both": int((p & y).sum()),
            "pine_only": int((p & ~y).sum()),
            "python_only": int((~p & y).sum()),
            "disagreeing_bars": int(mismatch.sum()),
        }
        for idx in compared.index[mismatch][:max_samples]:
            mismatches.append({
                "timestamp_utc": compared.at[idx, "timestamp"].isoformat(),
                "signal": name,
                "pine": bool(p.at[idx]),
                "python": bool(y.at[idx]),
            })
    mismatches = sorted(mismatches, key=lambda r: (r["timestamp_utc"], r["signal"]))[:max_samples]
    return {
        "status": "differences_found" if any(v["disagreeing_bars"] for v in fields.values()) else "raw_events_match",
        "important_scope": (
            "Raw Pine MSS PROXY vs canonical Python deduplicated MSS, plus raw "
            "3-candle FVG creation; NOT linked setup stages, FVG lifecycle, "
            "confluence scoring, trade signals or profitable execution."
        ),
        "price_source": "independent_ohlc_checked" if reference_bars is not None else "same_tradingview_chart_ohlc",
        "chart_bars": len(pine_bars),
        "model_bars": len(model_bars),
        "overlapping_bars": len(merged),
        "excluded_initial_warmup_bars": warmup_bars,
        "compared_bars": len(compared),
        "first_utc": compared.timestamp.min().isoformat(),
        "last_utc": compared.timestamp.max().isoformat(),
        "signals": fields,
        "first_mismatches": mismatches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pine-chart", type=Path, required=True,
                        help="TradingView Export chart data CSV, NOT trade list CSV")
    parser.add_argument("--reference-bars", type=Path,
                        help="Optional independent full-history UTC MNQ 1m OHLC CSV or Parquet")
    parser.add_argument("--config", type=Path, default=REPO / "config/strategy.yaml")
    parser.add_argument("--warmup-bars", type=int, default=40)
    parser.add_argument("--min-shared-bars", type=int, default=100)
    parser.add_argument("--max-samples", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        with args.config.open("r", encoding="utf-8") as handle:
            settings = yaml.safe_load(handle)
        if not isinstance(settings, dict):
            raise AuditInputError("Strategy config is not a YAML dictionary")
        report = audit(
            read_data(args.pine_chart),
            settings=settings,
            reference_bars=read_data(args.reference_bars) if args.reference_bars else None,
            warmup_bars=args.warmup_bars,
            min_shared_bars=args.min_shared_bars,
            max_samples=args.max_samples,
        )
        payload = json.dumps(report, indent=2)
        print(payload)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload + "\n", encoding="utf-8")
        return 1 if report["status"] == "differences_found" else 0
    except (AuditInputError, FileNotFoundError, KeyError, ImportError, ValueError) as exc:
        print(json.dumps({"status": "cannot_compare", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
