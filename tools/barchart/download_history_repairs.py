"""Fail-closed, contract-specific Barchart Premier repair acquisition (no ingestion).

Use `plan`, `probe`, `once`, then `resume`.  Browser/UI assumptions are deliberately
revalidated on *every* request.  This is not a data-acceptance or warmup certificate.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo('America/Chicago')
CONTRACT_ROLLS = {
    'NMM23': '2023-03-13', 'NMU23': '2023-06-12', 'NMZ23': '2023-09-11',
    'NMM24': '2024-03-11', 'NMU24': '2024-06-17', 'NMZ24': '2024-09-16',
    'NMH23': '2022-12-12', 'NMH24': '2023-12-11', 'NMH25': '2024-12-16',
    'NMM25': '2025-03-17', 'NMZ25': '2025-09-15', 'NMH26': '2025-12-15',
    'NMU25': '2025-06-16',
}
# 8 weeks is a collection hypothesis, not a certified feature-state warmup.
LOOKBACK_DAYS = 56
OVERLAP_DAYS = 4
CHUNK_DAYS = 4  # <=5,760 one-minute timestamps per inclusive 4-day window
SCHEMA = 1
HEADERS = {'Time', 'Open', 'High', 'Low', 'Latest', 'Volume'}


class AcquisitionError(RuntimeError):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def request_jobs():
    jobs = []
    for contract, roll in sorted(CONTRACT_ROLLS.items(), key=lambda x: (x[1], x[0])):
        start = date.fromisoformat(roll) - timedelta(days=LOOKBACK_DAYS)
        end = date.fromisoformat(roll) + timedelta(days=OVERLAP_DAYS)
        cursor = start
        while cursor <= end:
            last = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
            key = f'{contract}_{cursor.isoformat()}_{last.isoformat()}_1m'
            jobs.append({'id': key, 'contract': contract, 'start_date': cursor.isoformat(),
                         'end_date': last.isoformat(), 'interval_minutes': 1,
                         'filename': key + '.csv'})
            cursor = last + timedelta(days=1)
    return jobs


def plan_object():
    return {'schema': SCHEMA, 'vendor': 'Barchart Premier historical-download',
            'instrument': 'MNQ', 'contract_symbol_convention': 'NM[HMUZ]YY',
            'requested_timezone': 'America/Chicago', 'date_bounds': 'inclusive CT',
            'source_bar_timestamp': 'beginning of minute CT',
            'chunk_days': CHUNK_DAYS, 'min_required_context_sessions': 20,
            'lookback_days_provisional': LOOKBACK_DAYS,
            'overlap_days_after_roll': OVERLAP_DAYS,
            'warmup_certified': False,
            'jobs': request_jobs()}


def write_new(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def load_plan(root: Path):
    data = (root / 'request_manifest.json').read_bytes()
    p = json.loads(data)
    if p != plan_object() or data != canonical(p) + b'\n':
        raise AcquisitionError('Request manifest changed; refuse to resume')
    lock = json.loads((root / 'request_manifest.sha256.json').read_text())
    if lock != {'sha256': sha(data), 'schema': SCHEMA}:
        raise AcquisitionError('Request manifest hash/lock mismatch')
    return p


def create_plan(root: Path):
    if root.exists() and any(root.iterdir()):
        raise AcquisitionError(f'Nonempty work directory: {root} (never overwrite)')
    data = canonical(plan_object()) + b'\n'
    write_new(root / 'request_manifest.json', data)
    write_new(root / 'request_manifest.sha256.json', canonical({'schema': SCHEMA, 'sha256': sha(data)}) + b'\n')
    print(f'Created {len(request_jobs())} fixed requests in {root}')
    print(f'Raw CSVs: {root / "original_csv"}')


def validate_csv(data: bytes, job: dict):
    if not data or len(data) > 20_000_000:
        raise AcquisitionError('Empty or unexpectedly large CSV')
    try:
        text = data.decode('utf-8-sig', errors='strict')
    except UnicodeError as e:
        raise AcquisitionError('Invalid CSV encoding') from e
    if '<html' in text[:1000].lower() or '<!doctype' in text[:1000].lower():
        raise AcquisitionError('HTML response, likely login/challenge/error')
    rows = csv.DictReader(io.StringIO(text, newline=''))
    if rows.fieldnames is None or len(rows.fieldnames) != len(set(rows.fieldnames)) or not HEADERS <= set(rows.fieldnames):
        raise AcquisitionError(f'Unsupported CSV header: {rows.fieldnames}')
    if 'Symbol' in rows.fieldnames and rows.fieldnames.count('Symbol') == 1:
        symbol_key = 'Symbol'
    elif 'symbol' in rows.fieldnames and rows.fieldnames.count('symbol') == 1:
        symbol_key = 'symbol'
    else:
        symbol_key = None
    timestamps = []
    prev = None
    direction = 0
    for row in rows:
        if None in row or any(v is None for v in row.values()):
            raise AcquisitionError('CSV has unexpected columns/field count')
        if symbol_key and row[symbol_key].strip().upper() != job['contract']:
            raise AcquisitionError('CSV row symbol does not match requested contract')
        try:
            moment = datetime.strptime(row['Time'].strip(), '%Y/%m/%d %H:%M')
        except ValueError:
            try:
                moment = datetime.strptime(row['Time'].strip(), '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                raise AcquisitionError(f'Invalid minute timestamp: {row["Time"]!r}') from e
        if not date.fromisoformat(job['start_date']) <= moment.date() <= date.fromisoformat(job['end_date']):
            raise AcquisitionError(f'CSV timestamp outside requested CT dates: {moment}')
        if moment.second or moment.microsecond:
            raise AcquisitionError('Non-minute-aligned timestamp')
        # Avoid inferring nonexistent or ambiguous wall times without evidence.
        aware0 = moment.replace(tzinfo=CHICAGO, fold=0)
        aware1 = moment.replace(tzinfo=CHICAGO, fold=1)
        if aware0.utcoffset() != aware1.utcoffset():
            raise AcquisitionError(f'Ambiguous/nonexistent CT clock: {moment}')
        try:
            o, h, l, c, v = [Decimal(row[x].replace(',', '').strip()) for x in
                              ('Open', 'High', 'Low', 'Latest', 'Volume')]
        except (InvalidOperation, AttributeError) as e:
            raise AcquisitionError('Invalid numeric candle') from e
        if not all(x.is_finite() for x in (o, h, l, c, v)) or min(o, h, l, c) <= 0 or v < 0 or h < max(o, c, l) or l > min(o, c):
            raise AcquisitionError('Invalid candle bounds/volume')
        if prev is not None:
            diff = int((moment - prev).total_seconds() / 60)
            if not diff or abs(diff) < 1:
                raise AcquisitionError('Duplicate minute')
            side = 1 if diff > 0 else -1
            if direction and side != direction:
                raise AcquisitionError('Nonmonotonic timestamp sequence')
            direction = side
            if abs(diff) < job['interval_minutes']:
                raise AcquisitionError('Sub-minute frequency')
        prev = moment
        timestamps.append(moment)
        if len(timestamps) > CHUNK_DAYS * 1440:
            raise AcquisitionError('CSV exceeds maximum safe minute record count')
    if not timestamps:
        raise AcquisitionError('Zero data rows: not accepted as completed')
    # Without at least one adjacent minute, a coarser export cannot be distinguished.
    if len(timestamps) < 2 or not any(abs((a - b).total_seconds()) == 60 for a, b in zip(timestamps, timestamps[1:])):
        raise AcquisitionError('Cannot verify a one-minute CSV: no adjacent minute bars')
    # One-minute data can omit minutes with no eligible trades; a sparse file
    # cannot alone prove the requested minute setting. DOM readback is mandatory.
    return {'row_count': len(timestamps),
            'first_timestamp_ct': min(timestamps).isoformat(),
            'last_timestamp_ct': max(timestamps).isoformat(),
            'sha256': sha(data), 'bytes': len(data),
            'minute_interval_requested': 1, 'completeness_certified': False}


def events(root):
    ledger = root / 'progress.jsonl'
    if not ledger.exists():
        return {}
    done = {}
    for number, line in enumerate(ledger.read_text('utf-8').splitlines(), 1):
        try:
            e = json.loads(line)
        except ValueError as exc:
            raise AcquisitionError(f'Invalid progress record {number}') from exc
        if e.get('status') != 'downloaded_unaccepted' or e.get('id') in done:
            raise AcquisitionError('Unexpected/duplicate progress record')
        done[e['id']] = e
    return done


def pending(root):
    plan = load_plan(root)
    done = events(root)
    ids = {j['id'] for j in plan['jobs']}
    if not set(done) <= ids:
        raise AcquisitionError('Progress contains requests absent from locked plan')
    for job in plan['jobs']:
        target = root / 'original_csv' / job['filename']
        if job['id'] not in done:
            if target.exists():
                raise AcquisitionError(f'Orphan/unverified file; refusing overwrite: {target}')
            continue
        e = done[job['id']]
        if e.get('request') != job or not target.is_file():
            raise AcquisitionError(f'Progress/file identity mismatch: {job["id"]}')
        data = target.read_bytes()
        result = validate_csv(data, job)
        if e['validation'] != result:
            raise AcquisitionError(f'Previously acquired file changed: {target}')
    return [job for job in plan['jobs'] if job['id'] not in done]


def append_progress(root, job, validation, page_url, suggested_filename):
    entry = {'status': 'downloaded_unaccepted', 'id': job['id'], 'request': job,
             'validation': validation, 'page_url': page_url,
             'browser_filename': suggested_filename, 'timestamp_convention': 'CT minute start',
             'warning': 'NOT ACCEPTED: overlap, DST, full session and HTF state still pending'}
    path = root / 'progress.jsonl'
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(canonical(entry).decode() + '\n')
        f.flush()
        os.fsync(f.fileno())


def _only(locator, explanation):
    if locator.count() != 1 or not locator.first.is_visible():
        raise AcquisitionError(f'UI verification ambiguous: {explanation} (matched {locator.count()})')
    return locator.first


def inspect_controls(page):
    """Print non-secret control metadata; do not export cookies/HTML/profile."""
    print('Browser URL:', page.url)
    for el in page.locator('select, input').all():
        if not el.is_visible():
            continue
        typ = (el.get_attribute('type') or '').lower()
        if typ in ('password', 'hidden', 'email', 'search'):
            continue
        record = {x: el.get_attribute(x) for x in ('tagName', 'name', 'id', 'placeholder', 'aria-label', 'type')}
        if el.evaluate('(e) => e.tagName.toLowerCase()') == 'select':
            record['choices'] = el.locator('option').all_text_contents()[:25]
        print('CONTROL', json.dumps(record))


def select_form(page, job):
    """Verify known native controls; never guess among multiple date/interval fields.

    Barchart may change the UI. On change, STOP and use `probe`; do not guess.
    """
    if '/futures/quotes/' + job['contract'] + '/historical-download' not in page.url:
        raise AcquisitionError('Wrong contract URL or login redirected')
    if re.search(r'login|sign.in|captcha|challenge|access.denied', page.url, re.I):
        raise AcquisitionError('Login/challenge detected')
    if not re.search(r'\b' + re.escape(job['contract']) + r'\b', page.locator('body').inner_text(timeout=10000)):
        raise AcquisitionError('Visible page lacks exact contract symbol')
    # An expired individual contract must never silently turn into Nearby/continuous data.
    for box in page.locator('input[type=checkbox]:visible').all():
        nearby_label = (box.get_attribute('aria-label') or '') + ' ' + (box.get_attribute('name') or '')
        parent_text = box.evaluate('(e) => e.parentElement?.innerText || ')
        if re.search(r'nearby|continuous|back.adjust', nearby_label + ' ' + parent_text, re.I) and box.is_checked():
            raise AcquisitionError('Nearby/continuous/back-adjust option selected: refusing individual-contract claim')
    selects = page.locator('select:visible')
    interval_options = []
    frequency_options = []
    for el in selects.all():
        options = [x.strip().lower() for x in el.locator('option').all_text_contents()]
        if any(re.fullmatch(r'1\s*(min(?:ute)?s?)?', o) for o in options) and any('5' in o for o in options):
            interval_options.append(el)
        if any('intraday' in o for o in options) and any('daily' in o for o in options):
            frequency_options.append(el)
    if len(interval_options) != 1 or len(frequency_options) != 1:
        raise AcquisitionError('Native interval/frequency selectors not uniquely identifiable; run probe')
    freq, interval = frequency_options[0], interval_options[0]
    opts = freq.locator('option').all()
    matches = [o.get_attribute('value') for o in opts if o.inner_text().strip().lower() == 'intraday']
    if len(matches) != 1:
        raise AcquisitionError('Intraday choice ambiguous')
    freq.select_option(value=matches[0])
    opts = interval.locator('option').all()
    matches = [o.get_attribute('value') for o in opts if re.fullmatch(r'1\s*(min(?:ute)?s?)?', o.inner_text().strip().lower())]
    if len(matches) != 1:
        raise AcquisitionError('One-minute choice ambiguous')
    interval.select_option(value=matches[0])
    if not ('intraday' in freq.locator('option:checked').inner_text().lower() and
            re.fullmatch(r'1\s*(min(?:ute)?s?)?', interval.locator('option:checked').inner_text().strip().lower())):
        raise AcquisitionError('Frequency/interval readback failed')
    # Date selectors intentionally require explicit field semantics.
    start = _only(page.locator('input[placeholder*="Start" i]:visible, input[aria-label*="Start Date" i]:visible'), 'start date')
    end = _only(page.locator('input[placeholder*="End" i]:visible, input[aria-label*="End Date" i]:visible'), 'end date')
    if start.evaluate('(e)=>e===document.activeElement') or end.evaluate('(e)=>e===document.activeElement'):
        raise AcquisitionError('Unexpected active date control')
    for field, value in ((start, job['start_date']), (end, job['end_date'])):
        field.fill(value)
        field.press('Tab')
    def parse_readback(value):
        v = value.strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                pass
        raise AcquisitionError(f'Unrecognized date readback: {v!r}')
    if parse_readback(start.input_value()) != job['start_date'] or parse_readback(end.input_value()) != job['end_date']:
        raise AcquisitionError('Date readback mismatch after fill')
    buttons = page.locator('a.download-btn:visible').filter(has_text=re.compile(r'^\s*download\s*$', re.I))
    download = _only(buttons, 'exact download control')
    print('VERIFIED', job['contract'], job['start_date'], job['end_date'], 'Intraday, 1 minute, Chicago dates')
    return download


def download_jobs(root: Path, *, mode: str, pause_seconds: float = 3):
    from playwright.sync_api import sync_playwright
    jobs = pending(root)
    if not jobs:
        print('All requests downloaded and reverified (data acceptance still pending)')
        return
    with sync_playwright() as p:
        profile = root / 'browser_profile'
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False, accept_downloads=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            for job in (jobs[:1] if mode in ('once', 'probe') else jobs):
                url = f'https://www.barchart.com/futures/quotes/{job["contract"]}/historical-download'
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(2000)
                if mode == 'probe':
                    input('Log into Barchart manually in the open browser, then press Enter here to inspect the page: ')
                    inspect_controls(page)
                    print('Probe is read-only; no download was attempted. Login manually and rerun probe if needed.')
                    break
                if re.search(r'login|sign.in|captcha|challenge', page.url, re.I):
                    raise AcquisitionError('Manual login/challenge required; stop and rerun after login')
                button = select_form(page, job)
                # Reject any preexisting or orphan download before clicking.
                target = root / 'original_csv' / job['filename']
                if target.exists():
                    raise AcquisitionError('Destination already exists without verified manifest entry')
                staging = root / 'original_csv' / (job['filename'] + '.partial')
                if staging.exists():
                    raise AcquisitionError('Leftover partial file; stop for manual inspection')
                with page.expect_download(timeout=60000) as transfer:
                    button.click()
                download = transfer.value
                if download.failure():
                    raise AcquisitionError('Browser download failed')
                suggested = download.suggested_filename
                if job['contract'].lower() not in suggested.lower() or not suggested.lower().endswith('.csv'):
                    raise AcquisitionError(f'Cannot independently verify symbol in browser filename: {suggested!r}')
                staging.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(str(staging))
                try:
                    data = staging.read_bytes()
                    validation = validate_csv(data, job)
                    write_new(target, data)
                    if sha(target.read_bytes()) != validation['sha256']:
                        raise AcquisitionError('Post-write hash verification failed')
                    append_progress(root, job, validation, page.url, suggested)
                    print('ACQUIRED (UNACCEPTED)', target, validation)
                finally:
                    staging.unlink(missing_ok=True)
                if mode == 'once':
                    print('First live file saved; review progress before running resume.')
                    break
                time.sleep(pause_seconds)
        finally:
            ctx.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('plan', 'probe', 'once', 'resume', 'status'))
    parser.add_argument('--root', type=Path, default=Path.home() / 'Documents' / 'barchart-mnq-repairs')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'plan':
            create_plan(args.root)
        elif args.mode == 'status':
            remaining = pending(args.root)
            print(f'Acquired: {len(request_jobs()) - len(remaining)}; pending: {len(remaining)}; not accepted')
        else:
            download_jobs(args.root, mode=args.mode)
    except (AcquisitionError, FileNotFoundError, PermissionError) as e:
        print('STOP:', e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
