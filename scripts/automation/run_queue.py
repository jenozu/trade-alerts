#!/usr/bin/env python3
"""Run a fixed, committed experiment queue sequentially on the VPS.

The queue is written in advance by the operator. This runner never adds,
reorders, chooses or retries items. Each item goes through the existing
single-run executor (scripts/automation/execute_run_request.py), which keeps
its full-pytest preflight, commit check and duplicate request-ID refusal.
After each item, plain Python checks the evidence; any failure halts the queue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from scripts.archive_experiment import sha256_file  # noqa: E402  (also puts src/ on sys.path)
from scripts.automation.parse_batch_command import MAX_BATCH  # noqa: E402
from scripts.automation.parse_run_request import REQUEST_ID_RE, normalize_experiment  # noqa: E402
from experiment_identity import verify_input_lock  # noqa: E402
from telegram_transport import send_telegram_alert  # noqa: E402

# Only a reviewed code change may add a wrapper here. A wrapper qualifies once it
# writes EXECUTION_OUTPUT_LOCK.json and ARCHIVE_MANIFEST.json into $AUTOMATION_RUN_DIR.
# Neither EXP-001 nor EXP-030 does both today, so the allowlist starts empty.
ALLOWED_WRAPPERS: frozenset[str] = frozenset()
MAX_QUEUE_LENGTH = MAX_BATCH
ITEM_TIMEOUT_SECONDS = 360 * 60  # same limit as the single-run workflow
OUTPUT_LOCK = "EXECUTION_OUTPUT_LOCK.json"
HASH_MANIFEST = "ARCHIVE_MANIFEST.json"
SECRET_ENV = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


class QueueRefused(Exception):
    """Queue rejected before anything ran."""


class QueueHalt(Exception):
    """Queue stopped after starting; needs operator review."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def check_git_state(root: Path, expected_sha: str) -> None:
    """Same three checks as the workflow guard: on main, clean tree, exact commit."""
    if git(root, "branch", "--show-current") != "main":
        raise QueueHalt("checkout is not on main")
    if git(root, "status", "--porcelain"):
        raise QueueHalt("working tree has changes")
    actual = git(root, "rev-parse", "HEAD")
    if actual != expected_sha:
        raise QueueHalt(f"commit mismatch: expected {expected_sha}, HEAD is {actual}")


def holdout_years(policy: dict) -> set[int] | None:
    """Return a forward-holdout year range check, or None when not established."""
    hold = policy.get("forward_holdout") or {}
    if hold.get("start") is None:
        return None
    start = int(str(hold["start"])[:4])
    end = int(str(hold["end"])[:4]) if hold.get("end") is not None else 9999
    return set(range(start, end + 1))


def load_queue(root: Path, queue_path: Path, allowed: frozenset[str]) -> dict:
    data = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise QueueRefused("queue file must have queue_id and an items list")
    queue_id = str(data.get("queue_id") or "")
    if not REQUEST_ID_RE.fullmatch(queue_id):
        raise QueueRefused(f"invalid queue_id: {queue_id!r}")
    items = data["items"]
    if not items:
        raise QueueRefused("queue is empty")
    if len(items) > MAX_QUEUE_LENGTH:
        raise QueueRefused(f"queue has {len(items)} items; maximum is {MAX_QUEUE_LENGTH}")

    policy = yaml.safe_load((root / "config" / "research_policy.yaml").read_text(encoding="utf-8"))
    periods = policy.get("periods") or {}
    holdout = holdout_years(policy)
    seen: set[str] = set()
    clean = []
    for n, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise QueueRefused(f"item {n} is not a mapping")
        try:
            exp = normalize_experiment(item.get("experiment"))
        except ValueError as exc:
            raise QueueRefused(f"item {n}: {exc}") from None
        rid = str(item.get("request_id") or "").strip()
        if not REQUEST_ID_RE.fullmatch(rid):
            raise QueueRefused(f"item {n}: invalid request_id {rid!r}")
        if rid in seen:
            raise QueueRefused(f"duplicate request_id in queue: {rid}")
        seen.add(rid)
        if exp not in allowed:
            raise QueueRefused(f"item {n}: {exp} is not in the wrapper allowlist")
        if not (root / "automation" / "experiments" / f"{exp}.sh").is_file():
            raise QueueRefused(f"item {n}: wrapper for {exp} does not exist")
        prereg = str(item.get("prereg") or "")
        prereg_path = (root / prereg).resolve()
        if not prereg or Path(prereg).is_absolute() or not prereg_path.is_relative_to(root.resolve()) \
                or not prereg_path.is_file():
            raise QueueRefused(f"item {n}: preregistration file not found: {prereg!r}")
        if subprocess.run(["git", "ls-files", "--error-unmatch", prereg], cwd=root,
                          capture_output=True).returncode != 0:
            raise QueueRefused(f"item {n}: preregistration file is not committed: {prereg}")
        years = item.get("periods")
        if not isinstance(years, list) or not years or not all(isinstance(y, int) and not isinstance(y, bool) for y in years):
            raise QueueRefused(f"item {n}: periods must be a non-empty list of years")
        for year in years:
            if periods.get(year) != "development_research":
                raise QueueRefused(f"item {n}: {year} is {periods.get(year) or 'unclassified'}, "
                                   "not development_research")
            if holdout is not None and year in holdout:
                raise QueueRefused(f"item {n}: {year} overlaps the forward holdout")
        clean.append({"experiment": exp, "request_id": rid, "prereg": prereg, "periods": years})
    return {"queue_id": queue_id, "items": clean,
            "queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest()}


def verify_run(run_dir: Path, expected_sha: str) -> dict:
    """Plain-Python evidence check for one finished item. Raises QueueHalt."""
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise QueueHalt("run manifest.json missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("exit_code") != 0:
        raise QueueHalt(f"manifest exit_code is {manifest.get('exit_code')}")
    if manifest.get("status") != "passed":
        raise QueueHalt(f"manifest status is {manifest.get('status')!r}")
    if not (manifest.get("expected_sha") == manifest.get("actual_sha") == expected_sha):
        raise QueueHalt("expected/actual SHA mismatch in manifest")
    lock_path = run_dir / OUTPUT_LOCK
    if not lock_path.is_file():
        raise QueueHalt(f"{OUTPUT_LOCK} missing")
    try:
        verify_input_lock(json.loads(lock_path.read_text(encoding="utf-8")), check_files=False)
    except Exception as exc:
        raise QueueHalt(f"{OUTPUT_LOCK} invalid: {type(exc).__name__}: {exc}") from None
    hm_path = run_dir / HASH_MANIFEST
    if not hm_path.is_file():
        raise QueueHalt(f"{HASH_MANIFEST} missing")
    files = json.loads(hm_path.read_text(encoding="utf-8")).get("files") or []
    if OUTPUT_LOCK not in {f.get("path") for f in files}:
        raise QueueHalt(f"{HASH_MANIFEST} does not cover {OUTPUT_LOCK}")
    base = run_dir.resolve()
    for entry in files:
        path = (run_dir / str(entry.get("path"))).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise QueueHalt(f"hashed file missing or outside run dir: {entry.get('path')}")
        if sha256_file(path) != entry.get("sha256"):
            raise QueueHalt(f"hash mismatch: {entry.get('path')}")
    return {"status": "passed", "exit_code": 0, "hashed_files": len(files)}


class Status:
    def __init__(self, path: Path, data: dict):
        self.path, self.data = path, data

    def write(self, **changes) -> None:
        self.data.update(changes, updated_at=utc_now())
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)


def notify(status: Status) -> None:
    """Send 'finished or halted' via the existing transport. Never logs secrets."""
    token, chat = (os.environ.get(k) for k in SECRET_ENV)
    if not token or not chat:
        status.write(notification="skipped: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set")
        return
    d = status.data
    state = f"{d['state']}: {len(d['completed'])} done, {len(d['remaining'])} remaining"
    if d.get("halt_reason"):
        state += f"; reason: {d['halt_reason']}"
    try:
        send_telegram_alert({"type": f"queue_{d['state']}", "scenario_id": d["queue_id"],
                             "state": state, "as_of": utc_now()}, token=token, chat_id=chat)
        status.write(notification="sent")
    except Exception as exc:  # only the type name: messages could echo request details
        status.write(notification=f"failed: {type(exc).__name__}")


def execute_item(root: Path, item: dict, expected_sha: str, timeout: float) -> int:
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}
    cmd = [sys.executable, str(root / "scripts" / "automation" / "execute_run_request.py"),
           "--experiment", item["experiment"], "--request-id", item["request_id"],
           "--expected-sha", expected_sha]
    proc = subprocess.Popen(cmd, cwd=root, env=env, start_new_session=True)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)  # also stops pytest/wrapper children
        else:
            proc.kill()
        proc.wait()
        raise QueueHalt(f"timed out after {timeout:.0f}s") from None


def run_queue(root: Path, queue_path: Path, expected_sha: str, *,
              allowed: frozenset[str] = ALLOWED_WRAPPERS,
              timeout: float = ITEM_TIMEOUT_SECONDS) -> dict:
    root = root.resolve()
    runs = root / ".automation-runs"
    runs.mkdir(exist_ok=True)
    lock = runs / "queue.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise QueueRefused(f"another queue holds {lock} (if no runner is alive, delete it by hand)") from None
    # ponytail: manual stale-lock removal after a hard crash; add PID liveness check if this becomes routine
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{os.getpid()} {queue_path.name} {utc_now()}\n")
    try:
        return _run_locked(root, runs, queue_path, expected_sha, allowed, timeout)
    finally:
        lock.unlink(missing_ok=True)


def _run_locked(root, runs, queue_path, expected_sha, allowed, timeout) -> dict:
    try:
        check_git_state(root, expected_sha)
    except QueueHalt as exc:
        raise QueueRefused(str(exc)) from None
    queue = load_queue(root, queue_path, allowed)
    state_dir = runs / "queues" / queue["queue_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path = state_dir / "status.json"

    if status_path.is_file():
        old = json.loads(status_path.read_text(encoding="utf-8"))
        if old.get("state") in ("halted", "finished"):
            raise QueueRefused(f"queue {queue['queue_id']} already {old['state']}; "
                               "a new queue_id and request IDs are required")
        if old.get("queue_sha256") != queue["queue_sha256"] or old.get("expected_sha") != expected_sha:
            raise QueueRefused("queue file or commit changed since this queue started")
        status = Status(status_path, old)
    else:
        status = Status(status_path, {
            "queue_id": queue["queue_id"], "queue_sha256": queue["queue_sha256"],
            "expected_sha": expected_sha, "state": "running", "started_at": utc_now(),
            "completed": [], "remaining": [i["request_id"] for i in queue["items"]],
            "current_experiment": None, "current_request_id": None, "step": "preflight",
            "item_started_at": None, "last_result": None, "halt_reason": None, "notification": None,
        })
    done = {c["request_id"] for c in status.data["completed"]}
    for item in queue["items"]:
        if item["request_id"] not in done and (runs / item["request_id"]).exists():
            raise QueueRefused(f"run record already exists for {item['request_id']} but it is not a "
                               "completed item of this queue; it will not be re-run")
    status.write(state="running", step="preflight")

    try:
        for item in queue["items"]:
            rid = item["request_id"]
            if rid in done:
                continue
            check_git_state(root, expected_sha)
            status.write(current_experiment=item["experiment"], current_request_id=rid,
                         step="executing", item_started_at=utc_now())
            code = execute_item(root, item, expected_sha, timeout)
            status.write(step="verifying")
            if code != 0:
                raise QueueHalt(f"{rid}: executor exit code {code}")
            try:
                result = verify_run(runs / rid, expected_sha)
            except QueueHalt as exc:
                raise QueueHalt(f"{rid}: {exc}") from None
            check_git_state(root, expected_sha)
            result = {"request_id": rid, "experiment": item["experiment"],
                      "finished_at": utc_now(), **result}
            status.data["completed"].append(result)
            status.data["remaining"].remove(rid)
            status.write(step="done", last_result=result)
        status.write(state="finished", step="finished", current_experiment=None,
                     current_request_id=None, finished_at=utc_now())
    except Exception as exc:
        reason = str(exc) if isinstance(exc, QueueHalt) else f"unexpected {type(exc).__name__}: {exc}"
        status.write(state="halted", halt_reason=reason, finished_at=utc_now(),
                     last_result={"request_id": status.data.get("current_request_id"),
                                  "status": "failed", "reason": reason})
    notify(status)
    return status.data


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("queue_file", type=Path)
    p.add_argument("--expected-sha", required=True, help="full 40-char commit the VPS must be on")
    args = p.parse_args()
    if len(args.expected_sha) != 40:
        print("REFUSED: --expected-sha must be a full 40-character Git SHA", file=sys.stderr)
        return 2
    try:
        result = run_queue(ROOT, args.queue_file.resolve(), args.expected_sha)
    except QueueRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"QUEUE {result['queue_id']}: {result['state'].upper()}"
          + (f" - {result['halt_reason']}" if result.get("halt_reason") else ""))
    return 0 if result["state"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
