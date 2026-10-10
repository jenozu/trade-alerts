"""Validate EXP-041–045 draft research contracts without executing them."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "research-plans" / "exp041_045_preparation.json"
REQUIRED = ("id", "stage", "name", "objective", "control", "candidate", "design",
            "dependencies", "deliverables", "decisions_required")

def validate_plan(data: dict) -> list[str]:
    errors = []
    if data.get("schema_version") != 1:
        errors.append("invalid schema version")
    if data.get("execution_enabled") is not False:
        errors.append("execution must remain disabled")
    if data.get("datasets_certified") is not False:
        errors.append("data certification cannot be asserted")
    items = data.get("experiments")
    if not isinstance(items, list) or len(items) != 5:
        return errors + ["exactly five draft experiments required"]
    ids = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"entry {i} is not a mapping")
            continue
        ident = item.get("id")
        ids.append(ident)
        if not isinstance(ident, str) or not re.fullmatch(r"EXP-\d{3}", ident):
            errors.append(f"entry {i} has invalid experiment ID")
        for key in REQUIRED:
            val = item.get(key)
            if key in ("dependencies", "deliverables", "decisions_required"):
                if not isinstance(val, list) or not val or not all(isinstance(v, str) and v.strip() for v in val):
                    errors.append(f"{ident}: invalid {key}")
            elif not isinstance(val, str) or not val.strip():
                errors.append(f"{ident}: invalid {key}")
        if item.get("stage") != ("R9" if i < 4 else "R10"):
            errors.append(f"{ident}: unexpected research stage")
    if ids != [f"EXP-{i:03d}" for i in range(41, 46)]:
        errors.append("IDs must be EXP-041–EXP-045, in order")
    return errors

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, default=DEFAULT_PATH)
    args = p.parse_args()
    errors = validate_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    for error in errors:
        print("FAIL:", error)
    if errors:
        return 1
    print("PASS: five proposed contracts valid; execution disabled and certification unclaimed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
