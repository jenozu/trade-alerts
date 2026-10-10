"""Read-only inventory of corrected inputs and unused same-contract history.

Reports evidence, not research eligibility or exchange-calendar completeness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from feature_cache import sha256_file

RAW = ['timestamp', 'contract', 'open', 'high', 'low', 'close', 'volume']
VALUES = RAW[2:]


def read_raw(path):
    frame = pd.read_parquet(path, columns=RAW)
    if frame.empty:
        raise ValueError('Empty raw input')
    times = pd.to_datetime(frame.timestamp, errors='raise')
    if times.dt.tz is None or times.isna().any():
        raise ValueError('Timestamps must be non-null and timezone-aware')
    frame['timestamp'] = times.dt.tz_convert('UTC')
    if (times != times.dt.floor('min')).any():
        raise ValueError('Timestamps must be on minute boundaries')
    if frame.contract.isna().any() or frame.contract.astype(str).str.strip().eq('').any():
        raise ValueError('Contract labels must be nonblank')
    values = frame[VALUES].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (frame.volume < 0).any():
        raise ValueError('OHLCV must be finite with nonnegative volume')
    if (frame.high < frame[['open', 'close', 'low']].max(axis=1)).any() or (
            frame.low > frame[['open', 'close', 'high']].min(axis=1)).any():
        raise ValueError('Invalid OHLC bounds')
    if frame.duplicated(['contract', 'timestamp']).any():
        raise ValueError('Duplicate contract/timestamp rows; resolve before comparison')
    if not frame.timestamp.is_monotonic_increasing:
        raise ValueError('Input timestamps must be ordered')
    return frame


def describe(frame):
    # These are observed gaps, not missing market data: closures/no-trade minutes
    # need separate calendar/provider classification.
    gaps = frame.timestamp.diff().dt.total_seconds().div(60)
    return {'rows': len(frame), 'first_timestamp': frame.timestamp.iloc[0].isoformat(),
            'last_timestamp': frame.timestamp.iloc[-1].isoformat(),
            'observed_gap_count_gt_one_minute': int(gaps.gt(1).sum()),
            'largest_observed_gap_minutes': float(gaps.max()) if len(frame) > 1 else None}


def compare_history(segment, history, evaluation_year):
    contract = segment.contract.iloc[0]
    if segment.contract.nunique() != 1 or history.contract.nunique() != 1 or history.contract.iloc[0] != contract:
        raise ValueError('Comparison requires identical single-contract instruments')
    first = segment.timestamp.iloc[0]
    pre = history.loc[history.timestamp < first]
    evaluation = segment.loc[segment.timestamp.dt.year.eq(evaluation_year)]
    merged = segment.merge(history, on=['contract', 'timestamp'], suffixes=('_used', '_download'))
    mismatches = {c: int(merged[f'{c}_used'].ne(merged[f'{c}_download']).sum()) for c in VALUES}
    span = history.loc[history.timestamp.between(first, segment.timestamp.iloc[-1])]
    absent = span.loc[~span.timestamp.isin(segment.timestamp)]
    return {'unused_pre_segment_rows': len(pre),
            'unused_pre_segment_first_timestamp': None if pre.empty else pre.timestamp.iloc[0].isoformat(),
            'unused_pre_segment_last_timestamp': None if pre.empty else pre.timestamp.iloc[-1].isoformat(),
            'used_rows_before_first_evaluation_bar': None if evaluation.empty else int(
                segment.timestamp.lt(evaluation.timestamp.iloc[0]).sum()),
            'overlap_rows': len(merged), 'overlap_value_mismatches': mismatches,
            'used_rows_absent_from_download': int((~segment.timestamp.isin(history.timestamp)).sum()),
            'download_rows_absent_inside_used_span': len(absent),
            'first_download_row_absent_inside_used_span': None if absent.empty else absent.timestamp.iloc[0].isoformat(),
            'finding': ('OVERLAP_CONFLICT_REVIEW' if any(mismatches.values()) else
                        'EXISTING_HISTORY_NOT_USED' if len(pre) else
                        'NO_EARLIER_HISTORY_IN_THIS_FILE'),
            'warmup_sufficiency': 'NOT_CERTIFIED'}


def audit(build_summaries, contracts_dirs):
    evidence = {}

    def remember(path):
        path = Path(path).resolve()
        digest = sha256_file(path)
        if str(path) in evidence and evidence[str(path)] != digest:
            raise ValueError(f'Input changed during audit: {path}')
        evidence[str(path)] = digest
        return digest

    histories = {}
    inventory, errors = [], []
    for directory in contracts_dirs:
        directory = Path(directory).resolve()
        if not directory.is_dir():
            errors.append({'path': str(directory), 'error': 'Contract directory unavailable'})
            continue
        files = sorted(directory.glob('*_1m.parquet'))
        if not files:
            errors.append({'path': str(directory), 'error': 'No normalized *_1m.parquet files'})
        for path in files:
            try:
                digest = remember(path)
                frame = read_raw(path)
                if frame.contract.nunique() != 1:
                    raise ValueError('Contract download must contain one contract')
                contract = str(frame.contract.iloc[0])
                inventory.append({'path': str(path), 'sha256': digest, 'contract': contract, **describe(frame)})
                histories.setdefault(contract, []).append((path, frame))
            except Exception as exc:
                errors.append({'path': str(path), 'error': str(exc)})

    builds = []
    for summary_path in build_summaries:
        summary_path = Path(summary_path).resolve()
        try:
            remember(summary_path)
            summary = json.loads(summary_path.read_text())
            lock_path = summary_path.parent / 'FEATURE_OUTPUT_LOCK.json'
            remember(lock_path)
            lock = json.loads(lock_path.read_text())
            segments = []
            for number, item in enumerate(summary['segments']):
                path = (summary_path.parent / item['raw_path']).resolve()
                if not path.is_relative_to(summary_path.parent):
                    raise ValueError('Segment path escapes build directory')
                digest = remember(path)
                expected = lock['artifacts'][f'segment_raw:{number}']['sha256']
                if digest != expected:
                    raise ValueError(f'Raw segment hash differs from preserved output lock: {path}')
                frame = read_raw(path)
                if frame.contract.nunique() != 1 or frame.contract.iloc[0] != item['contract']:
                    raise ValueError('Segment contract disagrees with summary')
                if len(frame) != item['rows'] or frame.timestamp.iloc[0].isoformat() != item['first_timestamp'] or frame.timestamp.iloc[-1].isoformat() != item['last_timestamp']:
                    raise ValueError('Segment extent disagrees with summary')
                evaluations = frame.loc[frame.timestamp.dt.year.eq(summary['evaluation_year'])]
                segment = {'contract': item['contract'], 'raw_path': str(path), 'sha256': digest,
                           **describe(frame), 'first_evaluation_bar': None if evaluations.empty else evaluations.timestamp.iloc[0].isoformat(),
                           'context_rows_before_first_evaluation_bar': None if evaluations.empty else int(frame.timestamp.lt(evaluations.timestamp.iloc[0]).sum()),
                           'recorded_feature_warmup': item.get('warmup_context'),
                           'same_contract_downloads': []}
                for download_path, history in histories.get(item['contract'], []):
                    segment['same_contract_downloads'].append({'path': str(download_path),
                        **compare_history(frame, history, summary['evaluation_year'])})
                segment['download_inventory_status'] = ('FOUND' if segment['same_contract_downloads'] else 'NOT_FOUND_IN_SUPPLIED_DIRECTORIES')
                segments.append(segment)
            if sum(s['rows'] for s in segments) != summary['source_rows']:
                raise ValueError('Source row total disagrees with summary')
            builds.append({'summary_path': str(summary_path), 'evaluation_year': summary['evaluation_year'], 'segments': segments})
        except Exception as exc:
            errors.append({'path': str(summary_path), 'error': str(exc)})
    for path, digest in evidence.items():
        if sha256_file(path) != digest:
            raise ValueError(f'Input changed during audit: {path}')
    return {'status': 'INVENTORY_INCOMPLETE' if errors else 'INVENTORY_COMPLETE_COVERAGE_UNCERTIFIED',
            'research_ready': False, 'inputs_unchanged': True, 'builds': builds,
            'contract_file_inventory': inventory, 'errors': errors, 'input_sha256': evidence,
            'limitations': ['No exchange holiday/session completeness certification',
                'Observed gaps include closures and possible no-trade minutes',
                'No minimum warmup policy invented; earlier history is descriptive',
                'No history inserted, features rebuilt, or research experiment run',
                'Missing files in supplied directories do not prove a vendor download is needed',
                'Multiple downloads are compared independently; no automatic merge or source substitution',
                'Raw segment hashes checked; this is not full feature-lock or producer certification']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-summary', action='append', required=True, type=Path)
    parser.add_argument('--contracts-dir', action='append', default=[], type=Path)
    args = parser.parse_args()
    report = audit(args.build_summary, args.contracts_dir)
    # stdout only; the caller may redirect into a NEW file outside the sources.
    print(json.dumps(report, indent=2, allow_nan=False))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
