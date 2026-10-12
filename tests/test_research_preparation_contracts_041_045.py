import json
from scripts.automation.validate_preparation_plan_041_045 import DEFAULT_PATH, validate_plan

def load():
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))

def test_valid_nonexecuting_batch():
    assert validate_plan(load()) == []

def test_execution_remains_disabled():
    data = load()
    data["execution_enabled"] = True
    assert any("execution" in x for x in validate_plan(data))

def test_certification_not_asserted():
    data = load()
    data["datasets_certified"] = True
    assert any("certification" in x for x in validate_plan(data))

def test_malformed_ids_fail():
    data = load()
    data["experiments"][3]["id"] = "EXP-041"
    assert any("IDs must" in x for x in validate_plan(data))

def test_missing_critical_decisions_fail():
    data = load()
    data["experiments"][4]["decisions_required"] = []
    assert any("decisions_required" in x for x in validate_plan(data))

def test_stage_integrity():
    data = load()
    data["experiments"][4]["stage"] = "R9"
    assert any("research stage" in x for x in validate_plan(data))
