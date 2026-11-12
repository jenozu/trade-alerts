# Experiment queue runner

Runs a fixed, committed list of experiments one after another on the VPS.
**Status: approved (RULES.md §17a). Fixture-tested; not yet run on the VPS.** See
`docs/decisions/batch_queue_approval.md`.

## What it does

1. Refuses to start unless: no other queue holds `.automation-runs/queue.lock`;
   checkout is on `main`, clean, and at `--expected-sha`; queue has 1–20 items
   (`MAX_BATCH`); request IDs are unique and have no existing run record; every
   experiment is in `ALLOWED_WRAPPERS` and has a wrapper; every `prereg` file is
   committed; every listed year is `development_research` in
   `config/research_policy.yaml` and outside any forward holdout.
2. For each item, in file order, calls the existing
   `scripts/automation/execute_run_request.py` (full pytest, commit check,
   duplicate-ID refusal, run record). 360-minute limit per item.
3. After each item, plain Python checks: executor exit code 0; manifest
   `status == passed` and `exit_code == 0`; manifest expected SHA == actual SHA ==
   queue SHA; `EXECUTION_OUTPUT_LOCK.json` present and internally consistent;
   `ARCHIVE_MANIFEST.json` covers the lock and every listed SHA-256 matches;
   git state unchanged.
4. Any failure or unexpected error → queue **halts**, reason recorded, Telegram
   alert sent. Nothing is retried. A halted or finished queue cannot be started
   again; a rerun needs a new queue ID, new request IDs and your approval.

## Wrapper requirements to be allowlisted

A wrapper must write into `$AUTOMATION_RUN_DIR`:
- `EXECUTION_OUTPUT_LOCK.json` (written with `experiment_identity.write_input_lock`)
- `ARCHIVE_MANIFEST.json` with `{"files": [{"path": ..., "sha256": ...}]}`,
  paths relative to the run dir, including the output lock.

EXP-001 and EXP-030 do not do both today, so `ALLOWED_WRAPPERS` is empty.
Adding one is a reviewed code change to `scripts/automation/run_queue.py`.

## Crash and resume

Start the same command again. Items recorded as completed are skipped. If an
item had started (its `.automation-runs/<request_id>/` exists) but was not
recorded as completed, the runner refuses: it will not re-run it. If the queue
file or commit changed since the start, it refuses. After a hard crash
(power loss, `kill -9`) the lock file stays; confirm no runner process is alive
(`pgrep -f run_queue.py`), then delete `.automation-runs/queue.lock` by hand.

## Commands (on the VPS, once approved)

```bash
cd /docker/trade-alerts
git fetch origin main && git merge --ff-only origin/main
export TELEGRAM_BOT_TOKEN=...   # environment only; never in files or commits
export TELEGRAM_CHAT_ID=...
tmux new -s queue
.venv/bin/python scripts/automation/run_queue.py automation/queues/QUEUE-001.yaml \
  --expected-sha "$(git rev-parse HEAD)"
# check progress from another shell (read-only):
.venv/bin/python scripts/automation/queue_status.py QUEUE-001
```

Status lives in `.automation-runs/queues/<queue_id>/status.json` (gitignored).

## Secrets

Telegram credentials come only from `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`.
They are removed from the environment passed to the executor, pytest and the
wrappers. Notification failures are recorded by exception type only.

## Known limits

- `periods` is declared in the queue file; the runner cannot see what data a
  wrapper actually reads. Review wrappers for this when allowlisting.
- A single-run request pushed to `main` while a queue runs would move the VPS
  checkout. The runner detects the commit change and halts, but the item
  running at that moment is affected. Do not commit `run-requests/current.json`
  while a queue is running.
