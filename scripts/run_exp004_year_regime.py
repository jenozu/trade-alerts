#!/usr/bin/env python3
"""Run EXP-004 from archived trade ledgers without rerunning the pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from year_regime_research import analyze_year_regime, flatten_tables, markdown_report


def parse_ledger(value: str):
    try:
        year, path = value.split("=", 1)
        return int(year), Path(path)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Ledger must be YEAR=/path/to/trades.csv") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="EXP-004 ledger-only year/regime diagnostic")
    parser.add_argument("--ledger", action="append", required=True, type=parse_ledger, metavar="YEAR=PATH")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "data" / "reports" / "EXP-004_year-regime-stability"))
    args = parser.parse_args()

    ledgers = dict(args.ledger)
    if set(ledgers) != {2023, 2024, 2025}:
        parser.error("EXP-004 control set must contain exactly 2023, 2024, and 2025 ledgers.")
    missing = [str(path) for path in ledgers.values() if not path.exists()]
    if missing:
        parser.error("Ledger not found: " + ", ".join(missing))

    result = analyze_year_regime({year: pd.read_csv(path) for year, path in ledgers.items()})
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "exp004_year_regime_results.json").write_text(json.dumps(result, indent=2, allow_nan=True), encoding="utf-8")
    (out / "EXP-004-Year-and-Regime-Stability.md").write_text(markdown_report(result, {y: str(p) for y,p in ledgers.items()}), encoding="utf-8")
    for name, table in flatten_tables(result).items():
        table.to_csv(out / f"{name}.csv", index=False)
    print(f"EXP-004 complete: {out / 'EXP-004-Year-and-Regime-Stability.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
