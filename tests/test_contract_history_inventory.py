import json
import subprocess
import sys

import pandas as pd
import pytest

from scripts.audit_contract_history import audit, compare_history, read_raw
from feature_cache import sha256_file


def bars(start='2024-03-18T22:00Z', count=5, contract='NMM24'):
    return pd.DataFrame({'timestamp': pd.date_range(start, periods=count, freq='min'),
        'contract': contract, 'open': 100., 'high': 102., 'low': 99., 'close': 101., 'volume': 10.})


def build(tmp_path):
    directory = tmp_path / 'features'
    directory.mkdir()
    raw = directory / 'raw.parquet'
    frame = bars()
    frame.to_parquet(raw, index=False)
    summary = directory / 'FEATURE_BUILD_SUMMARY.json'
    summary.write_text(json.dumps({'evaluation_year': 2024, 'source_rows': len(frame),
        'segments': [{'contract': 'NMM24', 'rows': len(frame), 'raw_path': raw.name,
        'first_timestamp': frame.timestamp.iloc[0].isoformat(),
        'last_timestamp': frame.timestamp.iloc[-1].isoformat()}]}))
    (directory / 'FEATURE_OUTPUT_LOCK.json').write_text(json.dumps({
        'artifacts': {'segment_raw:0': {'sha256': sha256_file(raw)}}}))
    return summary, raw


def test_unused_history_is_distinguished_from_overlap_conflict():
    used = bars()
    downloaded = bars('2024-03-18T21:58Z', 7)
    result = compare_history(used, downloaded, 2024)
    assert result['unused_pre_segment_rows'] == 2
    assert result['overlap_rows'] == 5
    assert result['finding'] == 'EXISTING_HISTORY_NOT_USED'
    assert result['warmup_sufficiency'] == 'NOT_CERTIFIED'
    downloaded.loc[2, 'volume'] = 11
    assert compare_history(used, downloaded, 2024)['finding'] == 'OVERLAP_CONFLICT_REVIEW'


def test_missing_inside_segment_and_different_instrument():
    history = bars()
    result = compare_history(history.drop(index=2), history, 2024)
    assert result['download_rows_absent_inside_used_span'] == 1
    assert result['first_download_row_absent_inside_used_span'] == history.timestamp.iloc[2].isoformat()
    with pytest.raises(ValueError, match='identical'):
        compare_history(history, bars(contract='NQ'), 2024)


@pytest.mark.parametrize('damage', ['naive', 'duplicate', 'ohlc', 'nonfinite', 'negative', 'unordered', 'minute'])
def test_bad_market_data_is_not_accepted(tmp_path, damage):
    frame = bars()
    if damage == 'naive':
        frame['timestamp'] = frame.timestamp.dt.tz_localize(None)
    elif damage == 'duplicate':
        frame.loc[1, 'timestamp'] = frame.timestamp.iloc[0]
    elif damage == 'ohlc':
        frame.loc[0, 'high'] = 98
    elif damage == 'nonfinite':
        frame.loc[0, 'close'] = float('inf')
    elif damage == 'negative':
        frame.loc[0, 'volume'] = -1
    elif damage == 'unordered':
        frame = frame.iloc[::-1]
    else:
        frame.loc[0, 'timestamp'] += pd.Timedelta(seconds=1)
    path = tmp_path / 'bad.parquet'
    frame.to_parquet(path)
    with pytest.raises(ValueError):
        read_raw(path)


def test_audit_keeps_source_bytes_and_never_certifies_coverage(tmp_path):
    summary, raw = build(tmp_path)
    contracts = tmp_path / 'contracts'
    contracts.mkdir()
    download = contracts / 'NMM24_1m.parquet'
    bars('2024-03-18T21:58Z', 7).to_parquet(download, index=False)
    before = {str(p): sha256_file(p) for p in tmp_path.rglob('*') if p.is_file()}
    result = audit([summary], [contracts])
    assert result['status'] == 'INVENTORY_COMPLETE_COVERAGE_UNCERTIFIED'
    assert result['research_ready'] is False
    assert result['builds'][0]['segments'][0]['same_contract_downloads'][0]['unused_pre_segment_rows'] == 2
    assert before == {str(p): sha256_file(p) for p in tmp_path.rglob('*') if p.is_file()}
    cli = subprocess.run([sys.executable, 'scripts/audit_contract_history.py',
        '--build-summary', str(summary), '--contracts-dir', str(contracts)], capture_output=True, text=True)
    assert cli.returncode == 0
    assert json.loads(cli.stdout) == result


def test_missing_download_is_unknown_not_a_redownload_order(tmp_path):
    summary, _ = build(tmp_path)
    result = audit([summary], [])
    assert result['builds'][0]['segments'][0]['download_inventory_status'] == 'NOT_FOUND_IN_SUPPLIED_DIRECTORIES'
    assert not result['research_ready']


def test_drift_and_missing_paths_are_reported_as_incomplete(tmp_path):
    summary, raw = build(tmp_path)
    raw.write_bytes(raw.read_bytes() + b'drift')
    result = audit([summary], [tmp_path / 'missing'])
    assert result['status'] == 'INVENTORY_INCOMPLETE'
    assert len(result['errors']) == 2
    assert not result['builds']
