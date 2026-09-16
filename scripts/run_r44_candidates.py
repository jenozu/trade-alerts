from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(
        0,
        str(SRC),
    )

from score_candidate_models import (
    analyze,
    markdown_report,
    summary_frame,
    weights_frame,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--classified-trades",
        required=True,
    )

    parser.add_argument(
        "--config",
        default="config/strategy.yaml",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    args = parser.parse_args()

    df = pd.read_csv(
        args.classified_trades
    )

    result, scored = analyze(
        df,
        args.config,
    )

    out = Path(
        args.output_dir
    )

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        out /
        "R4-04-Candidate-Scoring-Models.md"
    ).write_text(
        markdown_report(result),
        encoding="utf-8",
    )

    (
        out /
        "r44_candidate_scoring_results.json"
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    summary_frame(
        result
    ).to_csv(
        out /
        "candidate_threshold_summary.csv",
        index=False,
    )

    weights_frame().to_csv(
        out /
        "candidate_weights.csv",
        index=False,
    )

    scored.to_csv(
        out /
        "candidate_rescored_baseline_trades.csv",
        index=False,
    )

    print("R4.4 complete")

    print(
        "baseline reconstruction:",
        result[
            "baseline_reconstruction"
        ],
    )

    print()

    print(
        summary_frame(
            result
        ).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
