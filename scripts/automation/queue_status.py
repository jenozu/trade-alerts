#!/usr/bin/env python3
"""Print a queue's status.json in plain English. Read-only."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _elapsed(start: str | None, end: str | None) -> str:
    if not start:
        return "n/a"
    stop = datetime.fromisoformat(end) if end else datetime.now(timezone.utc)
    secs = int((stop - datetime.fromisoformat(start)).total_seconds())
    return f"{secs // 3600}h {secs % 3600 // 60}m {secs % 60}s"


def describe(status: dict) -> str:
    end = status.get("finished_at")
    lines = [
        f"Queue {status['queue_id']} is {status['state'].upper()} (commit {status['expected_sha'][:12]}).",
        f"Started {status['started_at']}; total elapsed {_elapsed(status['started_at'], end)}.",
        f"Completed {len(status['completed'])}, remaining {len(status['remaining'])}.",
    ]
    if status["state"] == "running" and status.get("current_request_id"):
        lines.append(f"Now: {status['current_experiment']} ({status['current_request_id']}), "
                     f"step '{status['step']}', running {_elapsed(status['item_started_at'], None)}.")
    if status.get("last_result"):
        r = status["last_result"]
        lines.append(f"Last result: {r.get('request_id')} -> {r.get('status')}"
                     + (f" ({r['reason']})" if r.get("reason") else ""))
    if status.get("halt_reason"):
        lines.append(f"HALTED because: {status['halt_reason']}")
        lines.append("Nothing will be retried. A rerun needs a new request ID and your approval.")
    if status.get("remaining"):
        lines.append("Remaining: " + ", ".join(status["remaining"]))
    if status.get("notification"):
        lines.append(f"Telegram notification: {status['notification']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("queue_id")
    p.add_argument("--project-root", type=Path, default=ROOT)
    args = p.parse_args()
    path = args.project_root / ".automation-runs" / "queues" / args.queue_id / "status.json"
    if not path.is_file():
        print(f"No status yet for {args.queue_id} ({path})")
        return 1
    print(describe(json.loads(path.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
