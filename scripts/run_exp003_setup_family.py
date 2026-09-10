"""Run EXP-003 from archived trade ledgers without rerunning the pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from setup_family_research import analyze_setup_families, flatten_tables, markdown_report


def parse_ledger(value: str) -> tuple[int, Path]:
    try:
        year, path = value.split("=", 1)
        return int(year), Path(path)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Ledger must be YEAR=/path/to/trades.csv") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-003 ledger-only setup-family diagnostic")
    parser.add_argument("--ledger", action="append", required=True, type=parse_ledger, metavar="YEAR=PATH")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "reports" / "EXP-003_setup-family-comparison"),
    )
    args = parser.parse_args()
    ledgers = dict(args.ledger)
    if set(ledgers) != {2023, 2024, 2025}:
        parser.error("EXP-003 control set must contain exactly 2023, 2024, and 2025 ledgers.")
    missing = [str(path) for path in ledgers.values() if not path.exists()]
    if missing:
        parser.error("Ledger not found: " + ", ".join(missing))

    result = analyze_setup_families({year: pd.read_csv(path) for year, path in ledgers.items()})
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = output / "EXP-003-Setup-Family-Comparison.md"
    report.write_text(markdown_report(result, {year: str(path) for year, path in ledgers.items()}), encoding="utf-8")
    (output / "exp003_setup_family_results.json").write_text(
        json.dumps(result, indent=2, allow_nan=True), encoding="utf-8"
    )
    for name, table in flatten_tables(result).items():
        table.to_csv(output / f"{name}.csv", index=False)
    print(f"EXP-003 complete: {report}")


if __name__ == "__main__":
    main()
