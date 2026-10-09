"""Check archived corrected-control coverage without running a backtest."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from experiment_identity import verify_input_lock


def assess_control(archive_root: Path) -> dict:
    years = []
    for year in (2023, 2024, 2025):
        folder = Path(archive_root) / f'EXP-INTEGRITY-{year}-DIAGNOSTIC'
        locks = [json.loads((folder / name).read_text()) for name in
                 ('EXPERIMENT_INPUT_LOCK.json', 'EXECUTION_OUTPUT_LOCK.json')]
        for lock in locks:
            verify_input_lock(lock, check_files=False)
        for role, item in locks[0]['artifacts'].items():
            if locks[1]['artifacts'].get(role) != item:
                raise ValueError('Input/output lock correspondence differs')
        for role, name in (('summary', 'EXECUTION_AUDIT_SUMMARY.json'),
                           ('decisions', 'decisions.json'),
                           ('effective_strategy', 'effective_strategy.yaml')):
            data = (folder / name).read_bytes()
            item = locks[1]['artifacts'][role]
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError(f'Exported artifact drift: {year}/{name}')
        summary = json.loads((folder / 'EXECUTION_AUDIT_SUMMARY.json').read_text())
        decisions = json.loads((folder / 'decisions.json').read_text())
        if (summary['year_utc'] != year or summary['sequence_contract'] != 'fvg_chronology_v2'
                or summary['effective_backtest']['execution_model'] != 'market_after_retest_confirmation_v2'):
            raise ValueError('Unexpected control contract')
        accepted = sum(d['plan']['candidate'] is not None for d in decisions)
        reasons = Counter(r for d in decisions for r in d['plan']['rejections'])
        if (len(decisions) != summary['eligible_directional_signals']
                or accepted != summary['accepted_plans'] or dict(reasons) != summary['rejection_counts']
                or sum(s['rows'] for s in summary['segments']) != summary['source_rows']
                or sum(s['score_candidate_rows'] for s in summary['segments']) != summary['score_candidate_rows']):
            raise ValueError('Summary/decision counts differ')
        counts = locks[1]['identity']['counts']
        if counts != dict(bars=summary['source_rows'], candidates=len(decisions), trades=summary['simulated_trades']):
            raise ValueError('Locked counts differ')
        if not 0 <= summary['executed_plan_parity_checked'] <= summary['simulated_trades'] <= accepted:
            raise ValueError('Invalid execution counts')
        years.append(dict(year=year, score_candidate_rows=summary['score_candidate_rows'],
                          eligible_directional_signals=len(decisions), accepted_plans=accepted,
                          simulated_trades=summary['simulated_trades'],
                          rejection_categories=dict(sorted(Counter(r.split(':', 1)[0] for r in reasons.elements()).items())),
                          input_identity_sha256=locks[0]['input_identity_sha256'],
                          output_identity_sha256=locks[1]['input_identity_sha256']))
    empty = [y['year'] for y in years if y['accepted_plans'] == 0 or y['simulated_trades'] == 0]
    return dict(status='BLOCKED_EMPTY_CONTROL' if empty else 'COVERAGE_PRESENT_NOT_CERTIFIED',
                selection_run_ready=False, empty_control_years=empty, years=years,
                conclusion=('Additional eligibility-only filters cannot create accepted plans from this '
                            'zero-accepted-plan control; performance differences are not identifiable.'
                            if all(y['accepted_plans'] == 0 for y in years) else
                            'Coverage alone does not certify a candidate or its causal research contract.'),
                limits=['Score rows and directional signals are different counting units.',
                        'Rejection categories overlap; their sum is not a signal count.',
                        'The full scored stream is absent; earlier qualification losses cannot be attributed here.',
                        'VPS-only upstream files are not rehashed by this archive check.',
                        'Historical controls with different semantics are not substituted.'])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path, default=ROOT / 'research-archive')
    args = parser.parse_args()
    result = assess_control(args.archive_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result['empty_control_years'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
