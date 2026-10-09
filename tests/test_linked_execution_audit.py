"""Durable shared decisions and independently simulated accepted-path evidence."""
import json

import pandas as pd
import pytest
import yaml

import experiment_identity
from experiment_identity import build_input_lock, write_input_lock, verify_input_lock
from feature_cache import sha256_file
from chronology_sequences import add_chronology_sequences
from linked_sequences import CHRONOLOGY
from scripts.audit_linked_execution import audit
from tests.test_chronology_sequences import case
from tests.test_linked_derivation import ROOT, snapshot_producer_commit


def source_artifact(tmp_path, monkeypatch, direction='long', family='continuation', *, reject=False):
    frame, objects, config, _ = case(direction, family)
    times = pd.date_range('2025-01-29T14:30:00Z', periods=len(frame), freq='min')
    frame['timestamp'] = times
    frame['available_at'] = times + pd.Timedelta(minutes=1)
    objects['creation_time'] = times[1 if family == 'reversal' else 0]
    objects['retest_hold_time'] = times[2]
    frame['contract'] = 'NMH25'
    if reject:
        frame.loc[3:, 'close'] = 99.5
    enriched = add_chronology_sequences(frame, objects)
    source = tmp_path / 'source'
    source.mkdir()
    path = source / 'features.parquet'
    enriched.to_parquet(path, index=False)
    strategy = source / 'strategy.yaml'
    strategy.write_text(yaml.safe_dump(config))
    commit = snapshot_producer_commit(tmp_path)
    monkeypatch.setattr(experiment_identity, 'clean_git_commit', lambda _: commit)
    files = {'strategy': strategy, 'sessions': ROOT / 'config/sessions.yaml',
             'research_policy': ROOT / 'config/research_policy.yaml', 'linked_features:0': path,
             'scored_cache_candidate:0': path}
    lock = build_input_lock(experiment_id='TEST-REAL-LINKED-DERIVATION', root=ROOT,
        files=files, years=[2025], contracts=['NMH25'],
        counts={'bars':len(frame), 'candidates':None, 'trades':None},
        settings={'execution':{}, 'cost':{}, 'slippage':{}})
    write_input_lock(source / 'LINKED_OUTPUT_LOCK.json', lock)
    summary = dict(status='LINKED_FEATURE_CANDIDATE_NOT_RESEARCH_READY',
        sequence_contract=CHRONOLOGY, inputs_unchanged=True, source_rows=len(frame),
        segments=[dict(contract='NMH25', rows=len(frame), features_path='features.parquet',
                       feature_sha256=sha256_file(path))])
    (source / 'LINKED_SEQUENCE_SUMMARY.json').write_text(json.dumps(summary))
    return source


@pytest.mark.parametrize('direction', ['long', 'short'])
@pytest.mark.parametrize('family', ['reversal', 'continuation'])
def test_actual_locked_decisions_and_backtest_acceptance_parity(tmp_path, monkeypatch, direction, family):
    source = source_artifact(tmp_path, monkeypatch, direction, family)
    before = {p.name: sha256_file(p) for p in source.iterdir()}
    output = tmp_path / 'audit'
    result = audit(source, output, year=2025)
    assert result['eligible_directional_signals'] == 1
    assert result['accepted_plans'] == result['simulated_trades'] == 1
    assert result['executed_plan_parity_checked'] == 1
    assert result['research_ready'] is False
    assert before == {p.name: sha256_file(p) for p in source.iterdir()}
    for name in ('EXPERIMENT_INPUT_LOCK.json', 'EXECUTION_OUTPUT_LOCK.json'):
        verify_input_lock(json.loads((output / name).read_text()), root=ROOT)
    assert (output / 'decisions.json').exists()
    with pytest.raises(ValueError, match='fresh'):
        audit(source, output, year=2025)


def test_drift_and_coverage_fails_before_output_creation(tmp_path, monkeypatch):
    source = source_artifact(tmp_path, monkeypatch)
    path = source / 'features.parquet'
    path.write_bytes(path.read_bytes() + b'drift')
    with pytest.raises(ValueError, match='drift'):
        audit(source, tmp_path / 'audit', year=2025)
    assert not (tmp_path / 'audit').exists()


def test_zero_accepted_path_is_explicit_and_output_drift_is_detected(tmp_path, monkeypatch):
    source = source_artifact(tmp_path, monkeypatch, reject=True)
    output = tmp_path / 'audit'
    result = audit(source, output, year=2025)
    assert result['accepted_plans'] == result['simulated_trades'] == 0
    assert result['executed_plan_parity_checked'] == 0
    assert result['research_ready'] is False
    assert not (output / 'diagnostic_trades.csv').exists()
    lock = json.loads((output / 'EXECUTION_OUTPUT_LOCK.json').read_text())
    (output / 'decisions.json').write_text('changed')
    with pytest.raises(experiment_identity.ExperimentIdentityError, match='drift'):
        verify_input_lock(lock)


def test_summary_cannot_change_locked_coverage(tmp_path, monkeypatch):
    source = source_artifact(tmp_path, monkeypatch)
    path = source / 'LINKED_SEQUENCE_SUMMARY.json'
    summary = json.loads(path.read_text())
    summary['source_rows'] += 1
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='coverage'):
        audit(source, tmp_path / 'audit', year=2025)
    assert not (tmp_path / 'audit').exists()
