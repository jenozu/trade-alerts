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


class _FakeOption:
    def __init__(self, text, value):
        self.text, self.value = text, value

    def inner_text(self):
        return self.text

    def get_attribute(self, attr):
        assert attr == 'value'
        return self.value


class _FakeOptions:
    def __init__(self, options):
        self.options = options

    def all(self):
        return self.options


class _FakeSelected:
    def __init__(self, frequency):
        self.frequency = frequency

    def inner_text(self):
        return self.frequency.selected


class _FakeFrequency:
    first = property(lambda self: self)

    def __init__(self, choices):
        self.choices = choices
        self.selected = ''

    def count(self):
        return 1

    def is_visible(self):
        return True

    def locator(self, selector):
        if selector == 'option':
            return _FakeOptions([_FakeOption(t, v) for t, v in self.choices])
        if selector == 'option:checked':
            return _FakeSelected(self)
        raise AssertionError(selector)

    def select_option(self, *, value):
        self.selected = next(text for text, v in self.choices if v == value)


class _FakeInterval:
    first = property(lambda self: self)

    def __init__(self, *, visible=True, readback='1'):
        self.visible = visible
        self.readback = readback
        self.value = ''
        self.tabbed = False

    def count(self):
        return 1 if self.visible else 0

    def is_visible(self):
        return self.visible

    def fill(self, value):
        self.value = value

    def press(self, key):
        assert key == 'Tab'
        self.tabbed = True

    def input_value(self):
        return self.readback


class _FakePage:
    def __init__(self, choices, *, interval_visible=True, interval_readback='1'):
        self.freq = _FakeFrequency(choices)
        self.interval = _FakeInterval(visible=interval_visible, readback=interval_readback)
        self.aggregation_looked_up_after_selection = False

    def locator(self, selector):
        if selector == 'select[aria-label="Select frequency"]:visible':
            return self.freq
        if selector == 'input[name="aggregation"][type="number"][aria-label="Enter intraday minutes"]:visible':
            self.aggregation_looked_up_after_selection = self.freq.selected == 'Intraday'
            return self.interval
        raise AssertionError(selector)


def test_barchart_numeric_aggregation_selected_after_exact_intraday():
    page = _FakePage([('Intraday Nearby', 'nearby'), ('Daily', 'daily'),
                      ('Intraday', 'intraday')])
    repair.configure_intraday_minutes(page)
    assert page.freq.selected == 'Intraday'  # never Nearby/continuous
    assert page.aggregation_looked_up_after_selection  # field may be dynamically rendered
    assert page.interval.value == '1'
    assert page.interval.tabbed  # commit input change


def test_barchart_numeric_aggregation_fail_closed():
    choices = [('Intraday', 'intraday'), ('Intraday Nearby', 'nearby')]
    with pytest.raises(repair.AcquisitionError, match='numeric intraday-minute'):
        repair.configure_intraday_minutes(_FakePage(choices, interval_visible=False))
    with pytest.raises(repair.AcquisitionError, match='readback'):
        repair.configure_intraday_minutes(_FakePage(choices, interval_readback='5'))
    with pytest.raises(repair.AcquisitionError, match='Exact Intraday'):
        repair.configure_intraday_minutes(_FakePage([('Intraday Nearby', 'nearby')]))

def test_headless_cli_modes_and_forwarding(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(repair, 'download_jobs',
                        lambda root, *, mode, headless=False, inspect_on_error=False, browser_channel='chromium':
                        calls.append((root, mode, headless, inspect_on_error, browser_channel)))
    for mode, flag in [('once', True), ('resume', True), ('once', False),
                       ('resume', False), ('probe', False)]:
        args = [mode, '--root', str(tmp_path)] + (['--headless'] if flag else [])
        assert repair.main(args) == 0
    assert calls == [(tmp_path, 'once', True, False, 'chromium'),
                     (tmp_path, 'resume', True, False, 'chromium'),
                     (tmp_path, 'once', False, False, 'chromium'),
                     (tmp_path, 'resume', False, False, 'chromium'),
                     (tmp_path, 'probe', False, False, 'chromium')]


def test_headless_not_allowed_for_probe_or_plan(tmp_path):
    for mode in ('probe', 'plan', 'status'):
        with pytest.raises(SystemExit) as exc:
            repair.main([mode, '--root', str(tmp_path), '--headless'])
        assert exc.value.code == 2


def test_headless_launch_reuses_persistent_browser_profile(monkeypatch, tmp_path):
    import sys
    import types

    launched = []
    closed = []

    class FakePage:
        def on(self, event, callback):
            pass

        def goto(self, *_args, **_kwargs):
            raise repair.AcquisitionError('Synthetic stop before a real page loads')

    class FakeContext:
        pages = [FakePage()]

        def on(self, event, callback):
            pass

        def close(self):
            closed.append(True)

    class FakeChromium:
        def launch_persistent_context(self, profile, **kwargs):
            launched.append((profile, kwargs))
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    module = types.ModuleType('playwright.sync_api')
    module.sync_playwright = FakePlaywright
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', module)
    monkeypatch.setattr(repair, 'pending', lambda root: [repair.request_jobs()[0]])
    with pytest.raises(repair.AcquisitionError, match='Synthetic stop'):
        repair.download_jobs(tmp_path, mode='once', headless=True)
    assert launched == [(str(tmp_path / 'browser_profile'),
                         {'headless': True, 'accept_downloads': True})]
    assert closed == [True]


def test_inspect_on_error_is_visible_once_only(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(repair, 'download_jobs',
                        lambda root, *, mode, headless=False, inspect_on_error=False, browser_channel='chromium':
                        calls.append((mode, headless, inspect_on_error, browser_channel)))
    assert repair.main(['once', '--root', str(tmp_path), '--inspect-on-error']) == 0
    assert calls == [('once', False, True, 'chromium')]
    for args in (['resume', '--inspect-on-error'],
                 ['once', '--headless', '--inspect-on-error'],
                 ['probe', '--inspect-on-error'],
                 ['status', '--inspect-on-error']):
        with pytest.raises(SystemExit) as exc:
            repair.main(args + ['--root', str(tmp_path)])
        assert exc.value.code == 2


def test_browser_failure_reports_reason_and_waits_before_close(monkeypatch, tmp_path):
    import sys
    import types

    evidence = {'clicked': 0, 'closed': 0, 'ack': 0}

    class FakeDownload:
        suggested_filename = 'NMH23.csv'

        def failure(self):
            return 'canceled'

    class FakeTransfer:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        @property
        def value(self):
            return FakeDownload()

    class FakePage:
        url = 'https://www.barchart.com/futures/quotes/NMH23/historical-download'

        def on(self, event, callback):
            pass

        def goto(self, *_args, **_kwargs):
            pass

        def wait_for_timeout(self, *_args):
            pass

        def expect_download(self, *_args, **_kwargs):
            return FakeTransfer()

    class FakeButton:
        def click(self):
            evidence['clicked'] += 1

    class FakeContext:
        pages = [FakePage()]

        def on(self, event, callback):
            pass

        def close(self):
            evidence['closed'] += 1

    class FakeChromium:
        def launch_persistent_context(self, *_args, **kwargs):
            assert kwargs['headless'] is False
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    module = types.ModuleType('playwright.sync_api')
    module.sync_playwright = FakePlaywright
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', module)
    job = repair.request_jobs()[0]
    monkeypatch.setattr(repair, 'pending', lambda root: [job])
    monkeypatch.setattr(repair, 'select_form', lambda page, request: FakeButton())

    def acknowledge(prompt):
        assert 'Press Enter' in prompt
        assert evidence['closed'] == 0  # browser stays visible until user finishes
        evidence['ack'] += 1
        return ''

    monkeypatch.setattr('builtins.input', acknowledge)
    with pytest.raises(repair.AcquisitionError, match="Playwright: 'canceled'.*no CSV saved"):
        repair.download_jobs(tmp_path, mode='once', inspect_on_error=True)
    assert evidence == {'clicked': 1, 'closed': 1, 'ack': 1}
    assert not (tmp_path / 'original_csv').exists()


def test_browser_channel_profile_isolation_and_launch(monkeypatch, tmp_path):
    import sys
    import types

    launched = []
    closed = []

    class FakePage:
        def on(self, event, callback):
            pass

        def goto(self, *_args, **_kwargs):
            raise repair.AcquisitionError('Stop after launch')

    class FakeContext:
        pages = [FakePage()]

        def on(self, event, callback):
            pass

        def close(self):
            closed.append(True)

    class FakeChromium:
        def launch_persistent_context(self, profile, **options):
            launched.append((profile, options))
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    module = types.ModuleType('playwright.sync_api')
    module.sync_playwright = FakePlaywright
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', module)
    monkeypatch.setattr(repair, 'pending', lambda root: [repair.request_jobs()[0]])

    for channel in ('chromium', 'chrome', 'msedge'):
        with pytest.raises(repair.AcquisitionError, match='Stop after launch'):
            repair.download_jobs(tmp_path, mode='once', browser_channel=channel)

    assert launched == [
        (str(tmp_path / 'browser_profile'), {'headless': False, 'accept_downloads': True}),
        (str(tmp_path / 'browser_profile_chrome'),
         {'headless': False, 'accept_downloads': True, 'channel': 'chrome'}),
        (str(tmp_path / 'browser_profile_msedge'),
         {'headless': False, 'accept_downloads': True, 'channel': 'msedge'}),
    ]
    assert len(closed) == 3


def test_browser_channel_forwarded_from_cli(monkeypatch, tmp_path):
    observed = []
    monkeypatch.setattr(repair, 'download_jobs',
                        lambda root, *, mode, headless, inspect_on_error, browser_channel:
                        observed.append((mode, headless, browser_channel)))
    assert repair.main(['probe', '--root', str(tmp_path), '--channel', 'chrome']) == 0
    assert repair.main(['once', '--root', str(tmp_path), '--channel', 'msedge',
                        '--headless']) == 0
    assert observed == [('probe', False, 'chrome'), ('once', True, 'msedge')]


def test_preexisting_browser_closure_does_not_hide_original_failure(monkeypatch, tmp_path):
    import sys
    import types

    class TargetClosedError(Exception):
        pass

    class FakePage:
        def on(self, event, callback):
            pass

        def goto(self, *_args, **_kwargs):
            raise repair.AcquisitionError('Original navigation failure')

    class FakeContext:
        pages = [FakePage()]

        def on(self, event, callback):
            pass

        def close(self):
            raise TargetClosedError('Target page, context or browser has been closed')

    class FakeChromium:
        def launch_persistent_context(self, *_args, **_kwargs):
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    module = types.ModuleType('playwright.sync_api')
    module.sync_playwright = FakePlaywright
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', module)
    monkeypatch.setattr(repair, 'pending', lambda root: [repair.request_jobs()[0]])
    with pytest.raises(repair.AcquisitionError, match='Original navigation failure'):
        repair.download_jobs(tmp_path, mode='once')
