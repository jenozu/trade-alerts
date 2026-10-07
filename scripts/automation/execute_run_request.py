#!/usr/bin/env python3
"""Execute one allowlisted experiment wrapper and preserve a small run record."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT_RE = re.compile(r"^EXP-(\d{3})$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_stream(command: list[str], *, cwd: Path, env: dict[str, str], log_handle) -> None:
    printable = " ".join(command)
    print(f"$ {printable}", flush=True)
    log_handle.write(f"$ {printable}\n")
    log_handle.flush()

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log_handle.write(line)
        log_handle.flush()

    code = process.wait()
    if code != 0:
        raise subprocess.CalledProcessError(code, command)


def git_head(project_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()

    experiment = args.experiment.strip().upper()
    request_id = args.request_id.strip()
    expected_sha = args.expected_sha.strip()

    if not EXPERIMENT_RE.fullmatch(experiment):
        raise SystemExit(f"Invalid normalized experiment ID: {experiment!r}")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise SystemExit(f"Invalid request ID: {request_id!r}")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_sha):
        raise SystemExit("expected-sha must be a full 40-character Git SHA")

    project_root = Path(__file__).resolve().parents[2]
    python_bin = project_root / ".venv" / "bin" / "python"
    wrapper = project_root / "automation" / "experiments" / f"{experiment}.sh"
    run_dir = project_root / ".automation-runs" / request_id
    run_dir.mkdir(parents=True, exist_ok=False)

    actual_sha = git_head(project_root)
    manifest = {
        "request_id": request_id,
        "experiment": experiment,
        "expected_sha": expected_sha,
        "actual_sha": actual_sha,
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "status": "starting",
        "exit_code": None,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    exit_code = 1
    try:
        if actual_sha != expected_sha:
            raise RuntimeError(
                f"Git SHA mismatch: VPS has {actual_sha}, workflow expected {expected_sha}"
            )
        if not python_bin.is_file():
            raise RuntimeError(f"Project virtualenv Python missing: {python_bin}")
        if not wrapper.is_file():
            raise RuntimeError(
                f"{experiment} is not prepared for remote execution. "
                f"Missing wrapper: {wrapper.relative_to(project_root)}"
            )

        env = os.environ.copy()
        env.update(
            {
                "PYTHON_BIN": str(python_bin),
                "TRADE_ALERTS_PROJECT_ROOT": str(project_root),
                "AUTOMATION_RUN_DIR": str(run_dir),
                "EXPERIMENT_ID": experiment,
                "AUTOMATION_GIT_SHA": actual_sha,
            }
        )

        manifest["status"] = "preflight"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        with (run_dir / "run.log").open("w", encoding="utf-8") as log_handle:
            # A research run should start from a known-good code baseline.
            run_stream(
                [str(python_bin), "-m", "pytest", "-q", "--maxfail=1"],
                cwd=project_root,
                env=env,
                log_handle=log_handle,
            )

            manifest["status"] = "running"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            run_stream(
                ["bash", str(wrapper)],
                cwd=project_root,
                env=env,
                log_handle=log_handle,
            )

        exit_code = 0
        manifest["status"] = "passed"
        return
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        print(manifest["error"], file=sys.stderr, flush=True)
        raise
    finally:
        manifest["exit_code"] = exit_code
        manifest["finished_at_utc"] = utc_now()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
