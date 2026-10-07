import json

import pytest

from scripts.automation.parse_run_request import load_request, normalize_experiment


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", "EXP-001"),
        ("exp1", "EXP-001"),
        ("EXP-001", "EXP-001"),
        ("exp_21", "EXP-021"),
        (999, "EXP-999"),
    ],
)
def test_normalize_experiment(raw, expected):
    assert normalize_experiment(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "EXP-000", "EXP-1000", "EXP-1; rm -rf /", "../EXP-001", "one"],
)
def test_normalize_experiment_rejects_unsafe_values(raw):
    with pytest.raises(ValueError):
        normalize_experiment(raw)


def test_load_request_accepts_only_explicit_run(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "action": "run",
                "experiment": "exp7",
                "request_id": "EXP-007-r02",
                "requested_by": "chatgpt",
            }
        ),
        encoding="utf-8",
    )

    parsed = load_request(request)

    assert parsed["action"] == "run"
    assert parsed["experiment"] == "EXP-007"
    assert parsed["request_id"] == "EXP-007-r02"


def test_load_request_rejects_non_run_action(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "action": "prepare",
                "experiment": "EXP-001",
                "request_id": "EXP-001-r01",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly 'run'"):
        load_request(request)


def test_load_request_rejects_shell_like_request_id(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "action": "run",
                "experiment": "EXP-001",
                "request_id": "x;touch-pwned",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="request_id"):
        load_request(request)
