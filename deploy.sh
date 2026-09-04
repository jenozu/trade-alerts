#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

test -d .git || { echo "FAIL: not a Git checkout"; exit 1; }
test "$(git branch --show-current)" = "main" || { echo "FAIL: deployment branch must be main"; exit 1; }
test -z "$(git status --porcelain)" || { echo "FAIL: worktree has non-ignored changes"; exit 1; }

git fetch origin main
git merge --ff-only origin/main

test -x .venv/bin/python || { echo "FAIL: .venv is missing; create it before deployment"; exit 1; }
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q tests/test_production_operations.py

if test -f .env; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

.venv/bin/python scripts/healthcheck.py

if test "${TRADE_ALERTS_RESTART_SERVICES:-0}" = "1"; then
  sudo systemctl restart trade-alerts-health.timer trade-alerts-collect.timer \
    trade-alerts-premarket.timer trade-alerts-refresh.timer trade-alerts-arm.timer \
    trade-alerts-live.timer trade-alerts-recap.timer
fi

echo "PASS: trade-alerts deployment complete at $(git rev-parse --short HEAD)"
