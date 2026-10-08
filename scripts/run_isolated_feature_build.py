"""Full-input contract-isolated feature candidates; no backtests or certification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
import run_pipeline as pipeline
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock
from feature_cache import sha256_file
from rollover import prepare_contract_frame
from scripts.run_isolated_cache_replay import checked_path, historical_timing, verify_producer
from scripts.run_isolated_rollover_check import RAW_COLUMNS, generate_features, verify_features

STATUS = 'FEATURE_CANDIDATE_NOT_RESEARCH_READY'


def split_source(frame):
    """Validate chronological segment metadata; retain original offset IDs/history."""
    if frame.empty:
        raise ValueError('Source must not be empty')
    required = {'contract', 'rollover_segment', 'rollover_boundary'}
    if required - set(frame):
        raise ValueError('Source requires contract, segment and boundary metadata')
    if frame.contract.isna().any() or frame.contract.astype(str).str.strip().eq('').any():
        raise ValueError('Known nonblank contracts are required')
    ts = pd.to_datetime(frame.timestamp)
    if ts.dt.tz is None or ts.isna().any() or ts.duplicated().any() or not ts.is_monotonic_increasing:
        raise ValueError('Source timestamps must be aware, unique and ordered')
    ids = pd.to_numeric(frame.rollover_segment, errors='raise')
    if ids.isna().any() or not np.isfinite(ids).all() or (ids < 0).any() or (ids % 1 != 0).any():
        raise ValueError('Segment IDs must be nonnegative integers')
    if not pd.api.types.is_bool_dtype(frame.rollover_boundary) or frame.rollover_boundary.isna().any():
        raise ValueError('Boundary markers must be non-null booleans')
    contract_change = frame.contract.ne(frame.contract.shift())
    segment_change = ids.ne(ids.shift())
    # The first source row may itself be a roll in a sliced frozen input.
    if not (contract_change.iloc[1:].eq(segment_change.iloc[1:]).all()
            and contract_change.iloc[1:].eq(frame.rollover_boundary.iloc[1:]).all()):
        raise ValueError('Contract/segment transitions must match boundary markers')
    unique = ids.drop_duplicates().astype(int).tolist()
    if unique != list(range(unique[0], unique[0] + len(unique))):
        raise ValueError('Original segment IDs must be contiguous and ordered')
    if frame.loc[contract_change, 'contract'].duplicated().any():
        raise ValueError('A contract must not recur in a later segment')
    for name, expected in (('rollover_from_contract', frame.contract.shift()),
                           ('rollover_to_contract', frame.contract)):
        if name in frame:
            rolls = contract_change.copy()
            rolls.iloc[0] = False
            if not frame.loc[rolls, name].eq(expected.loc[rolls]).fillna(False).all():
                raise ValueError(f'Incorrect {name} at rollover')
    parts = []
    for _, part in frame.groupby('rollover_segment', sort=False):
        part = part.reset_index(drop=True)
        pipeline.require_single_contract_input(part)
        if not np.isfinite(part[['open', 'high', 'low', 'close', 'volume']].to_numpy()).all():
            raise ValueError('Raw OHLCV must be finite and non-null')
        prepare_contract_frame(part)
        parts.append(part)
    return parts


def verify_availability(raw, features):
    for name in ('available_at', 'bar_complete'):
        if name not in features or not raw[name].reset_index(drop=True).eq(
                features[name].reset_index(drop=True)).all():
            raise ValueError('Raw availability/completion clock changed')
    columns = [f'bias_available_at_{tf}' for tf in ('15m', '30m', '1h', '4h', '1d')]
    columns.append('structure_break_available_at')
    if set(columns) - set(features):
        raise ValueError('Missing context availability evidence')
    for name in columns:
        values = pd.to_datetime(features[name], utc=True)
        if (values > features.available_at).any():
            raise ValueError(f'Known context has future availability: {name}')
    return {'availability_preserved': True, 'context_availability_not_future': True,
            'context_availability_columns': columns}


def warmup_context(features):
    """Describe available context, without inventing a trade-eligibility policy."""
    names = ['atr_1m', 'pdh', 'pdl', *[c for c in features if c.startswith('bias_available_at_')]]
    result = {}
    for name in names:
        if name not in features:
            result[name] = {'present': False}
            continue
        valid = features[name].notna()
        first = features.loc[valid, 'timestamp']
        result[name] = {'present': True, 'missing_rows': int((~valid).sum()),
                        'first_non_null_bar': None if first.empty else first.iloc[0].isoformat()}
    return result


def build_features(*, source_root, output_dir, year, completed_through,
                   cache_dir=None, source_manifest=None, repository=ROOT):
    source_root, output_dir, repository = (
        Path(p).resolve() for p in (source_root, output_dir, repository))
    if (cache_dir is None) == (source_manifest is None):
        raise ValueError('Choose exactly one cache directory or explicit source manifest')
    meta_path = (Path(cache_dir).resolve() / 'cache_metadata.json'
                 if cache_dir is not None else Path(source_manifest).resolve())
    if not meta_path.is_relative_to(source_root):
        raise ValueError('Cache or source manifest must be under source root')
    if output_dir.is_relative_to(source_root) or source_root.is_relative_to(output_dir):
        raise ValueError('Output must be separate from preserved source root')
    if output_dir.exists():
        raise FileExistsError('Use a fresh output directory')
    meta_sha = sha256_file(meta_path)
    metadata = json.loads(meta_path.read_text())
    if source_manifest is None:
        differences = verify_producer(metadata, repository)
        provenance = 'verified_cache_producer_manifest'
    else:
        if (metadata.get('source_contract') != 'explicit_preserved_sources_v1'
                or metadata.get('producer_provenance') != 'unavailable'
                or 'git_sha' in metadata or 'feature_manifest' in metadata):
            raise ValueError('Explicit source manifest must declare unavailable old producer provenance')
        differences = None
        provenance = 'unavailable'
    paths = {role: checked_path(source_root, metadata[role]) for role in
             ('input', 'scored_cache', 'strategy_config', 'sessions_config')}
    schema = pq.ParquetFile(paths['input']).schema_arrow.names
    raw = pd.read_parquet(paths['input'], columns=[c for c in RAW_COLUMNS if c in schema])
    raw = historical_timing(raw, completed_through)
    if not raw.bar_complete.all():
        raise ValueError('All source bars must be completed; no silent filtering')
    if isinstance(year, bool) or not isinstance(year, int) or not raw.timestamp.dt.year.eq(year).any():
        raise ValueError('Declared evaluation year must occur in source')
    parts = split_source(raw)
    strategy = pipeline.load_yaml(paths['strategy_config'])
    sessions = pipeline.load_sessions_config(paths['sessions_config'])
    period = int(strategy.get('displacement', {}).get('atr_period', 14))
    if any(len(p) <= period for p in parts):
        raise ValueError('Every segment needs more than one ATR period')
    files = {'source_data': paths['input'], 'scored_cache_control': paths['scored_cache'],
             ('cache_metadata' if source_manifest is None else 'source_manifest'): meta_path,
             'strategy': paths['strategy_config'],
             'sessions': paths['sessions_config'], 'research_policy': repository / 'config/research_policy.yaml',
             'dependencies': repository / 'requirements.txt'}
    code = [*(repository / 'src').glob('*.py'), repository / 'run_pipeline.py',
            *[repository / 'scripts' / name for name in
              ('run_isolated_feature_build.py', 'run_isolated_rollover_check.py', 'run_isolated_cache_replay.py')]]
    files.update({f'code:{p.relative_to(repository)}': p for p in sorted(code)})
    settings = {'execution': {'mode': 'feature_only_full_input', 'evaluation_year': year,
        'warmup': 'all_available_same_contract_history; eligibility_not_certified',
        'timing': 'historical_bar_open_plus_one_minute_v1',
        'completed_through': pd.Timestamp(completed_through).isoformat()}, 'cost': {}, 'slippage': {}}
    lock_args = dict(root=repository, years=sorted(set(raw.timestamp.dt.year)),
        contracts=raw.contract.unique().tolist(), counts={'bars': len(raw), 'candidates': None, 'trades': None},
        settings=settings, unavailable={'research_readiness': STATUS,
            **({'original_cache_producer': 'Unavailable; explicit sources are hashed, not retrospectively certified'}
               if source_manifest is not None else {})})
    source_lock = build_input_lock(experiment_id='DIAGNOSTIC-FULL-INPUT-FEATURE-BUILD', files=files, **lock_args)
    if sha256_file(meta_path) != meta_sha:
        raise ValueError('Source metadata drift during preparation')
    output_dir.mkdir(parents=True, exist_ok=False)
    write_input_lock(output_dir / 'EXPERIMENT_INPUT_LOCK.json', source_lock)
    segments = []
    output_files = dict(files)
    for number, part in enumerate(parts):
        destination = output_dir / f'segment_{number}'
        destination.mkdir()
        raw_path = destination / 'raw_segment.parquet'
        features_path = destination / 'features_scored.parquet'
        part.to_parquet(raw_path, index=False)
        print(f'BUILD SEGMENT {number + 1}/{len(parts)}: {part.contract.iloc[0]}, {len(part)} bars', flush=True)
        features = generate_features(part.copy(), strategy, sessions, destination / 'processed')
        checks = verify_features(part, features, period)
        checks.update(verify_availability(part, features))
        features.to_parquet(features_path, index=False)
        output_files[f'segment_raw:{number}'] = raw_path
        output_files[f'scored_cache_candidate:{number}'] = features_path
        segments.append({'contract': str(part.contract.iloc[0]), 'original_segment': int(part.rollover_segment.iloc[0]),
            'rows': len(part), 'evaluation_year_rows': int(part.timestamp.dt.year.eq(year).sum()),
            'first_timestamp': part.timestamp.iloc[0].isoformat(), 'last_timestamp': part.timestamp.iloc[-1].isoformat(),
            'raw_path': str(raw_path.relative_to(output_dir)), 'features_path': str(features_path.relative_to(output_dir)),
            'feature_sha256': sha256_file(features_path), 'checks': checks, 'warmup_context': warmup_context(features)})
        del features
    verify_input_lock(source_lock, root=repository)
    output_lock = build_input_lock(experiment_id='DIAGNOSTIC-FEATURE-CANDIDATE-OUTPUTS', files=output_files, **lock_args)
    write_input_lock(output_dir / 'FEATURE_OUTPUT_LOCK.json', output_lock)
    verify_input_lock(output_lock, root=repository)
    report = {'status': STATUS, 'inputs_unchanged': True, 'source_rows': len(raw), 'evaluation_year': year,
        'evaluation_year_rows': int(raw.timestamp.dt.year.eq(year).sum()), 'segments': segments,
        'input_identity_sha256': source_lock['input_identity_sha256'],
        'output_identity_sha256': output_lock['input_identity_sha256'],
        'producer_commit': metadata.get('git_sha'), 'source_provenance': provenance,
        'feature_files_differing_from_producer': differences,
        'limitations': ['No backtest or research selection', 'No research cache certification or eligibility override',
            'Only source same-contract history; no invented pre-roll warmup',
            'Context null counts describe availability, not sufficient strategy warmup',
            'No vendor correction-history or sequence-object fidelity certification',
            'Original scored cache remains contaminated preserved control']}
    (output_dir / 'FEATURE_BUILD_SUMMARY.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('FEATURE BUILD: all segments passed; inputs unchanged; research readiness pending', flush=True)
    for item in segments:
        print(item['contract'], item['rows'], 'bars:', item['checks'], flush=True)
    print('Outputs:', output_dir, flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'output-dir', 'completed-through'):
        parser.add_argument('--' + name, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--cache-dir')
    source.add_argument('--source-manifest')
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--acknowledge-historical-export-assumption', action='store_true', required=True)
    args = vars(parser.parse_args())
    args.pop('acknowledge_historical_export_assumption')
    build_features(**args)


if __name__ == '__main__':
    main()
