import json
from pathlib import Path
import shutil

import pytest

from scripts.check_r7_control import assess_control

ARCHIVES = Path(__file__).resolve().parents[1] / 'research-archive'


def test_authoritative_zero_control_cannot_certify_selection():
    result = assess_control(ARCHIVES)
    assert result['status'] == 'BLOCKED_EMPTY_CONTROL'
    assert result['selection_run_ready'] is False
    assert result['empty_control_years'] == [2023, 2024, 2025]
    assert [y['eligible_directional_signals'] for y in result['years']] == [7, 2, 7]


@pytest.mark.parametrize('name', ['decisions.json', 'EXECUTION_AUDIT_SUMMARY.json', 'effective_strategy.yaml'])
def test_drift_cannot_turn_empty_control_into_research_evidence(tmp_path, name):
    shutil.copytree(ARCHIVES / 'EXP-INTEGRITY-2023-DIAGNOSTIC', tmp_path / 'EXP-INTEGRITY-2023-DIAGNOSTIC')
    path = tmp_path / 'EXP-INTEGRITY-2023-DIAGNOSTIC' / name
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='artifact drift'):
        assess_control(tmp_path)


def test_forged_lock_identity_fails_before_coverage_claim(tmp_path):
    folder = tmp_path / 'EXP-INTEGRITY-2023-DIAGNOSTIC'
    shutil.copytree(ARCHIVES / folder.name, folder)
    path = folder / 'EXECUTION_OUTPUT_LOCK.json'
    lock = json.loads(path.read_text())
    lock['identity']['counts']['trades'] = 1
    path.write_text(json.dumps(lock))
    with pytest.raises(ValueError, match='digest mismatch'):
        assess_control(tmp_path)
