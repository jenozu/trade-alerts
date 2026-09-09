from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_pipeline import (  # noqa: E402
    DEFAULT_REPORT_DIRECTORY,
    DEFAULT_STATE_DIRECTORY,
    load_yaml,
    stage_backtest,
    stage_market_state,
    stage_morning_report,
    stage_trade_plan,
)
from data_clock import visibility_times  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finish historical pipeline stages 17-20 from a certified scored cache."
    )
    parser.add_argument("--scored", required=True, help="Path to features_scored.parquet")
    parser.add_argument("--input", required=True, help="Original historical input path")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--symbol", default="MNQ")
    parser.add_argument("--contract", default=None)
    parser.add_argument(
        "--strategy-config",
        default=str(PROJECT_ROOT / "config" / "strategy.yaml"),
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Dedicated output directory. Defaults to data/results/research_runs/<year>_pipeline_final",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scored_path = Path(args.scored)
    input_path = Path(args.input)
    strategy_path = Path(args.strategy_config)
    results_dir = (
        Path(args.results_dir)
        if args.results_dir
        else PROJECT_ROOT / "data" / "results" / "research_runs" / f"{args.year}_pipeline_final"
    )
    state_dir = results_dir / "state"
    report_dir = results_dir / "reports"
    results_dir.mkdir(parents=True, exist_ok=True)

    if not scored_path.exists():
        raise SystemExit(f"Scored cache not found: {scored_path}")
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    strategy_config = load_yaml(strategy_path)
    data = pd.read_parquet(scored_path)
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

    print("=== CACHED PIPELINE TAIL ===")
    print(f"Year: {args.year}")
    print(f"Rows: {len(data):,}")
    print(f"Scored cache: {scored_path}")

    state_as_of = pd.Timestamp(visibility_times(data).iloc[-1])

    print("\n[17/20] BUILD DETERMINISTIC MARKET STATE")
    market_state, market_state_paths = stage_market_state(
        data,
        strategy_config=strategy_config,
        state_directory=state_dir,
        as_of=state_as_of,
        symbol=args.symbol,
        contract=args.contract,
        data_quality={
            "analysis_status": "degraded",
            "reasons": ["historical cached-tail completion"],
            "session_coverage": None,
        },
        source_snapshots=[str(input_path)],
    )

    print("\n[18/20] BUILD DETERMINISTIC TRADE PLAN")
    trade_plan = stage_trade_plan(market_state, strategy_config=strategy_config)

    print("\n[19/20] RENDER DETERMINISTIC MORNING REPORT")
    morning_report, morning_report_paths = stage_morning_report(
        market_state,
        trade_plan,
        report_directory=report_dir,
    )

    print("\n[20/20] RUN BACKTEST")
    trades = stage_backtest(
        data,
        strategy_config=strategy_config,
        results_directory=results_dir,
    )

    audit = {
        "year": args.year,
        "status": "completed",
        "completed_at": datetime.now().astimezone().isoformat(),
        "source_input": str(input_path),
        "scored_cache": str(scored_path),
        "rows": int(len(data)),
        "stages": {
            "17_market_state": {
                "status": "passed" if market_state["status"]["code"] in {"ready", "degraded"} else "no_analysis",
                "paths": market_state_paths,
            },
            "18_trade_plan": {
                "status": "passed" if trade_plan["decision"] == "TRADE PLAN" else "no_trade",
                "decision": trade_plan["decision"],
            },
            "19_morning_report": {
                "status": "passed",
                "paths": morning_report_paths,
                "decision": morning_report["decision"],
            },
            "20_backtest": {
                "status": "passed",
                "trades": int(len(trades)),
            },
        },
    }
    audit_path = results_dir / "cached_tail_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    print("\n=== CACHED PIPELINE TAIL COMPLETE ===")
    print(f"Results: {results_dir}")
    print(f"Audit: {audit_path}")


if __name__ == "__main__":
    main()
