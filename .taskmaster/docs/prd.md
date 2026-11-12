# VPS job manager for Claude Code (DRAFT, needs owner yes)

## Goal
Let Claude Code reach the trade-alerts VPS directly over SSH and use a small,
persistent job manager there to start allowlisted jobs (first: the test suite),
watch them, fetch their logs and results, and report back, without giving
Claude a general shell on the VPS. Done = from this PC, Claude can start a
`pytest` job on the VPS, the job survives Claude disconnecting, and Claude can
later read its status, tail its log and download its result, all through one
restricted SSH key.

## Non-goals
- No experiment or queue runs through this system until a later phase you approve
  separately. RULES.md §17/§17a stay as written; no RULES.md edits in this plan.
- No general shell for Claude on the VPS (forced-command key only, once Phase 2 lands).
- No changes to strategy, research policy, research-archive/, or run-requests/current.json.
- No new services exposed to the internet (no web UI, no open ports).
- No secrets in the repo, logs or job output.

## Success criteria
- `ssh trade-vps job start pytest` returns a job ID in seconds; job keeps running after disconnect.
- `job status <id>`, `job logs <id> --tail 200`, `job fetch <id>` work from this PC.
- The Claude key cannot run anything except the job command (tested: `ssh trade-vps whoami` is refused).
- Only one heavy job at a time; jobs time out at 360 min; every job records commit SHA and exit code.

## Infrastructure audit (2026-11-12, read-only, from this PC; VPS not contacted)
| Item | Finding |
|---|---|
| Local SSH config | `Host vps` → 2.25.108.3, user `deploy`, key `~/.ssh/claude_vps` (already exists). `Host lnve` → 72.60.170.192, user `root`. **Not confirmed which one is the trade-alerts VPS.** |
| Paths the repo assumes | Workflow: `/docker/trade-alerts` (+ `.venv`). EXP-030: `/root/trade-alerts-verify-…`. EXP-001: `/docker/trade-alerts-2023`, `-2024`. Suggests the repo runs as **root** today. |
| Current run path | GitHub Actions → SSH as `TRADE_VPS_USER` with `ssh-keyscan` (host key not pinned) → `execute_run_request.py`. |
| Existing VPS automation | `deploy.sh`, `deploy/install.sh`, systemd units under `deploy/systemd/` (alert timers). systemd is therefore available. |
| Local tools | `ssh` present (Git Bash + Windows OpenSSH). No tmux locally (not needed). `gh` installed and logged in. |
| Existing plan | Unmerged `plan/master-tasks-20261103` (MASTER-TASKS.md) says "Claude may not touch the VPS" and plans pinned host key, forced-command key, non-root account (D8, T2.3, T2.5). This PRD changes that direction for test jobs; see decision log. |
| Already built | Queue runner (PR #20) and EXP-030 hash manifest (PR #21), both draft, unmerged. |

## Capabilities
### Connect
- Dedicated Claude key + `Host trade-vps` alias, pinned host key (no `ssh-keyscan` trust-on-first-use).
- Forced command in `authorized_keys`: the key can only run `vps_job.py "$SSH_ORIGINAL_COMMAND"`, with `no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding`.
### Run jobs
- `job start <type>`: types are a code allowlist. Phase 1: `pytest` (full suite) and `pytest-file <tests/x.py>`. Each job runs as a transient systemd unit (`systemd-run --unit=tajob-<id>`), so it survives disconnects and reboots are visible.
- Refuses if another job is running, tree dirty, or not on `main`/expected SHA.
### Monitor
- `job list`, `job status <id>` (state, start, elapsed, exit code, SHA), `job logs <id> [--tail N]`.
- `job cancel <id>`.
### Retrieve and report
- `job fetch <id>` streams a tar of the job's small result folder to stdout (Claude saves it locally).
- Optional Telegram "finished/failed" via the existing transport (env-only creds).

## Structure
```
scripts/automation/vps_job.py    <- single entry point: parse, allowlist, start/status/logs/fetch/cancel
deploy/ssh/authorized_keys.example <- forced-command line (no real key)
docs/vps_job_manager.md          <- setup steps for you + usage
tests/test_vps_job.py            <- fixtures, fake systemd-run
```
Job records: `/docker/trade-alerts/.automation-runs/jobs/<id>/` (gitignored dir already).

## Dependency order
1. `vps_job.py` command parsing + allowlist (no deps).
2. Job execution via systemd-run (needs 1).
3. Forced-command install doc (needs 1).
4. Local helper / usage doc for Claude (needs 1–3).
5. Later: queue/experiment job types (needs owner approval + PR #20/#21 merged).

## Phases
- **Phase 0: Confirm the host (you + me, read-only).** You tell me which host is the trade VPS and approve one read-only check (`whoami; hostname; ls /docker/trade-alerts; systemctl --version; git -C /docker/trade-alerts rev-parse HEAD`). Exit: facts recorded here.
- **Phase 1: Job manager code, fixture-tested.** `vps_job.py` with `pytest` job types, tests with fake systemd. Exit: tests pass locally, draft PR.
- **Phase 2: Locked-down access.** You install the Claude public key with the forced command (I give exact copy-paste steps); pin the host key locally. Exit: `ssh trade-vps whoami` refused, `ssh trade-vps job list` works.
- **Phase 3: First remote test run.** I start `job start pytest`, monitor, fetch, report counts. Exit: real VPS pytest counts reported with the job record.
- **Phase 4 (separate approval): Experiment/queue job types.** Only via your explicit `run`/`run queue` command per RULES.md §17/§17a. Not designed in detail yet.

## Test strategy
`python -m pytest -q tests/test_vps_job.py` with a fake `systemd-run` on PATH and a fixture git repo; then full suite. Critical: allowlist refusal, injection attempts in `SSH_ORIGINAL_COMMAND` refused, one-job-at-a-time, no secrets in logs.

## Architecture and stack
- Python stdlib + systemd (already on the VPS). Rejected: tmux/screen (no status/exit codes), Celery/Redis (too heavy), a web API (opens a port).
- Default: reuse `.automation-runs/` and the existing Telegram transport.

## Risks and open questions
- **Which host?** `vps` (2.25.108.3, deploy) vs `lnve` (72.60.170.192, root). Repo paths imply root.
- Running as root vs `deploy`: jobs need write access to `/docker/trade-alerts`. Default: same user the workflow uses.
- A Claude job and a GitHub-triggered run could overlap; the job manager will refuse if `.automation-runs/queue.lock` exists or a workflow run is active (best effort).
- This reverses MASTER-TASKS' "Claude may not touch the VPS" for test jobs; needs your yes.

## Decision log
- 2026-11-12: Proposed. Owner priority is direct Claude↔VPS SSH + job manager. Test jobs only until Phase 4 is approved. No RULES.md changes.
