# Experiment execution wrappers

Each remotely runnable research experiment must have one committed shell wrapper:

```text
automation/experiments/EXP-NNN.sh
```

The automation dispatcher will not accept arbitrary commands from a run request. It only
executes the wrapper matching the requested experiment ID.

## Required wrapper properties

- Start with `#!/usr/bin/env bash` and `set -euo pipefail`.
- Use `$PYTHON_BIN` instead of assuming a global Python executable.
- Treat `$AUTOMATION_RUN_DIR` as the small, per-run evidence directory.
- Do not put API keys, credentials, or environment dumps in run output.
- Keep market datasets and large generated files outside Git.
- Copy only useful small summaries/metrics into `$AUTOMATION_RUN_DIR`.
- Follow `RULES.md`, especially no-look-ahead and strategy-ambiguity guardrails.
- Do not change strategy semantics merely to make an experiment execute.

The runner supplies:

```text
PYTHON_BIN=/docker/trade-alerts/.venv/bin/python
TRADE_ALERTS_PROJECT_ROOT=/docker/trade-alerts
AUTOMATION_RUN_DIR=/docker/trade-alerts/.automation-runs/<request_id>
EXPERIMENT_ID=EXP-NNN
AUTOMATION_GIT_SHA=<exact triggering commit>
```

## Example only

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON_BIN:?missing PYTHON_BIN}"
: "${AUTOMATION_RUN_DIR:?missing AUTOMATION_RUN_DIR}"

"$PYTHON_BIN" scripts/run_exp999_example.py \
  --input /path/to/vps-only/input.csv \
  --output-dir data/reports/EXP-999-example

cp data/reports/EXP-999-example/summary.json "$AUTOMATION_RUN_DIR/"
cp data/reports/EXP-999-example/report.md "$AUTOMATION_RUN_DIR/"
```

Do not copy the example paths into a real experiment. `prepare N` must use the actual
inputs and commands validated for that experiment.
