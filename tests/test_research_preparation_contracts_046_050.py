import json
from scripts.automation.validate_preparation_plan_046_050 import DEFAULT_PATH, validate_plan

def get_plan():
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))

def test_nonexecuting_contracts_are_valid():
    assert validate_plan(get_plan()) == []

def test_execution_never_implicitly_authorized():
    data = get_plan()
    data["execution_enabled"] = True
    assert any("execution" in error for error in validate_plan(data))

def test_data_integrity_not_presumed():
    data = get_plan()
    data["datasets_certified"] = True
    assert any("certification" in error for error in validate_plan(data))

def test_duplicate_id_rejected():
    data = get_plan()
    data["experiments"][1]["id"] = "EXP-046"
    assert any("IDs must" in error for error in validate_plan(data))

def test_unresolved_decision_fields_required():
    data = get_plan()
    data["experiments"][4]["decisions_required"] = []
    assert any("decisions_required" in error for error in validate_plan(data))

def test_stage_mapping_enforced():
    data = get_plan()
    data["experiments"][0]["stage"] = "R11"
    assert any("research stage" in error for error in validate_plan(data))
