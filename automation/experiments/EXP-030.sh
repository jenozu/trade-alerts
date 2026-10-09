#!/usr/bin/env bash
# Prepared diagnostic only; dispatch requires explicit user run authorization.
set -euo pipefail

: "${PYTHON_BIN:?missing PYTHON_BIN}"
: "${TRADE_ALERTS_PROJECT_ROOT:?missing TRADE_ALERTS_PROJECT_ROOT}"
: "${AUTOMATION_RUN_DIR:?missing AUTOMATION_RUN_DIR}"
: "${AUTOMATION_GIT_SHA:?missing AUTOMATION_GIT_SHA}"

cd "$TRADE_ALERTS_PROJECT_ROOT"
git diff --quiet
git diff --cached --quiet
test "$(git rev-parse HEAD)" = "$AUTOMATION_GIT_SHA"

SOURCE="/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/chronology"
OUTPUT="${SOURCE%/*}/EXP-030-${AUTOMATION_GIT_SHA}-${AUTOMATION_RUN_DIR##*/}"
test -f "$SOURCE/LINKED_SEQUENCE_SUMMARY.json"
test ! -e "$OUTPUT"

"$PYTHON_BIN" scripts/audit_linked_execution.py \
  --source-build "$SOURCE" --output-dir "$OUTPUT" --year 2023 \
  --family-policy confirmation_first_family_v1

"$PYTHON_BIN" - "$OUTPUT" "$AUTOMATION_RUN_DIR" <<'PY'
import json, sys
from copy import deepcopy
from pathlib import Path
import yaml
from scripts.check_r7_control import assess_control

output, evidence = map(Path, sys.argv[1:])
root = Path.cwd()
verified = assess_control(root / 'research-archive')
control = next(year for year in verified['years'] if year['year'] == 2023)
archived = root / 'research-archive/EXP-INTEGRITY-2023-DIAGNOSTIC'
old_lock = json.loads((archived / 'EXPERIMENT_INPUT_LOCK.json').read_text())
new_lock = json.loads((output / 'EXPERIMENT_INPUT_LOCK.json').read_text())
roles = [role for role in old_lock['artifacts'] if role.startswith('scored_cache_candidate:')]
for role in roles:
    assert old_lock['artifacts'][role] == new_lock['artifacts'][role], role
old_config = yaml.safe_load((archived / 'effective_strategy.yaml').read_text())
new_config = yaml.safe_load((output / 'effective_strategy.yaml').read_text())
expected = deepcopy(old_config)
expected['backtest']['family_policy'] = 'confirmation_first_family_v1'
assert expected == new_config, 'Unexpected config change beyond family policy'
old_decisions = json.loads((archived / 'decisions.json').read_text())
new_decisions = json.loads((output / 'decisions.json').read_text())
key = lambda row: (row['contract'], row['signal_time'], row['direction'])
lookup = {key(row): row for row in new_decisions}
for old in old_decisions:
    current = deepcopy(lookup[key(old)])
    assert current['plan'].pop('family_policy') == 'confirmation_first_family_v1'
    assert old == current, 'Existing control decision changed'
added = [row for row in new_decisions if key(row) not in {key(old) for old in old_decisions}]
assert [key(row) for row in added] == [('NMU23', '2023-08-24T13:45:00+00:00', 'short')]
summary = json.loads((output / 'EXECUTION_AUDIT_SUMMARY.json').read_text())
comparison = dict(status='DIAGNOSTIC_ONLY_NOT_PERFORMANCE_SELECTION',
    control=control, variant=summary, additional_decisions=added,
    existing_seven_decisions_unchanged=True, config_diff_only_family_policy=True,
    reused_locked_control=True, new_diagnostic_output=str(output))
evidence.mkdir(parents=True, exist_ok=True)
(evidence / 'FAMILY_POLICY_COMPARISON.json').write_text(json.dumps(comparison, indent=2) + '\n')
print('PASS: original seven decisions unchanged; one additional candidate evaluated; no performance selection')
PY

for artifact in EXECUTION_AUDIT_SUMMARY.json decisions.json effective_strategy.yaml \
                EXPERIMENT_INPUT_LOCK.json EXECUTION_OUTPUT_LOCK.json; do
  cp "$OUTPUT/$artifact" "$AUTOMATION_RUN_DIR/"
done
if test -f "$OUTPUT/diagnostic_trades.csv"; then
  cp "$OUTPUT/diagnostic_trades.csv" "$AUTOMATION_RUN_DIR/"
fi
