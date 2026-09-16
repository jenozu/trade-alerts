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

from score_component_lift_research import (
    enrich,
)

from score_component_redundancy_research import (
    analyze,
    markdown_report,
    summary_frame,
)


def parse(values):
    out = {}

    for raw in values:
        year, path = raw.split("=", 1)
        out[int(year)] = Path(path)

    return out


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--ledger",
        action="append",
        required=True,
    )

    parser.add_argument(
        "--features",
        action="append",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    args = parser.parse_args()

    ledgers = parse(args.ledger)
    features = parse(args.features)

    frames = []

    for year in (2023, 2024, 2025):
        x = enrich(
            pd.read_csv(ledgers[year]),
            pd.read_parquet(features[year]),
        )

        x["year"] = year
        frames.append(x)

    df = pd.concat(
        frames,
        ignore_index=True,
    )

    result = analyze(df)

    out = Path(args.output_dir)
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        out /
        "R4-03-Component-Redundancy.md"
    ).write_text(
        markdown_report(result),
        encoding="utf-8",
    )

    (
        out /
        "r43_component_redundancy_results.json"
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    summary = summary_frame(result)

    summary.to_csv(
        out /
        "component_redundancy_summary.csv",
        index=False,
    )

    print("R4.3 complete")
    print()

    print(
        summary[[
            "component_a",
            "component_b",
            "phi",
            "jaccard",
            "both_active",
            "a_added_to_b_expectancy",
            "b_added_to_a_expectancy",
        ]]
        .head(25)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
