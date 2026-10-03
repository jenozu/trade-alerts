import copy
import json
import subprocess
from pathlib import Path
import pytest
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock, ExperimentIdentityError
from scripts.archive_experiment import archive_experiment


@pytest.fixture
def inputs(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 'test@example.test'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'], check=True)
    files = {'ledger': 'trades.csv', 'strategy': 'strategy.yaml', 'sessions': 'sessions.yaml', 'research_policy': 'policy.yaml'}
    for role, name in files.items():
        (tmp_path / name).write_text('periods:\n  2023: development_research\n' if role == 'research_policy' else 'test\n')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'commit', '-qm', 'fixture'], check=True)
    return dict(experiment_id='EXP-999', root=tmp_path, files=files, years=[2023], contracts=['NQH23'], counts={'bars': None, 'candidates': None, 'trades': 1}, settings={'execution': 'next_bar_open', 'cost': {'enabled': False}, 'slippage': {'enabled': False}})


def test_identity_excludes_timestamp_experiment_label_and_location(inputs):
    first = build_input_lock(**inputs, timestamp='first')
    inputs['experiment_id'] = 'EXP-998'
    inputs['files']['ledger'] = 'copy.csv'
    (inputs['root'] / 'copy.csv').write_bytes((inputs['root'] / 'trades.csv').read_bytes())
    second = build_input_lock(**inputs, timestamp='second')
    assert first['input_identity_sha256'] == second['input_identity_sha256']
    assert first['identity']['coverage']['classification'] == {'2023': 'development_research'}


def test_drift_and_tampering_are_rejected(inputs):
    lock = build_input_lock(**inputs)
    (inputs['root'] / 'trades.csv').write_text('different\n')
    with pytest.raises(ExperimentIdentityError, match='drift'):
        verify_input_lock(lock)
    bad = copy.deepcopy(lock)
    bad['identity']['settings']['cost']['enabled'] = True
    with pytest.raises(ExperimentIdentityError, match='digest'):
        verify_input_lock(bad, check_files=False)


def test_dirty_tracked_code_rejected(inputs):
    (inputs['root'] / 'strategy.yaml').write_text('changed')
    with pytest.raises(ExperimentIdentityError, match='Commit'):
        build_input_lock(**inputs)


def test_immutable_lock_and_archive(inputs):
    lock = build_input_lock(**inputs)
    path = inputs['root'] / 'lock.json'
    write_input_lock(path, lock)
    with pytest.raises(FileExistsError):
        write_input_lock(path, lock)
    reports = inputs['root'] / 'reports'
    reports.mkdir()
    (reports / 'report.md').write_text('evidence')
    archives = inputs['root'] / 'archive'
    manifest = archive_experiment('EXP-999', reports, archives, input_lock=path)
    assert manifest['input_identity_sha256'] == lock['input_identity_sha256']
    assert json.loads((archives / 'EXP-999/EXPERIMENT_INPUT_LOCK.json').read_text()) == lock
    with pytest.raises(FileExistsError):
        archive_experiment('EXP-999', reports, archives, input_lock=path)


@pytest.mark.parametrize('change', ['files', 'counts', 'settings'])
def test_incomplete_input_contract_rejected(inputs, change):
    inputs[change] = {}
    with pytest.raises(ExperimentIdentityError):
        build_input_lock(**inputs)


def test_certification_cannot_replace_old_cache_metadata(tmp_path, monkeypatch):
    from scripts import certify_feature_cache
    from argparse import Namespace
    (tmp_path / 'cache_metadata.json').write_text('old immutable provenance')
    monkeypatch.setattr(certify_feature_cache, 'parse_args', lambda: Namespace(cache_dir=tmp_path))
    with pytest.raises(SystemExit, match='already certified'):
        certify_feature_cache.main()
    assert (tmp_path / 'cache_metadata.json').read_text() == 'old immutable provenance'


def test_settings_and_counts_change_identity(inputs):
    before = build_input_lock(**inputs)
    inputs['settings']['slippage']['enabled'] = True
    after = build_input_lock(**inputs)
    assert before['input_identity_sha256'] != after['input_identity_sha256']
    inputs['counts']['trades'] = 2
    assert build_input_lock(**inputs)['input_identity_sha256'] != after['input_identity_sha256']
