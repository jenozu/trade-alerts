"""Validate nonexecuting draft contracts for EXP-046 through EXP-050."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "research-plans" / "exp046_050_preparation.json"
FIELDS = ("id", "stage", "name", "objective", "control", "candidate", "design",
          "dependencies", "decisions_required", "deliverables")

def validate_plan(data: dict) -> list[str]:
    errors = []
    if data.get("schema_version") != 1:
        errors.append("unsupported schema version")
    if data.get("execution_enabled") is not False:
        errors.append("execution must be disabled")
    if data.get("datasets_certified") is not False:
        errors.append("data certification must not be claimed")
    items = data.get("experiments")
    if not isinstance(items, list) or len(items) != 5:
        return errors + ["five draft experiments required"]
    ids = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"entry {index} not an object")
            continue
        ident = item.get("id")
        ids.append(ident)
        if not isinstance(ident, str) or re.fullmatch(r"EXP-\d{3}", ident) is None:
            errors.append(f"invalid experiment ID at index {index}")
        for name in FIELDS:
            value = item.get(name)
            if name in ("dependencies", "decisions_required", "deliverables"):
                if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
                    errors.append(f"{ident}: invalid {name}")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{ident}: invalid {name}")
        expected = "R10" if index == 0 else "R11" if index < 3 else "R12"
        if item.get("stage") != expected:
            errors.append(f"{ident}: invalid research stage")
    if ids != [f"EXP-{n:03d}" for n in range(46, 51)]:
        errors.append("IDs must be EXP-046 through EXP-050 in order")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    errors = validate_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    for error in errors:
        print("FAIL:", error)
    if errors:
        return 1
    print("PASS: five nonexecuting EXP-046–050 draft contracts validated")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
