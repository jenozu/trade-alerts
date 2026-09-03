"""Required-session coverage tests (Phase 2 validation V4).

The morning engine needs certain sessions (config-driven via
``validation.required_sessions``) to be present in the data before it can
compute its levels. ``required_session_coverage`` is config-driven, ``as_of``
-aware, and uses the half-open ET session windows from config/sessions.yaml.

Coverage is a completeness check: a required session is ``covered`` only when
every completed 1m slot expected within its half-open window is present --
expected minutes run up to ``min(as_of, window end)``, so an ongoing due
window needs complete coverage only through ``as_of`` while a finalized
window needs its full exact wall-clock/DST-aware constituent minutes. A
window that has not started by ``as_of`` is never covered and never blocks.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from sessions import (
    SessionError,
    load_sessions_config,
    required_session_coverage,
    required_sessions,
)

TRADING_TZ = "America/New_York"


def _config() -> dict:
    return load_sessions_config("config/sessions.yaml")


def _bars(records: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    timestamps_utc = [
        pd.Timestamp(timestamp_et, tz=TRADING_TZ).tz_convert("UTC")
        for timestamp_et, *_ in records
    ]
    return pd.DataFrame(
        {
            "timestamp": timestamps_utc,
            "open": [record[1] for record in records],
            "high": [record[2] for record in records],
            "low": [record[3] for record in records],
            "close": [record[4] for record in records],
            "volume": [100 for _ in records],
        }
    )


def _dense(start_et: str, periods: int | None = None, *, end_et: str | None = None) -> pd.DataFrame:
    """Contiguous 1m bars in ET from ``start_et`` (``periods`` count or up to
    and including ``end_et``), converted to UTC as the pipeline stores them."""
    start = pd.Timestamp(start_et, tz=TRADING_TZ)
    if end_et is not None:
        index = pd.date_range(start, pd.Timestamp(end_et, tz=TRADING_TZ), freq="1min")
    else:
        assert periods is not None
        index = pd.date_range(start, periods=periods, freq="1min")
    return pd.DataFrame(
        {
            "timestamp": index.tz_convert("UTC"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 100,
        }
    )


def _drop(df: pd.DataFrame, timestamp_et: str) -> pd.DataFrame:
    """Return ``df`` without the bar that opens at the given ET time."""
    target = pd.Timestamp(timestamp_et, tz=TRADING_TZ).tz_convert("UTC")
    return df.loc[df["timestamp"] != target].reset_index(drop=True)


def _drop_span(
    df: pd.DataFrame, start_et: str, end_et_exclusive: str
) -> pd.DataFrame:
    """Return ``df`` without every 1m bar opening in [start_et, end_et_exclusive)."""
    start = pd.Timestamp(start_et, tz=TRADING_TZ)
    end = pd.Timestamp(end_et_exclusive, tz=TRADING_TZ)
    span = pd.date_range(start, end - timedelta(minutes=1), freq="1min")
    drop_set = set(span.tz_convert("UTC"))
    return df.loc[~df["timestamp"].isin(drop_set)].reset_index(drop=True)


# Full 1m coverage of the Globex session dated 2026-09-01 through 08:59 ET
# (the last bar completes exactly at as_of 09:00 ET). 900 minutes from the
# Aug 31 18:00 ET session open.
def _full_morning() -> pd.DataFrame:
    return _dense("2026-08-31 18:00", end_et="2026-09-01 08:59")


def test_required_sessions_reads_config() -> None:
    assert required_sessions(_config()) == ["overnight", "london", "asia", "premarket"]


def test_required_sessions_falls_back_to_default() -> None:
    config = _config()
    del config["validation"]["required_sessions"]
    assert required_sessions(config) == ["overnight", "london", "asia", "premarket"]


def test_required_sessions_rejects_unknown_name() -> None:
    config = _config()
    config["validation"]["required_sessions"] = ["overnight", "bogus_session"]
    with pytest.raises(SessionError, match="bogus_session"):
        required_sessions(config)


def test_full_minute_coverage_reports_all_required_sessions_covered() -> None:
    config = _config()
    df = _full_morning()
    report = required_session_coverage(
        df, config, as_of="2026-09-01T09:00:00-04:00"
    )
    assert report.all_covered is True
    assert report.missing == ()
    assert report.all_due_covered is True
    by_name = {entry.session: entry for entry in report.sessions}
    # Expected completed minutes by 09:00 ET: overnight 18:00..08:59 (900),
    # Asia (finalized at 00:00) 20:00..23:59 (240), London (finalized at
    # 05:00) 02:00..04:59 (180), premarket (ongoing) 04:00..08:59 (300).
    assert by_name["overnight"].covered is True
    assert by_name["overnight"].expected_count == 900
    assert by_name["asia"].covered is True
    assert by_name["asia"].expected_count == 240
    assert by_name["london"].covered is True
    assert by_name["london"].expected_count == 180
    assert by_name["premarket"].covered is True
    assert by_name["premarket"].expected_count == 300


def test_sparse_fragments_do_not_cover_required_sessions() -> None:
    """Four isolated minutes spread across the windows must not report the
    sessions covered: unreliable extrema need every expected minute."""
    config = _config()
    df = _bars(
        [
            ("2026-08-31 18:00", 100.0, 101.0, 99.0, 100.0),  # overnight open
            ("2026-08-31 20:00", 100.0, 102.0, 98.0, 100.0),  # asia
            ("2026-09-01 02:00", 100.0, 104.0, 96.0, 100.0),  # london
            ("2026-09-01 04:00", 100.0, 105.0, 95.0, 100.0),  # premarket
        ]
    )
    report = required_session_coverage(
        df, config, as_of="2026-09-01T09:00:00-04:00"
    )
    assert report.all_covered is False
    assert report.all_due_covered is False
    assert set(report.missing) == {"overnight", "london", "asia", "premarket"}
    assert set(report.missing_due) == {"overnight", "london", "asia", "premarket"}
    for entry in report.sessions:
        assert entry.covered is False
        assert entry.due is True
        assert entry.expected_count > 1


def test_missing_london_is_reported() -> None:
    config = _config()
    # Full coverage except the entire London [02:00, 05:00) window.
    df = _drop_span(_full_morning(), "2026-09-01 02:00", "2026-09-01 05:00")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T09:00:00-04:00"
    )
    assert "london" in report.missing
    assert "london" in report.missing_due


def test_coverage_is_as_of_aware() -> None:
    config = _config()
    # Full overnight/Asia coverage through 01:00 ET; London starts at 02:00.
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 00:59")
    # At as_of 01:00 ET London has not started: it is missing presence-wise
    # but not due, so it never drives a no-analysis outcome.
    before = required_session_coverage(
        df, config, as_of="2026-09-01T01:00:00-04:00"
    )
    assert "london" in before.missing
    assert before.missing_due == ()
    assert before.all_due_covered is True
    # Once London is under way (as_of 03:00 ET) with only a fragment present,
    # its missing expected minutes are due and block analysis.
    after = required_session_coverage(
        df, config, as_of="2026-09-01T03:00:00-04:00"
    )
    assert "london" in after.missing
    assert "london" in after.missing_due
    assert after.all_due_covered is False


def test_coverage_uses_half_open_windows() -> None:
    config = _config()
    # A bar exactly at 05:00 ET is the London end boundary and belongs to no
    # London window (half-open [02:00, 05:00)), so London is still missing.
    df = _bars(
        [
            ("2026-08-31 18:00", 100.0, 101.0, 99.0, 100.0),
            ("2026-09-01 05:00", 100.0, 102.0, 99.0, 101.0),
        ]
    )
    report = required_session_coverage(df, config)
    assert "london" in report.missing


def test_coverage_empty_data_reports_all_missing() -> None:
    config = _config()
    empty = pd.DataFrame(
        {
            "timestamp": pd.to_datetime([], utc=True),
            "open": pd.Series(dtype="float64"),
            "high": pd.Series(dtype="float64"),
            "low": pd.Series(dtype="float64"),
            "close": pd.Series(dtype="float64"),
            "volume": pd.Series(dtype="float64"),
        }
    )
    report = required_session_coverage(empty, config)
    assert report.all_covered is False
    assert set(report.missing) == {"overnight", "london", "asia", "premarket"}


def test_not_yet_due_windows_are_absent_from_missing_due() -> None:
    config = _config()
    # Overnight and Asia are fully covered through 01:00 ET; London (02:00)
    # and premarket (04:00) have not started yet.
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 00:59")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T01:00:00-04:00"
    )
    assert report.all_covered is False
    assert set(report.missing) == {"london", "premarket"}
    # Their windows are not due at 01:00 ET, so they must not drive a
    # no-analysis outcome.
    assert report.missing_due == ()
    assert report.all_due_covered is True


def test_due_missing_session_appears_in_missing_due() -> None:
    config = _config()
    # Full overnight/Asia coverage only; evaluated at 05:30 ET: London and
    # premarket have started and produced no bars, so they are due and block.
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 00:59")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T05:30:00-04:00"
    )
    assert "london" in report.missing
    assert "london" in report.missing_due
    assert "premarket" in report.missing_due
    assert report.all_due_covered is False


def test_covered_due_windows_leave_missing_due_empty() -> None:
    config = _config()
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 06:59")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T07:00:00-04:00"
    )
    assert report.missing == ()
    assert report.missing_due == ()
    assert report.all_covered is True
    assert report.all_due_covered is True


def test_single_missing_minute_breaks_coverage() -> None:
    """One absent expected minute (02:30 ET, inside London and overnight)
    makes both windows uncovered and due-blocking."""
    config = _config()
    df = _drop(_full_morning(), "2026-09-01 02:30")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T09:00:00-04:00"
    )
    by_name = {entry.session: entry for entry in report.sessions}
    assert by_name["london"].covered is False
    assert by_name["overnight"].covered is False
    assert by_name["london"].expected_count == 180
    assert by_name["overnight"].expected_count == 900
    # The unaffected windows are still fully covered.
    assert by_name["asia"].covered is True
    assert by_name["premarket"].covered is True
    assert "london" in report.missing_due
    assert "overnight" in report.missing_due
    assert report.all_due_covered is False


def test_finalized_window_needs_its_full_final_minute() -> None:
    """A window that finalizes exactly at as_of still requires the bar that
    completes at that instant (open 09:29 completes at 09:30 ET)."""
    config = _config()
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 09:29")
    report = required_session_coverage(
        df, config, as_of="2026-09-01T09:30:00-04:00"
    )
    assert report.all_covered is True
    gapped = _drop(df, "2026-09-01 09:29")
    report = required_session_coverage(
        gapped, config, as_of="2026-09-01T09:30:00-04:00"
    )
    by_name = {entry.session: entry for entry in report.sessions}
    assert by_name["premarket"].covered is False
    assert by_name["overnight"].covered is False
    assert by_name["overnight"].expected_count == 930
    assert report.all_due_covered is False


def test_ongoing_prefix_requires_coverage_only_through_as_of() -> None:
    """At 09:00 ET the overnight/premarket windows are still open (they end
    at 09:30); full coverage through 08:59 satisfies them without needing
    minutes that have not happened yet."""
    config = _config()
    report = required_session_coverage(
        _full_morning(), config, as_of="2026-09-01T09:00:00-04:00"
    )
    by_name = {entry.session: entry for entry in report.sessions}
    assert by_name["overnight"].due is True
    assert by_name["overnight"].covered is True
    assert by_name["premarket"].due is True
    assert by_name["premarket"].covered is True
    # Their expected horizon stops at as_of, not at the window end 09:30.
    assert by_name["overnight"].expected_count == 900
    assert by_name["premarket"].expected_count == 300


def test_coverage_handles_dst_spring_forward() -> None:
    """US spring-forward 2026-03-08 02:00 ET: the London window start is a
    nonexistent local time that day; its first real minute is 03:00 EDT, so a
    finalized London window contains 120 real minutes, not 180."""
    config = _config()
    # Session dated Mar 8: dense from Mar 7 18:00 EST through Mar 8 08:59 EDT
    # (the pandas tz-aware grid skips the nonexistent 02:00-02:59 minutes).
    df = _dense("2026-03-07 18:00", end_et="2026-03-08 08:59")
    assert len(df) == 840  # 6h + 2h + 6h of real wall-clock minutes
    report = required_session_coverage(
        df, config, as_of="2026-03-08T09:00:00-04:00"
    )
    assert report.missing_due == ()
    by_name = {entry.session: entry for entry in report.sessions}
    assert by_name["london"].covered is True
    assert by_name["london"].due is True
    assert by_name["london"].expected_count == 120
    assert by_name["overnight"].expected_count == 840
    # Removing the first real London minute (03:00 EDT) breaks coverage.
    gapped = _drop(df, "2026-03-08 03:00")
    report = required_session_coverage(
        gapped, config, as_of="2026-03-08T09:00:00-04:00"
    )
    assert "london" in report.missing_due
    assert report.all_due_covered is False


def test_coverage_handles_dst_fall_back_duplicated_minutes() -> None:
    """US fall-back 2026-11-01 02:00 EDT -> 01:00 EST: the overnight window
    that night contains the 01:00-01:59 wall hour twice (once EDT, once EST);
    coverage must require both real fold legs."""
    config = _config()
    # Session dated Nov 1: dense from Oct 31 18:00 EDT through Nov 1 08:59
    # EST. The pandas tz-aware grid emits both fold legs, so the overnight
    # window through 08:59 has 960 real minutes (900 + the extra 60-minute
    # fall-back leg), not 900.
    df = _dense("2026-10-31 18:00", end_et="2026-11-01 08:59")
    assert len(df) == 960
    report = required_session_coverage(
        df, config, as_of="2026-11-01T09:00:00-05:00"
    )
    by_name = {entry.session: entry for entry in report.sessions}
    assert by_name["overnight"].covered is True
    assert by_name["overnight"].expected_count == 960
    assert by_name["asia"].covered is True
    assert by_name["asia"].expected_count == 240
    assert by_name["london"].covered is True
    assert by_name["london"].expected_count == 180
    assert by_name["premarket"].covered is True
    assert by_name["premarket"].expected_count == 300
    assert report.all_due_covered is True

    # Dropping only the pre-fold leg of 01:30 (the 01:30 EDT bar; the
    # 01:30 EST bar remains) must leave the overnight window uncovered.
    # 01:30 EDT == 05:30 UTC; the post-fold 01:30 EST is 06:30 UTC.
    first_leg_utc = pd.Timestamp("2026-11-01T05:30:00Z")
    assert first_leg_utc.tz_convert(TRADING_TZ).hour == 1
    gapped = df.loc[df["timestamp"] != first_leg_utc].reset_index(drop=True)
    report = required_session_coverage(
        gapped, config, as_of="2026-11-01T09:00:00-05:00"
    )
    assert "overnight" in report.missing_due
    assert report.all_due_covered is False


def test_to_dict_exposes_due_and_missing_due() -> None:
    config = _config()
    df = _dense("2026-08-31 18:00", end_et="2026-09-01 00:59")
    payload = required_session_coverage(
        df, config, as_of="2026-09-01T05:30:00-04:00"
    ).to_dict()
    assert "missing_due" in payload
    assert "london" in payload["missing_due"]
    by_name = {entry["session"]: entry for entry in payload["sessions"]}
    assert by_name["london"]["due"] is True
    assert by_name["london"]["covered"] is False
