"""Validate proposed research contracts without launching historical research."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "research-plans" / "exp031_035_preparation.json"
EXPERIMENT_ID = re.compile(r"EXP-\d{3}\Z")
REQUIRED = ("id", "stage", "name", "objective", "control", "candidate",
            "design", "dependencies", "deliverables", "decisions_required")


def validate_plan(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("unsupported schema version")
    if data.get("execution_enabled") is not False:
        errors.append("draft plans must not enable execution")
    if data.get("datasets_certified") is not False:
        errors.append("draft plans must not assert data certification")
    plans = data.get("experiments")
    if not isinstance(plans, list) or len(plans) != 5:
        return errors + ["exactly five experiment drafts required"]
    ids = []
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            errors.append(f"index {index}: expected object")
            continue
        ident = plan.get("id")
        if not isinstance(ident, str) or not EXPERIMENT_ID.fullmatch(ident):
            errors.append(f"index {index}: invalid experiment ID")
        ids.append(ident)
        for field in REQUIRED:
            value = plan.get(field)
            if field in ("dependencies", "deliverables", "decisions_required"):
                if not isinstance(value, list) or not value or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    errors.append(f"{ident}: missing or invalid {field}")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{ident}: missing or invalid {field}")
        if plan.get("stage") not in ("R7", "R8"):
            errors.append(f"{ident}: unexpected stage")
    if ids != [f"EXP-{n:03d}" for n in range(31, 36)]:
        errors.append("experiment IDs must be EXP-031..EXP-035 in order")
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
    print("PASS: five nonexecuting draft contracts validated; none are executable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
