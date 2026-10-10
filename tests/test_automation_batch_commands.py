import pytest
from scripts.automation.parse_batch_command import parse_batch_command


@pytest.mark.parametrize("raw,verb,ids", [
    ("prepare 31-35", "prepare", ["EXP-031", "EXP-032", "EXP-033", "EXP-034", "EXP-035"]),
    ("prepare 31, 32, 33, 34 and 35", "prepare", ["EXP-031", "EXP-032", "EXP-033", "EXP-034", "EXP-035"]),
    ("status EXP-030, 31, exp_32", "status", ["EXP-030", "EXP-031", "EXP-032"]),
    ("run 31,31,32", "run", ["EXP-031", "EXP-032"]),
])
def test_batch(raw, verb, ids):
    item = parse_batch_command(raw)
    assert (item["verb"], item["experiments"]) == (verb, ids)


@pytest.mark.parametrize("raw", [
    "prepare 35-31", "run 0", "run 1000", "prepare 31,,32",
    "prepare 31; touch /tmp/foo", "push 31-35", "prepare 1-25",
    "prepare 31-", "run", "run 31 && echo bad",
])
def test_rejects_invalid_input(raw):
    with pytest.raises(ValueError):
        parse_batch_command(raw)


def test_prepare_never_authorizes_execution():
    assert parse_batch_command("prepare 31-35")["requires_explicit_execution_authorization"] is False
    assert parse_batch_command("run 31-35")["requires_explicit_execution_authorization"] is True
