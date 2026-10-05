from __future__ import annotations

import json
import subprocess

import pandas as pd
import pytest

import experiment_identity
from feature_cache import sha256_file
from scripts.run_isolated_feature_build import split_source, build_features, verify_availability
from scripts.run_isolated_rollover_check import ROOT
from tests.test_isolated_rollover_check import raw_bars, frozen_source


def test_split_keeps_every_bar_and_offset_id():
    raw = raw_bars()
    parts = split_source(raw)
    pd.testing.assert_frame_equal(pd.concat(parts, ignore_index=True), raw)
    assert [int(p.rollover_segment.iloc[0]) for p in parts] == [12, 13]


@pytest.mark.parametrize('damage', ['marker', 'segment', 'fraction', 'blank', 'nonfinite'])
def test_bad_source_rejected(damage):
    raw = raw_bars()
    if damage == 'marker':
        raw.loc[90, 'rollover_boundary'] = False
    elif damage == 'segment':
        raw.loc[91, 'rollover_segment'] = 14
    elif damage == 'fraction':
        raw['rollover_segment'] = raw.rollover_segment + .5
    elif damage == 'blank':
        raw.loc[0, 'contract'] = ' '
    else:
        raw.loc[0, 'high'] = float('inf')
    with pytest.raises(ValueError):
        split_source(raw)


def test_availability_rejects_future_context_and_changed_raw_clock():
    from scripts.run_isolated_cache_replay import historical_timing
    raw = historical_timing(raw_bars().iloc[:90], '2026-01-02T00:00:00Z')
    features = raw.copy()
    for name in [f'bias_available_at_{tf}' for tf in ('15m', '30m', '1h', '4h', '1d')] + ['structure_break_available_at']:
        features[name] = pd.Series(pd.NaT, index=features.index, dtype='datetime64[ns, UTC]')
    features.loc[0, 'bias_available_at_1h'] = raw.available_at.iloc[0] + pd.Timedelta(minutes=1)
    with pytest.raises(ValueError, match='future'):
        verify_availability(raw, features)
    features['bias_available_at_1h'] = pd.Series(pd.NaT, index=features.index, dtype='datetime64[ns, UTC]')
    features.loc[0, 'available_at'] += pd.Timedelta(minutes=1)
    with pytest.raises(ValueError, match='clock'):
        verify_availability(raw, features)


def test_full_input_build_real_stages_and_output_lock(tmp_path, monkeypatch):
    source, cache = frozen_source(tmp_path)
    before = {str(p): sha256_file(p) for p in source.rglob('*') if p.is_file()}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    monkeypatch.setattr(experiment_identity, 'clean_git_commit', lambda _: commit)
    output = tmp_path / 'new'
    kwargs = dict(source_root=source, cache_dir=cache, output_dir=output,
                  year=2025, completed_through='2026-01-02T00:00:00Z')
    report = build_features(**kwargs)
    assert report['status'] == 'FEATURE_CANDIDATE_NOT_RESEARCH_READY'
    assert report['source_rows'] == sum(s['rows'] for s in report['segments']) == 180
    assert report['inputs_unchanged']
    assert before == {str(p): sha256_file(p) for p in source.rglob('*') if p.is_file()}
    assert not (output / 'cache_metadata.json').exists()
    assert not list(output.rglob('trades.csv'))
    lock = json.loads((output / 'FEATURE_OUTPUT_LOCK.json').read_text())
    experiment_identity.verify_input_lock(lock, root=ROOT)
    assert 'code:scripts/run_isolated_feature_build.py' in lock['artifacts']
    for s in report['segments']:
        raw = pd.read_parquet(output / s['raw_path'])
        features = pd.read_parquet(output / s['features_path'])
        assert 'atr_1m' not in raw
        assert features.atr_1m.iloc[:13].isna().all()
        assert s['checks']['availability_preserved']
        assert s['warmup_context']['pdh']['missing_rows'] > 0
    with pytest.raises(FileExistsError):
        build_features(**kwargs)
    altered = output / report['segments'][0]['features_path']
    altered.write_bytes(altered.read_bytes() + b'drift')
    with pytest.raises(experiment_identity.ExperimentIdentityError, match='drift'):
        experiment_identity.verify_input_lock(lock)


def test_output_safety_and_incomplete_source(tmp_path):
    source, cache = frozen_source(tmp_path)
    common = dict(source_root=source, cache_dir=cache, year=2025,
                  completed_through='2026-01-02T00:00:00Z')
    with pytest.raises(ValueError, match='separate'):
        build_features(**common, output_dir=source / 'new')
    common['completed_through'] = '2025-03-17T22:01:00Z'
    with pytest.raises(ValueError, match='completed'):
        build_features(**common, output_dir=tmp_path / 'fresh')
    assert not (tmp_path / 'fresh').exists()
