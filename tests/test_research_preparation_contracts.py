import copy
import json

from scripts.automation.validate_preparation_plan import DEFAULT_PATH, validate_plan


def _plan():
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def test_five_preparation_contracts_are_nonexecuting():
    assert validate_plan(_plan()) == []


def test_draft_cannot_authorize_execution():
    data = _plan()
    data["execution_enabled"] = True
    assert any("execution" in item for item in validate_plan(data))


def test_draft_cannot_claim_data_certification():
    data = _plan()
    data["datasets_certified"] = True
    assert any("certification" in item for item in validate_plan(data))


def test_required_decisions_cannot_be_removed():
    data = _plan()
    data["experiments"][2]["decisions_required"] = []
    assert any("decisions_required" in item for item in validate_plan(data))


def test_missing_or_duplicate_experiment_is_rejected():
    data = _plan()
    data["experiments"][1]["id"] = "EXP-031"
    assert any("IDs must be" in item for item in validate_plan(data))
