from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dol_research import (
    analyze,
    enrich,
    markdown_report,
    metrics_frame,
)


def parse(values):
    out = {}
    for raw in values:
        y, p = raw.split("=", 1)
        out[int(y)] = Path(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", action="append", required=True)
    ap.add_argument("--features", action="append", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    ledgers = parse(args.ledger)
    features = parse(args.features)

    frames = {}

    for year in (2023, 2024, 2025):
        frames[year] = enrich(
            pd.read_csv(ledgers[year]),
            pd.read_parquet(features[year]),
        )

    result, classified = analyze(frames)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / "EXP-014-Draw-on-Liquidity.md").write_text(
        markdown_report(result),
        encoding="utf-8",
    )

    (out / "exp014_dol_results.json").write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    metrics_frame(result).to_csv(
        out / "dol_metrics.csv",
        index=False,
    )

    classified.to_csv(
        out / "classified_dol_trades.csv",
        index=False,
    )

    print("EXP-014 complete")
    print(
        f"feature_match={result['coverage']['matched']}/"
        f"{result['coverage']['total']}"
    )


if __name__ == "__main__":
    main()
