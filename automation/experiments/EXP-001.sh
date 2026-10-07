#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON_BIN:?missing PYTHON_BIN}"
: "${TRADE_ALERTS_PROJECT_ROOT:?missing TRADE_ALERTS_PROJECT_ROOT}"
: "${AUTOMATION_RUN_DIR:?missing AUTOMATION_RUN_DIR}"

LEDGER_2023="/docker/trade-alerts-2023/data/results/backtest/trades.csv"
LEDGER_2024="/docker/trade-alerts-2024/data/results/backtest/trades.csv"
LEDGER_2025="/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv"
OUTPUT_DIR="${TRADE_ALERTS_PROJECT_ROOT}/data/reports/EXP-001_score-bands-baseline"

for ledger in "$LEDGER_2023" "$LEDGER_2024" "$LEDGER_2025"; do
  test -f "$ledger" || {
    echo "FAIL: required archived baseline ledger is missing: $ledger"
    exit 30
  }
done

"$PYTHON_BIN" scripts/run_exp001_score_bands.py   --ledger "2023=$LEDGER_2023"   --ledger "2024=$LEDGER_2024"   --ledger "2025=$LEDGER_2025"   --output-dir "$OUTPUT_DIR"

cp "$OUTPUT_DIR/exp001_score_band_results.json" "$AUTOMATION_RUN_DIR/"
cp "$OUTPUT_DIR/EXP-001_score-band-baseline.md" "$AUTOMATION_RUN_DIR/"

echo "PASS: EXP-001 completed from the existing archived 2023-2025 baseline ledgers."
