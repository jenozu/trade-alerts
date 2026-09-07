from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scorer import enrich_scores, add_score_change_events, scoring_summary, save_scoring_outputs  # noqa: E402
from backtest import run_backtest, calculate_backtest_metrics, save_backtest_outputs  # noqa: E402


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid YAML config: {path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resume a research run from a completed DOL parquet checkpoint."
    )
    parser.add_argument("--dol", required=True, help="Path to nq_1m_dol.parquet")
    parser.add_argument(
        "--strategy-config",
        default=str(PROJECT_ROOT / "config" / "strategy.yaml"),
    )
    parser.add_argument(
        "--processed-dir",
        default=str(PROJECT_ROOT / "data" / "processed"),
    )
    parser.add_argument(
        "--results-dir",
        default=str(PROJECT_ROOT / "data" / "results"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dol_path = Path(args.dol)
    processed_dir = Path(args.processed_dir)
    results_dir = Path(args.results_dir)
    strategy_config = load_yaml(Path(args.strategy_config))

    if not dol_path.exists():
        raise SystemExit(f"DOL checkpoint not found: {dol_path}")

    print("=== RESUME FROM DOL CHECKPOINT ===")
    print(f"DOL: {dol_path}")
    data = pd.read_parquet(dol_path)
    if "timestamp" in data.columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
    print(f"Rows: {len(data):,}")

    print("\n[16/20] SCORE LONG AND SHORT SETUPS")
    scored = enrich_scores(data, strategy_config)
    scored = add_score_change_events(scored, strategy_config)
    summary = scoring_summary(scored)
    save_scoring_outputs(scored, processed_dir / "scoring")
    print(f"Long candidates: {summary.long_candidates:,}")
    print(f"Short candidates: {summary.short_candidates:,}")
    print(f"Max long score: {summary.max_long_score}")
    print(f"Max short score: {summary.max_short_score}")

    print("\n[20/20] RUN BACKTEST")
    trades = run_backtest(scored, strategy_config)
    output_dir = results_dir / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)

    if trades.empty:
        trades.to_csv(output_dir / "trades.csv", index=False)
        metrics = {"trades": 0}
    else:
        metrics = calculate_backtest_metrics(trades)
        save_backtest_outputs(trades, output_dir)

    summary_payload = {
        "source_checkpoint": str(dol_path),
        "bars": int(len(scored)),
        "trades": int(len(trades)),
        "metrics": metrics,
    }
    (results_dir / "resume_from_dol_summary.json").write_text(
        json.dumps(summary_payload, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Bars: {len(scored):,}")
    print(f"Trades: {len(trades):,}")
    if trades.empty:
        print("No trades generated.")
    else:
        print(f"Win rate: {metrics.get('win_rate')}")
        print(f"Expectancy points: {metrics.get('expectancy_points')}")
        print(f"Expectancy R: {metrics.get('expectancy_r')}")
        print(f"Profit factor: {metrics.get('profit_factor')}")
    print(f"Scored cache candidate: {processed_dir / 'scoring' / 'nq_1m_scored.parquet'}")
    print(f"Results: {output_dir}")


if __name__ == "__main__":
    main()
