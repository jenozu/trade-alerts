from __future__ import annotations

import json
import os
import subprocess

import pandas as pd
import pytest

import experiment_identity
from experiment_identity import verify_input_lock
from feature_cache import sha256_file
from scripts.derive_linked_sequences import derive, checked_file, checked_objects, verify_preserved_lock
from scripts.run_isolated_feature_build import build_features
from tests.test_isolated_rollover_check import ROOT, frozen_source
from tests.test_linked_sequences import inputs
from fvg import attach_fvg_events_to_bars
from linked_sequences import CHRONOLOGY


def snapshot_producer_commit(tmp_path):
    """Real Git blobs of the tested producer, including pending code changes.

    A private index leaves the worktree/branch/index untouched. Claiming HEAD
    produced dirty source bytes would make the provenance test contradictory.
    """
    env = dict(os.environ, GIT_INDEX_FILE=str(tmp_path / 'producer-index'))
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, env=env, text=True).strip()
    git('read-tree', 'HEAD')
    git('add', 'src', 'scripts')
    return git('commit-tree', git('write-tree'), '-p', git('rev-parse', 'HEAD'),
               '-m', 'test producer snapshot')


@pytest.mark.parametrize('contract', ['fvg_object_linked_v1', CHRONOLOGY])
def test_real_stage_build_to_linked_derivation_and_both_locks(tmp_path, monkeypatch, contract):
    source, cache = frozen_source(tmp_path)
    commit = snapshot_producer_commit(tmp_path)
    monkeypatch.setattr(experiment_identity, 'clean_git_commit', lambda _: commit)
    original = tmp_path / 'full-build'
    build_features(source_root=source, cache_dir=cache, output_dir=original, year=2025,
                   completed_through='2026-01-02T00:00:00Z')
    hashes = {str(p): sha256_file(p) for p in original.rglob('*') if p.is_file()}
    output = tmp_path / 'linked-build'
    result = derive(original, output, sequence_contract=contract)
    assert result['inputs_unchanged']
    assert result['source_rows'] == 180
    assert len(result['segments']) == 2
    assert result['sequence_contract'] == contract
    for name in ('EXPERIMENT_INPUT_LOCK.json', 'LINKED_OUTPUT_LOCK.json'):
        verify_input_lock(json.loads((output / name).read_text()), root=ROOT)
    assert hashes == {str(p): sha256_file(p) for p in original.rglob('*') if p.is_file()}
    for old, new in zip(json.loads((original / 'FEATURE_BUILD_SUMMARY.json').read_text())['segments'], result['segments']):
        before = pd.read_parquet(original / old['features_path'])
        after = pd.read_parquet(output / new['features_path'])
        pd.testing.assert_frame_equal(before, after[before.columns])
        assert after.linked_sequence_contract.eq(contract).all()
    with pytest.raises(ValueError, match='fresh'):
        derive(original, output)
    changed = output / result['segments'][0]['features_path']
    changed.write_bytes(changed.read_bytes() + b'drift')
    with pytest.raises(experiment_identity.ExperimentIdentityError, match='drift'):
        verify_input_lock(json.loads((output / 'LINKED_OUTPUT_LOCK.json').read_text()))


def test_unknown_derivation_contract_fails_before_read_or_write(tmp_path):
    with pytest.raises(ValueError, match='contract'):
        derive(tmp_path / 'missing', tmp_path / 'new', sequence_contract='invented')
    assert not (tmp_path / 'new').exists()


@pytest.mark.parametrize('damage', ['bound', 'event', 'naive'])
def test_retained_lifecycle_must_match_locked_geometry_and_events(damage):
    frame, objects, _ = inputs()
    frame['bullish_fvg_lower'] = 100.
    frame['bullish_fvg_upper'] = 101.
    objects['lower_bound'] = 100.
    objects['upper_bound'] = 101.
    for name in ('first_touch_time', 'full_fill_time', 'inverse_fvg_time'):
        objects[name] = pd.NaT
    frame = attach_fvg_events_to_bars(frame, objects)
    if damage == 'bound':
        objects['upper_bound'] = 102.
    elif damage == 'event':
        objects['retest_hold_time'] = frame.timestamp.iloc[2]
    else:
        objects['retest_hold_time'] = objects.retest_hold_time.dt.tz_localize(None)
    with pytest.raises(ValueError):
        checked_objects(frame, objects)


def test_source_paths_and_output_escape_are_rejected(tmp_path):
    source = tmp_path / 'isolated' / 'build'
    source.mkdir(parents=True)
    outside = tmp_path / 'secret.txt'
    outside.write_text('unrelated')
    with pytest.raises(ValueError):
        checked_file(source, '../../secret.txt')
    with pytest.raises(ValueError, match='alongside'):
        derive(source, tmp_path / 'production' / 'output')


def test_old_producer_code_verified_against_git_blob_after_checkout_changes(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    path = repo / 'code.py'
    path.write_text('original = True\n')
    subprocess.run(['git', 'add', 'code.py'], cwd=repo, check=True)
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    'commit', '-qm', 'original'], cwd=repo, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    item = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
    identity = {'git_commit': commit, 'files': {'code:code.py': {k: v for k, v in item.items() if k != 'path'}}}
    lock = {'identity': identity, 'artifacts': {'code:code.py': item},
            'input_identity_sha256': experiment_identity.canonical_hash(identity)}
    path.write_text('new_revision = True\n')
    verify_preserved_lock(lock, repo)
    identity['files']['code:code.py']['sha256'] = item['sha256'] = '0' * 64
    lock['input_identity_sha256'] = experiment_identity.canonical_hash(identity)
    with pytest.raises(ValueError, match='producer blob'):
        verify_preserved_lock(lock, repo)
