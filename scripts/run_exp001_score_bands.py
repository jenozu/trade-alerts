"""Run EXP-001 from archived trade ledgers without rerunning the pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from score_band_research import analyze_score_bands, markdown_report  # noqa: E402


def parse_ledger(value: str) -> tuple[int, Path]:
    try:
        year, raw_path = value.split("=", 1)
        return int(year), Path(raw_path)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Ledger must be YEAR=/path/to/trades.csv") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-001 ledger-only score-band baseline analysis.")
    parser.add_argument("--ledger", action="append", required=True, type=parse_ledger, metavar="YEAR=PATH")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "data" / "reports" / "EXP-001_score-bands-baseline"))
    args = parser.parse_args()
    ledgers = dict(args.ledger)
    if set(ledgers) != {2023, 2024, 2025}:
        parser.error("EXP-001 control set must contain exactly 2023, 2024, and 2025 ledgers.")
    missing = [str(path) for path in ledgers.values() if not path.exists()]
    if missing:
        parser.error("Ledger not found: " + ", ".join(missing))
    result = analyze_score_bands({year: pd.read_csv(path) for year, path in ledgers.items()})
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "exp001_score_band_results.json").write_text(json.dumps(result, indent=2, allow_nan=True), encoding="utf-8")
    (output / "EXP-001_score-band-baseline.md").write_text(markdown_report(result, ledger_paths={year: str(path) for year, path in ledgers.items()}), encoding="utf-8")
    print(f"EXP-001 complete: {output / 'EXP-001_score-band-baseline.md'}")


if __name__ == "__main__":
    main()
