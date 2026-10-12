"""Validate EXP-036–040 nonexecuting preparation contracts."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "research-plans" / "exp036_040_preparation.json"
FIELDS = ("id", "stage", "name", "objective", "control", "candidate", "design",
          "dependencies", "deliverables", "decisions_required")


def validate_plan(data: dict) -> list[str]:
    errors = []
    if data.get("schema_version") != 1:
        errors.append("invalid schema version")
    if data.get("execution_enabled") is not False:
        errors.append("execution must remain disabled")
    if data.get("datasets_certified") is not False:
        errors.append("data certification cannot be asserted")
    entries = data.get("experiments")
    if not isinstance(entries, list) or len(entries) != 5:
        return errors + ["expected five experiment drafts"]
    ids = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {i} is not a dict")
            continue
        name = entry.get("id")
        ids.append(name)
        if not isinstance(name, str) or not re.fullmatch(r"EXP-\d{3}", name):
            errors.append(f"invalid ID at index {i}")
        for key in FIELDS:
            value = entry.get(key)
            if key in ("dependencies", "deliverables", "decisions_required"):
                if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
                    errors.append(f"{name}: invalid {key}")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{name}: invalid {key}")
        expected_stage = "R8" if i < 3 else "R9"
        if entry.get("stage") != expected_stage:
            errors.append(f"{name}: stage mismatch")
    if ids != [f"EXP-{i:03d}" for i in range(36, 41)]:
        errors.append("experiment ID sequence must be EXP-036 through EXP-040")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    errors = validate_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("PASS: EXP-036–040 draft contracts valid; execution remains disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
