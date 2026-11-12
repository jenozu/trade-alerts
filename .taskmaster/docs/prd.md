# VPS job manager for Claude Code (DRAFT, needs owner yes)

## Goal
Let Claude Code reach the trade-alerts VPS directly over SSH and use a small,
persistent job manager there to start jobs (first: the test suite), watch them,
fetch their logs and results, and report back. Claude has administrative access
(a dedicated account with sudo) to install packages, edit files, configure
services, troubleshoot and maintain the job manager on the trade-alerts VPS only (not the web-app deploy VPS). Done = from this PC, Claude can start a
`pytest` job on the VPS, the job survives Claude disconnecting, and Claude can
later read its status, tail its log and download its result, using a dedicated alias for the confirmed trade VPS.

## Non-goals
- No experiment or queue runs through this system until a later phase you approve
  separately. RULES.md §17/§17a stay as written; no RULES.md edits in this plan.
- No changes to the web-app deploy VPS (2.25.108.3) or its `deploy` account. Access is scoped to the confirmed trade-alerts VPS only.
- Admin access does NOT authorize experiments: EXP-030, QUEUE-001 and any experiment or
  queue run still need your explicit `run`/`run queue` command (RULES.md �17/�17a).
- No changes to strategy, research policy, research-archive/, or run-requests/current.json.
- No new services exposed to the internet (no web UI, no open ports).
- No secrets in the repo, logs or job output.

## Success criteria
- `ssh trade-vps job start pytest` returns a job ID in seconds; job keeps running after disconnect.
- `job status <id>`, `job logs <id> --tail 200`, `job fetch <id>` work from this PC.
- Claude's account can run `sudo -n` commands (verified), and only via the trade VPS alias.
- Only one heavy job at a time; jobs time out at 360 min; every job records commit SHA and exit code.

## Servers (do not confuse)
| Name | What it is | Status |
|---|---|---|
| **Web-app deploy VPS** | 2.25.108.3, local alias `vps`, user `deploy`, locked to `vps-agent` gatekeeper. No apps listed. | Leave unchanged. Not a target of this plan. |
| **Trade-alerts VPS** | Whatever host is in GitHub secret `TRADE_VPS_HOST` (set 2026-10-10). Has `/docker/trade-alerts`; last successful run 38062346882 left `/docker/trade-alerts/.automation-runs/EXP-030-r02-20261010/`. | **Unconfirmed.** Target of this plan once identified. |
| `lnve` | 72.60.170.192, root | Do not access unless owner confirms it is the trade VPS. |

No account creation, SSH or sudo changes on any server until the trade VPS is confirmed.

## Infrastructure audit (2026-11-12, read-only, from this PC; VPS not contacted)
| Item | Finding |
|---|---|
| Local SSH config | `Host vps` → 2.25.108.3, user `deploy`, key `~/.ssh/claude_vps` (already exists). `Host lnve` → 72.60.170.192, user `root`. **Trade VPS not yet confirmed; see Servers table.** |
| Paths the repo assumes | Workflow: `/docker/trade-alerts` (+ `.venv`). EXP-030: `/root/trade-alerts-verify-…`. EXP-001: `/docker/trade-alerts-2023`, `-2024`. Suggests the repo runs as **root** today. |
| Current run path | GitHub Actions → SSH as `TRADE_VPS_USER` with `ssh-keyscan` (host key not pinned) → `execute_run_request.py`. |
| Existing VPS automation | `deploy.sh`, `deploy/install.sh`, systemd units under `deploy/systemd/` (alert timers). systemd is therefore available. |
| Local tools | `ssh` present (Git Bash + Windows OpenSSH). No tmux locally (not needed). `gh` installed and logged in. |
| Existing plan | Unmerged `plan/master-tasks-20261103` (MASTER-TASKS.md) says "Claude may not touch the VPS" and plans pinned host key, forced-command key, non-root account (D8, T2.3, T2.5). Superseded for VPS access by the 2026-11-12 owner decision (admin access); see decision log. |
| Already built | Queue runner (PR #20) and EXP-030 hash manifest (PR #21), both draft, unmerged. |

## Capabilities
### Connect (access model, owner decision 2026-11-12)
- New alias (e.g. `trade-vps`) for the confirmed trade-alerts VPS. Full interactive SSH, no forced command. The `vps` alias and `deploy` account stay unchanged.
- Dedicated non-root account with broad sudo (passwordless for Claude's non-interactive use).
  Root SSH login not required. Host key pinned in `~/.ssh/known_hosts`.
- Claude may install packages, edit files, manage services and the job manager.
  Before destructive or hard-to-undo admin actions (deleting data, firewall/SSH changes,
  reboots, touching alert timers during 09:00-10:30 ET) Claude states the action first.
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
docs/vps_job_manager.md          <- setup steps for you + usage
tests/test_vps_job.py            <- fixtures, fake systemd-run
```
Job records: `/docker/trade-alerts/.automation-runs/jobs/<id>/` (gitignored dir already).

## Dependency order
1. `vps_job.py` command parsing + allowlist (no deps).
2. Job execution via systemd-run (needs 1).
3. Admin access verified (Phase 0/2).
4. Local helper / usage doc for Claude (needs 1–3).
5. Later: queue/experiment job types (needs owner approval + PR #20/#21 merged).

## Phases
- **Phase 0: Confirm the host (you + me, read-only).** You tell me which host is the trade VPS and approve one read-only check (`whoami; hostname; ls /docker/trade-alerts; systemctl --version; git -C /docker/trade-alerts rev-parse HEAD`). Exit: facts recorded here.
- **Phase 1: Job manager code, fixture-tested.** `vps_job.py` with `pytest` job types, tests with fake systemd. Exit: tests pass locally, draft PR.
- **Phase 2: Admin access setup.** Only if Phase 0 shows gaps: you run the exact steps I give (create account / add to sudo / install key). Exit: `ssh vps 'sudo -n true'` succeeds.
- **Phase 3: First remote test run.** I start `job start pytest`, monitor, fetch, report counts. Exit: real VPS pytest counts reported with the job record.
- **Phase 4 (separate approval): Experiment/queue job types.** Only via your explicit `run`/`run queue` command per RULES.md §17/§17a. Not designed in detail yet.

## Test strategy
`python -m pytest -q tests/test_vps_job.py` with a fake `systemd-run` on PATH and a fixture git repo; then full suite. Critical: allowlist refusal, one-job-at-a-time, no secrets in logs.

## Architecture and stack
- Python stdlib + systemd (already on the VPS). Rejected: forced-command key (owner wants admin access), tmux/screen (no status/exit codes), Celery/Redis (too heavy), a web API (opens a port).
- Default: reuse `.automation-runs/` and the existing Telegram transport.

## Risks and open questions
- Repo paths imply the app runs as root; `deploy` may need sudo or group access to `/docker/trade-alerts`.
- Running as root vs `deploy`: jobs need write access to `/docker/trade-alerts`. Default: same user the workflow uses.
- A Claude job and a GitHub-triggered run could overlap; the job manager will refuse if `.automation-runs/queue.lock` exists or a workflow run is active (best effort).
- This reverses MASTER-TASKS' "Claude may not touch the VPS" for test jobs; needs your yes.

## Decision log
- 2026-11-12: Proposed. Owner priority is direct Claude↔VPS SSH + job manager. Test jobs only until Phase 4 is approved. No RULES.md changes.
- 2026-11-12: Owner chose admin access via dedicated sudo account on `vps` (2.25.108.3), no forced command. Host confirmed; `lnve` out of scope. Experiment safeguards unchanged.
- 2026-11-12: Phase 0 check. `ssh vps` logs in as `deploy` but is locked by a forced command (`vps-agent 1.2.0`, a web-app deploy gatekeeper; its help says admin actions use sudo from your own login, never the deploy key). No shell, sudo unverifiable through it. `vps list` shows no apps; trade-alerts is not a vps-agent app, and `/docker/trade-alerts` could not be checked. Admin access needs a new `claude` sudo account (owner action). Open: confirm trade-alerts actually lives on 2.25.108.3.
- 2026-11-12: Owner: 2.25.108.3 not yet confirmed as trade VPS (it is the web-app deploy VPS). Paused account creation until `TRADE_VPS_HOST` target is identified via the EXP-030-r02 run folder.
