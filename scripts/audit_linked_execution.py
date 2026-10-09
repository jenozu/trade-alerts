"""Locked diagnostic decisions/replays from preserved linked feature artifacts."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
import yaml
from backtest import (MARKET_EXECUTION_MODEL, build_backtest_settings,
                      confirmed_setup_family, market_execution_decision, run_backtest)
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock
from feature_cache import sha256_file
from linked_sequences import CONTRACT, CHRONOLOGY, apply_sequence_contract
from scripts.derive_linked_sequences import checked_file, verify_preserved_lock


def audit(source, output, *, year=2025, repository=ROOT):
    source, output = Path(source).resolve(), Path(output).resolve()
    if (output.exists() or not output.is_relative_to(source.parent) or output == source.parent
            or output.is_relative_to(source) or source.is_relative_to(output)):
        raise ValueError('Audit output must be a fresh sibling directory')
    if isinstance(year, bool) or not isinstance(year, int) or not 2023 <= year <= 2025:
        raise ValueError('This integrity diagnostic supports development years 2023–2025 only')
    summary_path = checked_file(source, 'LINKED_SEQUENCE_SUMMARY.json')
    lock_path = checked_file(source, 'LINKED_OUTPUT_LOCK.json')
    report = json.loads(summary_path.read_text())
    old_lock = json.loads(lock_path.read_text())
    # Updating the review checkout does not change the historical producer.
    verify_preserved_lock(old_lock, repository)
    contract = report.get('sequence_contract')
    segments = report.get('segments', [])
    if (report.get('status') != 'LINKED_FEATURE_CANDIDATE_NOT_RESEARCH_READY'
            or report.get('inputs_unchanged') is not True or contract not in (CONTRACT, CHRONOLOGY)
            or not segments or sum(s['rows'] for s in segments) != report['source_rows']
            or report['source_rows'] != old_lock['identity']['counts']['bars']
            or len({s['contract'] for s in segments}) != len(segments)):
        raise ValueError('Completed linked candidate coverage is required')
    files = {'source_lock': lock_path, 'source_summary': summary_path}
    for role in ('strategy', 'sessions', 'research_policy'):
        files[role] = Path(old_lock['artifacts'][role]['path'])
    for i, segment in enumerate(segments):
        path = checked_file(source, segment['features_path'])
        item = old_lock['artifacts'].get(f'linked_features:{i}', {})
        if (Path(item.get('path', '')).resolve() != path or
                item.get('sha256') != segment['feature_sha256'] or sha256_file(path) != segment['feature_sha256']):
            raise ValueError('Summary must match locked linked feature identity')
        files[f'scored_cache_candidate:{i}'] = path
    files.update({f'code:{p.relative_to(repository)}': p for p in sorted((repository / 'src').glob('*.py'))})
    for script in ('audit_linked_execution.py', 'derive_linked_sequences.py'):
        files[f'code:scripts/{script}'] = repository / 'scripts' / script
    config = deepcopy(yaml.safe_load(files['strategy'].read_text()))
    config.setdefault('backtest', {}).update(execution_model=MARKET_EXECUTION_MODEL, sequence_contract=contract)
    settings = build_backtest_settings(config)
    effective = asdict(settings)
    args = dict(root=repository, years=[year], contracts=[s['contract'] for s in segments],
        counts={'bars':report['source_rows'], 'candidates':None, 'trades':None},
        settings={'execution':{'sequence_contract':contract, 'evaluation_year_utc':year,
                              'retained_context_years':old_lock['identity']['coverage']['years'],
                              'effective_backtest':effective, 'effective_strategy':config},
                  'cost':{k:v for k,v in effective.items() if k.startswith('commission') or k in ('point_value','quantity')},
                  'slippage':{k:v for k,v in effective.items() if 'slippage' in k}},
        unavailable={'realistic_costs':'Actual broker/prop fee schedule not certified',
                     'research_readiness':'Diagnostic only; no strategy selection'})
    lock = build_input_lock(experiment_id='DIAGNOSTIC-LINKED-EXECUTION', files=files, **args)
    output.mkdir(parents=True, exist_ok=False)
    write_input_lock(output / 'EXPERIMENT_INPUT_LOCK.json', lock)
    snapshot = output / 'effective_strategy.yaml'
    snapshot.write_text(yaml.safe_dump(config, sort_keys=True))
    output_files = dict(files, effective_strategy=snapshot)
    decisions, totals, ledger = [], [], []
    rows = candidates = eligible = accepted = parity = 0
    rejections = Counter()
    for i, segment in enumerate(segments):
        print(f'AUDIT SEGMENT {i+1}/{len(segments)}: {segment["contract"]}', flush=True)
        original = pd.read_parquet(files[f'scored_cache_candidate:{i}'])
        if len(original) != segment['rows'] or not original.contract.eq(segment['contract']).all():
            raise ValueError('Linked segment contract/row mismatch')
        frame = apply_sequence_contract(original, config).reset_index(drop=True)
        evaluation = frame.timestamp.dt.tz_convert('UTC').dt.year.eq(year)
        for direction in ('long', 'short'):
            name = f'{direction}_candidate'
            if not pd.api.types.is_bool_dtype(frame[name]) or frame[name].isna().any():
                raise ValueError('Score eligibility must be non-null boolean')
            frame[name] &= evaluation
        selected = frame.long_candidate | frame.short_candidate
        candidates += int(selected.sum())
        rows += len(frame)
        segment_decisions, index = [], {}
        for n, row in frame.loc[selected].iterrows():
            for direction in ('long', 'short'):
                family = confirmed_setup_family(row, direction)
                if not row[f'{direction}_candidate'] or family is None:
                    continue
                if n+1 >= len(frame):
                    decision = dict(decision='NO TRADE', candidate=None, rejections=['next_bar_unavailable'])
                else:
                    decision = market_execution_decision(frame, n, direction, config, settings)
                record = dict(contract=segment['contract'], signal_time=row.timestamp.isoformat(),
                              direction=direction, family=family, plan=decision)
                index[(record['signal_time'],direction)] = decision
                segment_decisions.append(record)
                rejections.update(decision['rejections'])
        eligible += len(segment_decisions)
        valid = sum(d['plan']['candidate'] is not None for d in segment_decisions)
        accepted += valid
        # Avoid walking an entire segment again when there is no accepted path.
        trades = run_backtest(frame, config) if valid else pd.DataFrame()
        for trade in trades.to_dict('records'):
            key = (trade['signal_time'].isoformat(), trade['direction'])
            if json.loads(trade['execution_plan']) != index[key]:
                raise ValueError('Executed plan differs from independent shared decision')
            parity += 1
        if not trades.empty:
            trades = trades.copy()
            trades['contract'] = segment['contract']
            ledger.append(trades)
        decisions.extend(segment_decisions)
        totals.append(dict(contract=segment['contract'], rows=len(frame),
            score_candidate_rows=int(selected.sum()), eligible_directional_signals=len(segment_decisions),
            accepted_plans=valid, simulated_trades=len(trades)))
    decisions_path = output / 'decisions.json'
    decisions_path.write_text(json.dumps(decisions, indent=2, allow_nan=False) + '\n')
    output_files['decisions'] = decisions_path
    if ledger:
        ledger_path = output / 'diagnostic_trades.csv'
        pd.concat(ledger, ignore_index=True).to_csv(ledger_path, index=False)
        output_files['ledger_diagnostic'] = ledger_path
    if rows != report['source_rows']:
        raise ValueError('Audit did not retain all source rows')
    verify_input_lock(lock, root=repository)
    verify_preserved_lock(old_lock, repository)
    result = dict(status='LINKED_EXECUTION_DIAGNOSTIC_NOT_RESEARCH_READY', research_ready=False,
        sequence_contract=contract, year_utc=year, inputs_unchanged=True, source_rows=rows,
        score_candidate_rows=candidates, eligible_directional_signals=eligible, accepted_plans=accepted,
        simulated_trades=sum(len(t) for t in ledger), executed_plan_parity_checked=parity,
        rejection_counts=dict(rejections), segments=totals, effective_backtest=effective,
        limitations=['Costs are recorded frozen settings, not verified actual fees',
                     'Accepted standalone decisions may not execute due to side tie/one-position policy',
                     'No historical accepted-path proof when simulated_trades is zero',
                     'Development diagnostic only; no optimization or research readiness certification'])
    result_path = output / 'EXECUTION_AUDIT_SUMMARY.json'
    result_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    output_files['summary'] = result_path
    args['counts'] = {'bars':rows, 'candidates':eligible, 'trades':result['simulated_trades']}
    final = build_input_lock(experiment_id='DIAGNOSTIC-LINKED-EXECUTION-OUTPUTS', files=output_files, **args)
    write_input_lock(output / 'EXECUTION_OUTPUT_LOCK.json', final)
    verify_input_lock(final, root=repository)
    print(json.dumps({k:result[k] for k in ('sequence_contract','eligible_directional_signals','accepted_plans',
                                        'simulated_trades','executed_plan_parity_checked')}, sort_keys=True), flush=True)
    print('EXECUTION AUDIT: completed; inputs unchanged; both locks verified; research readiness pending', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-build', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--year', type=int, default=2025)
    options = parser.parse_args()
    audit(options.source_build, options.output_dir, year=options.year)
