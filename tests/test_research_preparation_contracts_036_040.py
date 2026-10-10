import json
from scripts.automation.validate_preparation_plan_036_040 import DEFAULT_PATH, validate_plan


def load():
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def test_valid_nonexecuting_drafts():
    assert validate_plan(load()) == []


def test_execution_approval_not_implied():
    data = load()
    data["execution_enabled"] = True
    assert any("execution" in e for e in validate_plan(data))


def test_data_certification_not_implied():
    data = load()
    data["datasets_certified"] = True
    assert any("certification" in e for e in validate_plan(data))


def test_missing_required_decisions_fails():
    data = load()
    data["experiments"][3]["decisions_required"] = []
    assert any("decisions_required" in e for e in validate_plan(data))


def test_duplicated_id_fails():
    data = load()
    data["experiments"][1]["id"] = "EXP-036"
    assert any("ID sequence" in e for e in validate_plan(data))


def test_wrong_research_stage_fails():
    data = load()
    data["experiments"][3]["stage"] = "R8"
    assert any("stage mismatch" in e for e in validate_plan(data))
