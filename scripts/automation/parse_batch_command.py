#!/usr/bin/env python3
"""Parse operator batch shorthand; never dispatch experiments.

This helper is for the ChatGPT command interface only. Execution still requires
an explicit, separately committed single-experiment run request.
"""
from __future__ import annotations

import argparse
import json
import re

VERBS = {"prepare", "run", "rerun", "status", "logs", "results"}
ID = r"(?:EXP[-_ ]?)?\d{1,3}"
COMMAND = re.compile(r"^\s*(prepare|run|rerun|status|logs|results)\s+(.+?)\s*$", re.I)
ITEM = re.compile(rf"^\s*({ID})\s*$", re.I)
RANGE = re.compile(rf"^\s*({ID})\s*-\s*({ID})\s*$", re.I)
MAX_BATCH = 20


def number(token: str) -> int:
    if not ITEM.fullmatch(token):
        raise ValueError(f"Invalid experiment number: {token!r}")
    value = int(re.search(r"\d{1,3}$", token.strip()).group())
    if not 1 <= value <= 999:
        raise ValueError("Experiment number must be 1–999")
    return value


def parse_batch_command(raw: str) -> dict:
    match = COMMAND.fullmatch(raw)
    if not match:
        raise ValueError("Expected command: prepare|run|rerun|status|logs|results followed by experiment IDs")
    verb, expr = match.groups()
    expr = re.sub(r"\s+and\s+", ",", expr, flags=re.I)
    if not expr.strip():
        raise ValueError("Missing experiment IDs")
    numbers: list[int] = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            raise ValueError("Empty experiment ID")
        span = RANGE.fullmatch(part)
        if span:
            start, end = (number(span.group(i)) for i in (1, 2))
            if end < start:
                raise ValueError("Descending ranges are not supported")
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(number(part))
        if len(numbers) > MAX_BATCH * 2:
            raise ValueError("Batch too large")
    values = list(dict.fromkeys(numbers))
    if len(values) > MAX_BATCH:
        raise ValueError(f"Maximum {MAX_BATCH} experiments per batch")
    return {"verb": verb.lower(), "experiments": [f"EXP-{n:03d}" for n in values], "requires_explicit_execution_authorization": verb.lower() in {"run", "rerun"}}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", help="e.g. 'prepare 31-35'")
    args = p.parse_args()
    print(json.dumps(parse_batch_command(args.command), indent=2))


if __name__ == "__main__":
    main()
