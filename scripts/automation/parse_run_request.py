#!/usr/bin/env python3
"""Validate and normalize a committed experiment run request."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPERIMENT_RE = re.compile(r"^(?:EXP[-_ ]?)?(\d{1,3})$", re.IGNORECASE)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def normalize_experiment(value: object) -> str:
    raw = str(value or "").strip()
    match = EXPERIMENT_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"Invalid experiment identifier: {raw!r}")
    number = int(match.group(1))
    if number < 1 or number > 999:
        raise ValueError("Experiment number must be between 1 and 999")
    return f"EXP-{number:03d}"


def load_request(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Run request must be a JSON object")
    if data.get("action") != "run":
        raise ValueError("Run request action must be exactly 'run'")
    experiment = normalize_experiment(data.get("experiment"))
    request_id = str(data.get("request_id") or "").strip()
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise ValueError(
            "request_id must contain only letters, numbers, dot, underscore, or hyphen"
        )
    return {
        "action": "run",
        "experiment": experiment,
        "request_id": request_id,
        "requested_by": str(data.get("requested_by") or "unknown"),
        "note": str(data.get("note") or ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request_file", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    request = load_request(args.request_file)

    print(json.dumps(request, indent=2))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as fh:
            fh.write(f"experiment={request['experiment']}\n")
            fh.write(f"request_id={request['request_id']}\n")


if __name__ == "__main__":
    main()
