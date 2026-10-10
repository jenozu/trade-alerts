"""Network-free regression contracts for fail-closed MNQ repair acquisition."""
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'tools/barchart/download_history_repairs.py'
spec = importlib.util.spec_from_file_location('download_history_repairs', MODULE)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def job():
    return {'id':'NMM23_2023-02-01_2023-02-04_1m', 'contract':'NMM23',
            'start_date':'2023-02-01','end_date':'2023-02-04',
            'interval_minutes':1,'filename':'NMM23_2023-02-01_2023-02-04_1m.csv'}


def sample(bad=False):
    rows = 'Time,Open,High,Low,Latest,Volume\n'
    rows += '2023/02/01 09:30,12000.00,12001.00,11999.00,12000.25,5\n'
    rows += ('2023/02/01 09:31,12000.25,12000.50,11999.75,12000.00,-1\n'
             if bad else '2023/02/01 09:31,12000.25,12001.50,12000.00,12001.00,6\n')
    return rows.encode()


def test_fixed_manifest_and_safe_windows(tmp_path):
    root = tmp_path/'repair'
    repair.create_plan(root)
    p = repair.load_plan(root)
    assert len({j['id'] for j in p['jobs']}) == len(p['jobs'])
    assert set(repair.CONTRACT_ROLLS) == {j['contract'] for j in p['jobs']}
    assert all((__import__('datetime').date.fromisoformat(j['end_date']) - __import__('datetime').date.fromisoformat(j['start_date'])).days < 4 for j in p['jobs'])
    assert not p['warmup_certified']
    with pytest.raises(repair.AcquisitionError, match='Nonempty'):
        repair.create_plan(root)
    (root/'request_manifest.json').write_text((root/'request_manifest.json').read_text()+' ')
    with pytest.raises(repair.AcquisitionError, match='changed'):
        repair.load_plan(root)


def test_validate_csv_and_errors():
    result = repair.validate_csv(sample(), job())
    assert result['row_count'] == 2
    assert result['first_timestamp_ct'] == '2023-02-01T09:30:00'
    assert result['sha256'] == repair.sha(sample())
    for payload in (sample(True), b'<html>sign in</html>', b'garbage',
                    sample().replace(b'2023/02/01 09:31',b'2023/02/05 09:31'),
                    sample().replace(b'2023/02/01 09:31',b'2023/02/01 09:30'),
                    sample().replace(b'12001.50',b'11999.00'),
                    sample().replace(b'2023/02/01 09:31',b'2023/02/01 09:30')):
        with pytest.raises(repair.AcquisitionError):
            repair.validate_csv(payload, job())
    sym = sample().replace(b'Time,',b'Symbol,Time,').replace(b'2023/02/01',b'NMU23,2023/02/01')
    with pytest.raises(repair.AcquisitionError, match='symbol'):
        repair.validate_csv(sym, job())


def test_provenance_resume_tamper_and_orphan(tmp_path):
    root = tmp_path/'repair'
    repair.create_plan(root)
    first = repair.request_jobs()[0]
    csv_bytes = sample().replace(b'2023/02/01', first['start_date'].replace('-', '/').encode())
    target = root/'original_csv'/first['filename']
    target.parent.mkdir(parents=True)
    assert first in repair.pending(root)
    # An existing arbitrary file is NEVER accepted by filename alone.
    target.write_bytes(csv_bytes)
    with pytest.raises(repair.AcquisitionError, match='Orphan'):
        repair.pending(root)
    result = repair.validate_csv(csv_bytes, first)
    repair.append_progress(root, first, result, 'https://www.barchart.com/futures/quotes/'+first['contract']+'/historical-download', first['contract']+'.csv')
    assert first not in repair.pending(root)
    assert len(repair.events(root)) == 1
    target.write_bytes(csv_bytes+b'\n')
    with pytest.raises(repair.AcquisitionError, match='changed'):
        repair.pending(root)
    with pytest.raises(FileExistsError):
        repair.write_new(target, b'other')


def test_candle_limit_and_duplicate_rejected():
    repeated = 'Time,Open,High,Low,Latest,Volume\n'
    repeated += ('2023/02/01 09:30,12000,12001,11999,12000,1\n'*2)
    with pytest.raises(repair.AcquisitionError, match='Duplicate'):
        repair.validate_csv(repeated.encode(), job())
    assert repair.main(['status','--root','/path/does/not/exist']) == 1
