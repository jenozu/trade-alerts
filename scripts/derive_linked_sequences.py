"""Derive linked confirmation from preserved isolated artifacts, no backtest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
import yaml
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock
from feature_cache import sha256_file
from fvg import attach_fvg_events_to_bars
from linked_sequences import CONTRACT, CHRONOLOGY, add_linked_sequences, apply_sequence_contract
from chronology_sequences import add_chronology_sequences


def verify_preserved_lock(lock, repository):
    """Verify original code via Git blobs after updating the review checkout.

    Data/config files must still match on disk. This does not recertify the
    original lock against a new producer or ignore changed code contents.
    """
    verify_input_lock(lock, check_files=False)
    for role, item in lock['artifacts'].items():
        if role.startswith('code:'):
            path = role[len('code:'):]
            content = subprocess.check_output(['git', 'show', f"{lock['identity']['git_commit']}:{path}"], cwd=repository)
            if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
                raise ValueError(f'Original producer blob mismatch: {role}')
        else:
            path = Path(item['path'])
            if not path.is_file() or path.stat().st_size != item['bytes'] or sha256_file(path) != item['sha256']:
                raise ValueError(f'Preserved input drift: {role}')


def checked_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Artifact must be an existing file within the source build')
    return path


def checked_objects(frame, objects):
    """Check retained lifecycle records against locked creation/event evidence."""
    if not objects.empty:
        required = {'lower_bound', 'upper_bound', 'creation_time', 'direction',
                    'first_touch_time', 'full_fill_time', 'inverse_fvg_time'}
        if required - set(objects):
            raise ValueError('Incomplete saved FVG lifecycle schema')
        if frame.timestamp.duplicated().any():
            raise ValueError('Source feature timestamps must be unique')
        creation_lookup = frame.set_index('timestamp')
        for gap in objects.to_dict('records'):
            timestamp = pd.Timestamp(gap['creation_time'])
            if timestamp.tzinfo is None:
                raise ValueError('FVG creation time must be aware')
            if timestamp not in creation_lookup.index or gap['direction'] not in ('bullish', 'bearish'):
                raise ValueError('FVG creation must match one source bar')
            side = gap['direction']
            row = creation_lookup.loc[timestamp]
            if (not bool(row[f'{side}_fvg_created']) or
                    gap['lower_bound'] != row[f'{side}_fvg_lower'] or
                    gap['upper_bound'] != row[f'{side}_fvg_upper']):
                raise ValueError('FVG creation geometry differs from locked features')
    parsed = objects.copy()
    for name in ('first_touch_time', 'retest_hold_time', 'full_fill_time', 'inverse_fvg_time'):
        if name in parsed:
            values = [pd.NaT if pd.isna(v) else pd.Timestamp(v) for v in parsed[name]]
            if any(pd.notna(v) and v.tzinfo is None for v in values):
                raise ValueError('FVG event times must be aware')
            parsed[name] = pd.to_datetime(values, utc=True)
    projected = attach_fvg_events_to_bars(frame, parsed)
    for side in ('bullish', 'bearish'):
        for event in ('first_touch', 'retest_hold', 'full_fill'):
            name = f'{side}_fvg_{event}'
            if name not in frame or not projected[name].eq(frame[name]).all():
                raise ValueError(f'Saved lifecycle differs from locked events: {name}')
    return parsed


def derive(source, output, *, repository=ROOT, sequence_contract=CONTRACT):
    if sequence_contract not in (CONTRACT, CHRONOLOGY):
        raise ValueError('Unknown derivation sequence contract')
    source, output = Path(source).resolve(), Path(output).resolve()
    if not output.is_relative_to(source.parent) or output == source.parent:
        raise ValueError('Output must stay alongside the isolated source build')
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Output must be a fresh directory separate from the source build')
    summary_path = checked_file(source, 'FEATURE_BUILD_SUMMARY.json')
    report = json.loads(summary_path.read_text())
    if report.get('status') != 'FEATURE_CANDIDATE_NOT_RESEARCH_READY' or report.get('inputs_unchanged') is not True:
        raise ValueError('A completed isolated feature candidate build is required')
    original_locks = []
    files = {'source_summary': summary_path}
    for name in ('EXPERIMENT_INPUT_LOCK.json', 'FEATURE_OUTPUT_LOCK.json'):
        path = checked_file(source, name)
        lock = json.loads(path.read_text())
        verify_preserved_lock(lock, repository)
        original_locks.append(lock)
        files[f'source_lock:{name}'] = path
    segments = report['segments']
    if not segments:
        raise ValueError('No source segments')
    if (sum(s['rows'] for s in segments) != report['source_rows'] or
            len({s['contract'] for s in segments}) != len(segments) or
            report['source_rows'] != original_locks[1]['identity']['counts']['bars']):
        raise ValueError('Source summary coverage must match the original lock')
    for role in ('strategy', 'sessions', 'research_policy'):
        files[role] = Path(original_locks[0]['artifacts'][role]['path'])
    for number, segment in enumerate(segments):
        features = checked_file(source, segment['features_path'])
        if sha256_file(features) != segment['feature_sha256']:
            raise ValueError('Source summary feature hash mismatch')
        lock_role = f'scored_cache_candidate:{number}'
        locked = original_locks[1]['artifacts'].get(lock_role, {})
        if locked.get('sha256') != segment['feature_sha256'] or Path(locked.get('path', '')).resolve() != features:
            raise ValueError('Summary segment must match the locked feature artifact')
        files[f'scored_cache_candidate:{number}'] = features
        files[f'source_lifecycle:{number}'] = checked_file(source, str(features.parent.relative_to(source) / 'processed/fvg/fvg_lifecycle.csv'))
    files.update({f'code:{path.relative_to(repository)}': path for path in sorted((repository / 'src').glob('*.py'))})
    files['code:scripts/derive_linked_sequences.py'] = repository / 'scripts/derive_linked_sequences.py'
    execution = {'mode': 'linked_sequence_derivation_only', 'sequence_contract': sequence_contract}
    if sequence_contract == CHRONOLOGY:
        strategy = yaml.safe_load(files['strategy'].read_text())
        execution.update(lookback_bars=10,
                         break_buffer_points=strategy.get('structure', {}).get('break_buffer_points', .25))
    args = dict(root=repository, years=original_locks[0]['identity']['coverage']['years'],
                contracts=[s['contract'] for s in segments],
                counts={'bars': report['source_rows'], 'candidates': None, 'trades': None},
                settings={'execution': execution,
                          'cost': {}, 'slippage': {}}, unavailable={'research_readiness': 'NOT_CERTIFIED'})
    lock = build_input_lock(experiment_id='DIAGNOSTIC-LINKED-SEQUENCE-DERIVATION', files=files, **args)
    output.mkdir(parents=True, exist_ok=False)
    write_input_lock(output / 'EXPERIMENT_INPUT_LOCK.json', lock)
    retained = []
    output_files = dict(files)
    for number, segment in enumerate(segments):
        print(f'DERIVE SEGMENT {number + 1}/{len(segments)}: {segment["contract"]}', flush=True)
        frame = pd.read_parquet(files[f'scored_cache_candidate:{number}'])
        if len(frame) != segment['rows'] or 'contract' not in frame or not frame.contract.eq(segment['contract']).all():
            raise ValueError('Segment contract/row coverage mismatch')
        try:
            objects = pd.read_csv(files[f'source_lifecycle:{number}'])
        except pd.errors.EmptyDataError:
            objects = pd.DataFrame()
        objects = checked_objects(frame, objects)
        linked = (add_chronology_sequences(frame, objects, lookback_bars=execution['lookback_bars'],
                    break_buffer_points=execution['break_buffer_points'])
                  if sequence_contract == CHRONOLOGY else add_linked_sequences(frame, objects))
        pd.testing.assert_frame_equal(linked[frame.columns], frame)
        apply_sequence_contract(linked, {'backtest': {'sequence_contract': sequence_contract}})
        destination = output / f'segment_{number}'
        destination.mkdir()
        path = destination / 'features_linked.parquet'
        linked.to_parquet(path, index=False)
        output_files[f'linked_features:{number}'] = path
        counts = {f'{side}_{family}': int(linked[f'{side}_linked_{family}_entry_valid_event'].sum())
                  for side in ('bullish', 'bearish') for family in ('reversal', 'continuation')}
        retained.append({'contract': segment['contract'], 'rows': len(frame),
            'features_path': str(path.relative_to(output)), 'feature_sha256': sha256_file(path),
            'linked_event_counts_all_source_history': counts})
    verify_input_lock(lock, root=repository)
    for old in original_locks:
        verify_preserved_lock(old, repository)
    final_lock = build_input_lock(experiment_id='DIAGNOSTIC-LINKED-SEQUENCE-OUTPUTS', files=output_files, **args)
    write_input_lock(output / 'LINKED_OUTPUT_LOCK.json', final_lock)
    verify_input_lock(final_lock, root=repository)
    result = {'status': 'LINKED_FEATURE_CANDIDATE_NOT_RESEARCH_READY', 'sequence_contract': sequence_contract,
        'inputs_unchanged': True, 'source_rows': report['source_rows'], 'segments': retained,
        'input_identity_sha256': lock['input_identity_sha256'], 'output_identity_sha256': final_lock['input_identity_sha256'],
        'limitations': ['No backtest, research certification or eligibility override',
            'Retained lifecycle CSVs were not included in the prior output lock; now locked and checked against source events/geometry',
            ('Completed-bar chronology is explicit; historical execution and research readiness are not certified'
             if sequence_contract == CHRONOLOGY else
             'Same-row core ordering and separate acceptance/micro-BOS remain unresolved')]}
    (output / 'LINKED_SEQUENCE_SUMMARY.json').write_text(json.dumps(result, indent=2) + '\n')
    label = 'CHRONOLOGY' if sequence_contract == CHRONOLOGY else 'LINKED'
    print(f'{label} DERIVATION: completed; original inputs unchanged; research readiness pending', flush=True)
    print(output, flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-build', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--sequence-contract', choices=[CONTRACT, CHRONOLOGY], default=CONTRACT)
    options = parser.parse_args()
    derive(options.source_build, options.output_dir, sequence_contract=options.sequence_contract)
