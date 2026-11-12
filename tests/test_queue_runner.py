"""Queue runner tests: fake project, fake executor, no real experiments or network."""
import json
import subprocess
import textwrap

import pytest

from scripts.automation import run_queue as rq
from scripts.automation.queue_status import describe

POLICY = """schema_version: 1
periods:
  2023: development_research
  2024: development_research
  2025: development_research
  2026: pseudo_out_of_sample_validation
forward_holdout:
  status: not_established
  start: {start}
  end: null
"""

# Fake executor: same CLI as execute_run_request.py. FAKE_MODE env picks behaviour.
FAKE_EXECUTOR = textwrap.dedent('''
    import argparse, hashlib, json, os, subprocess, sys
    from pathlib import Path
    p = argparse.ArgumentParser()
    for a in ("--experiment", "--request-id", "--expected-sha"):
        p.add_argument(a, required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    runs = root / ".automation-runs"
    with (runs / "calls.log").open("a") as fh:
        fh.write(a.request_id + "\\n")
    run = runs / a.request_id
    run.mkdir(parents=True, exist_ok=False)
    mode = os.environ.get("FAKE_MODE", "ok")
    fail = mode == "fail:" + a.request_id
    (run / "env_keys.json").write_text(json.dumps(sorted(os.environ)))
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    (run / "manifest.json").write_text(json.dumps({
        "request_id": a.request_id, "experiment": a.experiment,
        "expected_sha": a.expected_sha, "actual_sha": sha,
        "status": "failed" if fail else "passed", "exit_code": 1 if fail else 0}))
    identity = {"files": {}}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    lock = json.dumps({"experiment_id": a.experiment, "input_identity_sha256": digest,
                       "identity": identity, "artifacts": {}})
    (run / "EXECUTION_OUTPUT_LOCK.json").write_text(lock)
    h = hashlib.sha256(lock.encode()).hexdigest()
    if mode == "badhash:" + a.request_id:
        h = "0" * 64
    (run / "ARCHIVE_MANIFEST.json").write_text(json.dumps(
        {"files": [{"path": "EXECUTION_OUTPUT_LOCK.json", "sha256": h}]}))
    sys.exit(1 if fail else 0)
''')


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def make_project(tmp_path, items, *, holdout_start="null", queue_id="QUEUE-T"):
    root = tmp_path / "proj"
    (root / "config").mkdir(parents=True)
    (root / "config" / "research_policy.yaml").write_text(POLICY.format(start=holdout_start))
    (root / "automation" / "experiments").mkdir(parents=True)
    (root / "automation" / "experiments" / "EXP-901.sh").write_text("#!/usr/bin/env bash\n")
    (root / "docs").mkdir()
    (root / "docs" / "prereg.md").write_text("prereg\n")
    (root / "scripts" / "automation").mkdir(parents=True)
    (root / "scripts" / "automation" / "execute_run_request.py").write_text(FAKE_EXECUTOR)
    (root / ".gitignore").write_text(".automation-runs/\n")
    (root / "automation" / "queues").mkdir()
    queue = root / "automation" / "queues" / "Q.yaml"
    queue.write_text(json.dumps({"queue_id": queue_id, "items": items}))  # JSON is valid YAML
    git(root.parent, "init", "-q", "-b", "main", str(root))
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "core.autocrlf", "false")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fixture")
    return root, queue, git(root, "rev-parse", "HEAD")


def item(rid, exp="EXP-901", periods=(2023,), prereg="docs/prereg.md"):
    return {"experiment": exp, "request_id": rid, "prereg": prereg, "periods": list(periods)}


def calls(root):
    log = root / ".automation-runs" / "calls.log"
    return log.read_text().split() if log.exists() else []


ALLOW = frozenset({"EXP-901"})


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    sent = []
    monkeypatch.setattr(rq, "send_telegram_alert", lambda alert, **kw: sent.append((alert, kw)) or {"ok": True})
    monkeypatch.delenv("FAKE_MODE", raising=False)
    return sent


def test_success_runs_all_items_in_order_and_notifies(tmp_path, monkeypatch, no_network):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2"), item("R3")])
    status = rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert status["state"] == "finished"
    assert calls(root) == ["R1", "R2", "R3"]
    assert [c["request_id"] for c in status["completed"]] == ["R1", "R2", "R3"]
    assert status["remaining"] == [] and status["notification"] == "sent"
    assert no_network[0][0]["type"] == "queue_finished"
    assert not (root / ".automation-runs" / "queue.lock").exists()


def test_failure_halts_and_never_retries(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "fail:R2")
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2"), item("R3")])
    status = rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert status["state"] == "halted"
    assert "R2" in status["halt_reason"] and calls(root) == ["R1", "R2"]
    assert status["remaining"] == ["R2", "R3"]
    monkeypatch.delenv("FAKE_MODE")
    with pytest.raises(rq.QueueRefused, match="already halted"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert calls(root) == ["R1", "R2"]  # nothing re-run


def test_bad_hash_halts(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "badhash:R1")
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2")])
    status = rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert status["state"] == "halted" and "hash mismatch" in status["halt_reason"]
    assert calls(root) == ["R1"]


def test_crash_resume_skips_completed_item(tmp_path, monkeypatch):
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2")])
    real = rq.execute_item

    def crash_on_second(root_, it, *a):
        if it["request_id"] == "R2":
            raise KeyboardInterrupt  # simulates the runner process dying
        return real(root_, it, *a)

    monkeypatch.setattr(rq, "execute_item", crash_on_second)
    with pytest.raises(KeyboardInterrupt):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    monkeypatch.setattr(rq, "execute_item", real)
    status = rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert status["state"] == "finished"
    assert calls(root) == ["R1", "R2"]  # R1 not re-run


def test_crash_mid_item_refuses_instead_of_rerunning(tmp_path, monkeypatch):
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2")])
    real = rq.execute_item

    def die_after_execute(root_, it, *a):
        real(root_, it, *a)
        raise KeyboardInterrupt  # died before verification was recorded

    monkeypatch.setattr(rq, "execute_item", die_after_execute)
    with pytest.raises(KeyboardInterrupt):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    monkeypatch.setattr(rq, "execute_item", real)
    with pytest.raises(rq.QueueRefused, match="will not be re-run"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert calls(root) == ["R1"]


def test_duplicate_request_ids_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R1")])
    with pytest.raises(rq.QueueRefused, match="duplicate"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert calls(root) == []


def test_existing_run_record_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1")])
    (root / ".automation-runs" / "R1").mkdir(parents=True)
    with pytest.raises(rq.QueueRefused, match="already exists"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)


def test_pseudo_oos_year_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1", periods=[2025, 2026])])
    with pytest.raises(rq.QueueRefused, match="2026"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)


def test_forward_holdout_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1", periods=[2024])], holdout_start="'2024-06-01'")
    with pytest.raises(rq.QueueRefused, match="forward holdout"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)


@pytest.mark.parametrize("bad, match", [
    (item("R1", exp="EXP-902"), "allowlist"),
    (item("R1", prereg="docs/missing.md"), "preregistration"),
    (item("R1", prereg="../outside.md"), "preregistration"),
    (item("R1", periods=[]), "periods"),
])
def test_invalid_items_refused(tmp_path, bad, match):
    root, queue, sha = make_project(tmp_path, [bad])
    with pytest.raises(rq.QueueRefused, match=match):
        rq.run_queue(root, queue, sha, allowed=ALLOW)


def test_default_allowlist_is_empty_and_refuses(tmp_path):
    assert rq.ALLOWED_WRAPPERS == frozenset()
    root, queue, sha = make_project(tmp_path, [item("R1")])
    with pytest.raises(rq.QueueRefused, match="allowlist"):
        rq.run_queue(root, queue, sha)


def test_max_length_and_empty_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item(f"R{i}") for i in range(rq.MAX_QUEUE_LENGTH + 1)])
    with pytest.raises(rq.QueueRefused, match="maximum"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    root2, queue2, sha2 = make_project(tmp_path / "b", [])
    with pytest.raises(rq.QueueRefused, match="empty"):
        rq.run_queue(root2, queue2, sha2, allowed=ALLOW)


def test_dirty_tree_and_wrong_sha_refused(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1")])
    with pytest.raises(rq.QueueRefused, match="commit mismatch"):
        rq.run_queue(root, queue, "f" * 40, allowed=ALLOW)
    (root / "stray.txt").write_text("x")
    with pytest.raises(rq.QueueRefused, match="working tree"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert calls(root) == []


def test_one_queue_at_a_time(tmp_path):
    root, queue, sha = make_project(tmp_path, [item("R1")])
    (root / ".automation-runs").mkdir()
    (root / ".automation-runs" / "queue.lock").write_text("other")
    with pytest.raises(rq.QueueRefused, match="another queue"):
        rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert (root / ".automation-runs" / "queue.lock").read_text() == "other"


def test_status_file_and_plain_english_output(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "fail:R2")
    root, queue, sha = make_project(tmp_path, [item("R1"), item("R2")])
    rq.run_queue(root, queue, sha, allowed=ALLOW)
    status = json.loads((root / ".automation-runs" / "queues" / "QUEUE-T" / "status.json").read_text())
    for key in ("current_experiment", "step", "started_at", "item_started_at",
                "completed", "remaining", "last_result"):
        assert key in status
    text = describe(status)
    assert "HALTED" in text and "Completed 1, remaining 1" in text
    assert "new request ID" in text and "R2" in text


def test_secrets_never_logged_or_passed_to_children(tmp_path, monkeypatch, capsys):
    token = "SECRET-TOKEN-123456"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "CHAT-987")

    def failing_send(alert, *, token, chat_id):
        raise rq.QueueHalt(f"leaky error with {token}")

    monkeypatch.setattr(rq, "send_telegram_alert", failing_send)
    root, queue, sha = make_project(tmp_path, [item("R1")])
    status = rq.run_queue(root, queue, sha, allowed=ALLOW)
    assert status["notification"] == "failed: QueueHalt"
    child_env = json.loads((root / ".automation-runs" / "R1" / "env_keys.json").read_text())
    assert "TELEGRAM_BOT_TOKEN" not in child_env and "TELEGRAM_CHAT_ID" not in child_env
    out = capsys.readouterr()
    everything = out.out + out.err + "".join(
        p.read_text(errors="ignore") for p in (root / ".automation-runs").rglob("*") if p.is_file())
    assert token not in everything and "CHAT-987" not in everything


def test_missing_credentials_skips_notification(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    root, queue, sha = make_project(tmp_path, [item("R1")])
    assert rq.run_queue(root, queue, sha, allowed=ALLOW)["notification"].startswith("skipped")
