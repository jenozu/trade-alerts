from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "raw" / "barchart" / "mnq_continuous_1m.parquet"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "barchart" / "research_inputs"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a calendar-year research input with prior warm-up history."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--warmup-days", type=int, default=92)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source
    if not source.exists():
        raise FileNotFoundError(source)

    evaluation_start = pd.Timestamp(f"{args.year}-01-01T00:00:00Z")
    evaluation_end = pd.Timestamp(f"{args.year + 1}-01-01T00:00:00Z")
    warmup_start = evaluation_start - pd.Timedelta(days=args.warmup_days)

    df = pd.read_parquet(source)
    if "timestamp" not in df.columns:
        raise SystemExit("Source is missing timestamp column")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    selected = df[
        (df["timestamp"] >= warmup_start)
        & (df["timestamp"] < evaluation_end)
    ].copy()
    selected = selected.sort_values("timestamp").reset_index(drop=True)

    if selected.empty:
        raise SystemExit("Selected year input is empty")
    if selected["timestamp"].duplicated().any():
        raise SystemExit("Selected year input contains duplicate timestamps")

    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in selected.columns]
    if missing:
        raise SystemExit(f"Missing OHLCV columns: {missing}")
    null_ohlcv = int(selected[required].isna().sum().sum())
    if null_ohlcv:
        raise SystemExit(f"Selected year input contains {null_ohlcv} null OHLCV cells")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"mnq_{args.year}_warmup_{args.warmup_days}d.parquet"
    audit = output.with_suffix(".audit.json")
    selected.to_parquet(output, index=False)

    contracts = (
        selected["contract"].dropna().astype(str).drop_duplicates().tolist()
        if "contract" in selected.columns
        else []
    )
    evaluation_rows = int(
        ((selected["timestamp"] >= evaluation_start) & (selected["timestamp"] < evaluation_end)).sum()
    )

    payload = {
        "year": args.year,
        "warmup_days": args.warmup_days,
        "warmup_start_utc": str(warmup_start),
        "evaluation_start_utc": str(evaluation_start),
        "evaluation_end_exclusive_utc": str(evaluation_end),
        "actual_first_timestamp_utc": str(selected["timestamp"].min()),
        "actual_last_timestamp_utc": str(selected["timestamp"].max()),
        "rows_total": int(len(selected)),
        "rows_evaluation": evaluation_rows,
        "contracts": contracts,
        "duplicate_timestamps": 0,
        "null_ohlcv": 0,
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "output_path": str(output),
        "output_sha256": sha256_file(output),
    }
    audit.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("=== YEAR RESEARCH INPUT ===")
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
