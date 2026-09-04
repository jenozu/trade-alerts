#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$PROJECT_ROOT/deploy/systemd"
TARGET_DIR="/etc/systemd/system"
REPLACE=0
test "${1:-}" = "--replace" && REPLACE=1

test -d "$SOURCE_DIR" || { echo "FAIL: systemd templates missing"; exit 1; }

for source in "$SOURCE_DIR"/*.{service,timer}; do
  test -e "$source" || continue
  name="$(basename "$source")"
  temporary="$(mktemp)"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$source" > "$temporary"
  if test -e "$TARGET_DIR/$name" && ! cmp -s "$temporary" "$TARGET_DIR/$name" && test "$REPLACE" -ne 1; then
    rm -f "$temporary"
    echo "FAIL: $TARGET_DIR/$name differs; inspect it or rerun with --replace"
    exit 1
  fi
  sudo install -m 0644 "$temporary" "$TARGET_DIR/$name"
  rm -f "$temporary"
done

sudo systemctl daemon-reload
sudo systemctl enable --now \
  trade-alerts-health.timer trade-alerts-collect.timer \
  trade-alerts-premarket.timer trade-alerts-refresh.timer \
  trade-alerts-arm.timer trade-alerts-live.timer trade-alerts-recap.timer
sudo systemctl list-timers 'trade-alerts-*'

echo "PASS: systemd timers installed from $PROJECT_ROOT"
