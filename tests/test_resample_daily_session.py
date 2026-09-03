"""Session-aware Daily resampling tests (Phase 2 R5/R6).

The ``1d`` timeframe must aggregate the CME Globex session (18:00 ET -> 17:00
ET the next calendar day), not a UTC-midnight calendar day. A session that
spans UTC midnight must stay in one daily bar, the bar must be labelled by its
session open and become available only at its session close, and a session is
``bar_complete`` only once the completed prefix contains every required
constituent minute of its half-open ``[18:00, 17:00)`` window:

- a full (finalized) session is complete from its 17:00 ET ``available_at``,
  even when it is the last session in the data;
- a developing session (tail minutes not yet present) is incomplete and is
  never a production input, so bias consumes finalized daily bars only;
- an earlier session with missing constituent minutes is NOT marked complete
  merely because a later session exists;
- bars opening in the daily maintenance window [17:00, 18:00) ET belong to no
  Globex session and are excluded from every daily aggregate.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from bias import calculate_timeframe_bias
from data_clock import filter_as_of
from resample import resample_timeframe

TRADING_TZ = "America/New_York"

# A normal (non-DST) Globex session dated S runs S-1 18:00 ET through S 17:00
# ET: 23 hours = 1380 one-minute constituent bars.
SESSION_MINUTES = 23 * 60


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


def _session_open_et(trading_date: str) -> pd.Timestamp:
    """Globex open instant: 18:00 ET of the prior calendar day."""
    open_et = pd.Timestamp(f"{trading_date} 18:00", tz=TRADING_TZ)
    return open_et - timedelta(days=1)


def _full_session(
    trading_date: str,
    *,
    open_: float = 100.0,
    high: float = 104.0,
    low: float = 99.0,
    close: float = 103.0,
) -> pd.DataFrame:
    """Full 1m constituent coverage of the Globex session dated trading_date."""
    timestamps_utc = pd.date_range(
        _session_open_et(trading_date), periods=SESSION_MINUTES, freq="1min"
    ).tz_convert("UTC")
    n = len(timestamps_utc)
    return pd.DataFrame(
        {
            "timestamp": timestamps_utc,
            "open": [open_] * n,
            "high": [high] * n,
            "low": [low] * n,
            "close": [close] * n,
            "volume": [100.0] * n,
        }
    )


def _session_through(trading_date: str, through_et: str) -> pd.DataFrame:
    """1m bars of the session dated trading_date through the bar opening at
    ``through_et`` (the developing tail of a still-open session)."""
    through = pd.Timestamp(through_et, tz=TRADING_TZ)
    timestamps_utc = pd.date_range(
        _session_open_et(trading_date), through, freq="1min"
    ).tz_convert("UTC")
    n = len(timestamps_utc)
    return pd.DataFrame(
        {
            "timestamp": timestamps_utc,
            "open": [100.0] * n,
            "high": [104.0] * n,
            "low": [99.0] * n,
            "close": [103.0] * n,
            "volume": [100.0] * n,
        }
    )


def test_daily_spans_globex_session_not_utc_midnight() -> None:
    # Session date Sep 1: opens Mon Aug 31 18:00 ET, closes Tue Sep 1 17:00 ET.
    # The 23:59 ET bar and the 00:00 ET bar straddle UTC midnight but must stay
    # in a single daily bar.
    df = _bars(
        [
            ("2026-08-31 18:00", 100.0, 101.0, 99.0, 100.5),  # session open
            ("2026-08-31 23:59", 100.5, 102.0, 100.0, 101.5),  # before UTC midnight
            ("2026-09-01 00:00", 101.5, 103.0, 101.0, 102.0),  # after UTC midnight
            ("2026-09-01 16:59", 102.0, 104.0, 100.0, 103.0),  # last 1m bar
        ]
    )
    result = resample_timeframe(df, "1d")
    bars = result.dataframe

    assert len(bars) == 1, "Globex session must not be split at UTC midnight"
    bar = bars.iloc[0]
    assert bar["timestamp"] == pd.Timestamp("2026-08-31 18:00", tz=TRADING_TZ).tz_convert("UTC")
    assert bar["available_at"] == pd.Timestamp("2026-09-01 17:00", tz=TRADING_TZ).tz_convert("UTC")
    assert bar["open"] == 100.0
    assert bar["high"] == 104.0
    assert bar["low"] == 99.0
    assert bar["close"] == 103.0
    assert bar["volume"] == 400.0
    assert bar["bar_count"] == 4
    # Four minutes of a 1380-minute session: the single session is developing.
    assert bool(bar["bar_complete"]) is False
    assert result.incomplete_bars == 1


def test_daily_rolls_session_date_at_1800_et() -> None:
    # A fully covered session dated Aug 31, then a maintenance-gap bar and the
    # first bars of the next session (dated Sep 1).
    prior = _full_session("2026-08-31")
    gap = _bars([("2026-08-31 17:59", 300.0, 999.0, 1.0, 400.0)])  # no session
    next_session = _bars(
        [
            ("2026-08-31 18:00", 200.0, 201.0, 199.0, 200.0),  # rolls -> session Sep 1
            ("2026-09-01 09:30", 201.0, 205.0, 198.0, 203.0),  # session Sep 1
        ]
    )
    result = resample_timeframe(
        pd.concat([prior, gap, next_session], ignore_index=True), "1d"
    )
    bars = result.dataframe

    assert len(bars) == 2
    # Session date Aug 31 opened Aug 30 18:00 ET; the 17:59 maintenance-gap
    # row is excluded (bar_count stays at the full 1380 minutes, high is not
    # the gap row's 999).
    first = bars.iloc[0]
    assert first["timestamp"] == pd.Timestamp("2026-08-30 18:00", tz=TRADING_TZ).tz_convert("UTC")
    assert first["available_at"] == pd.Timestamp("2026-08-31 17:00", tz=TRADING_TZ).tz_convert("UTC")
    assert first["bar_count"] == SESSION_MINUTES
    assert first["high"] == 104.0
    assert bool(first["bar_complete"]) is True
    # Session date Sep 1 opened Aug 31 18:00 ET and is still developing.
    second = bars.iloc[1]
    assert second["timestamp"] == pd.Timestamp("2026-08-31 18:00", tz=TRADING_TZ).tz_convert("UTC")
    assert second["available_at"] == pd.Timestamp("2026-09-01 17:00", tz=TRADING_TZ).tz_convert("UTC")
    assert bool(second["bar_complete"]) is False
    assert result.incomplete_bars == 1


def test_daily_excludes_maintenance_gap_1700_to_1800_et() -> None:
    # A synthetic 17:30 ET maintenance-gap row (high 999) must not be
    # aggregated into either adjacent Globex daily bar.
    session = _full_session("2026-08-31")
    gap = _bars([("2026-08-31 17:30", 500.0, 999.0, 490.0, 500.0)])
    next_session = _bars([("2026-08-31 18:00", 200.0, 201.0, 199.0, 200.0)])

    bars = resample_timeframe(
        pd.concat([session, gap, next_session], ignore_index=True), "1d"
    ).dataframe

    assert len(bars) == 2
    assert bars.iloc[0]["bar_count"] == SESSION_MINUTES
    assert bars.iloc[0]["high"] == 104.0, "maintenance-gap row contaminated prior Daily"
    assert bars.iloc[1]["bar_count"] == 1


def test_daily_available_at_honors_dst_wall_clock() -> None:
    # US spring-forward 2026-03-08 02:00 ET. The session dated Mar 8 opens
    # Mar 7 18:00 EST (UTC-5) and closes Mar 8 17:00 EDT (UTC-4): 22 real hours.
    df = _bars(
        [
            ("2026-03-07 18:00", 100.0, 101.0, 99.0, 100.0),
            ("2026-03-08 16:59", 100.0, 102.0, 98.0, 101.0),
        ]
    )
    bar = resample_timeframe(df, "1d").dataframe.iloc[0]

    assert bar["timestamp"] == pd.Timestamp("2026-03-07 18:00", tz=TRADING_TZ).tz_convert("UTC")
    assert bar["available_at"] == pd.Timestamp("2026-03-08 17:00", tz=TRADING_TZ).tz_convert("UTC")
    # 17:00 EDT is 21:00 UTC, not a naive open+24h (23:00 UTC).
    assert bar["available_at"] == pd.Timestamp("2026-03-08 21:00:00Z")


def test_final_session_completes_and_is_visible_at_its_1700_available_at() -> None:
    # The verifier repro: a fully covered session that is the LAST in the data
    # must flip to complete exactly at its 17:00 ET available_at and be visible
    # to filter_as_of there -- no later session is needed to prove finality.
    session = _full_session("2026-08-31")  # bars open Aug 30 18:00 .. Aug 31 16:59 ET

    # as_of 16:59 ET sees through the 16:58 bar (1379 of 1380 minutes): the
    # session is still developing and stays hidden even past its own bar open.
    early_prefix = filter_as_of(session, as_of="2026-08-31T16:59:00-04:00")
    early = resample_timeframe(early_prefix, "1d").dataframe
    assert bool(early.iloc[0]["bar_complete"]) is False
    assert filter_as_of(early, as_of="2026-08-31T16:59:00-04:00").empty

    # at exactly 17:00 ET the 16:59 bar (which completes at 17:00) is present:
    # the session has full constituent coverage and its bar is complete.
    full_prefix = filter_as_of(session, as_of="2026-08-31T17:00:00-04:00")
    bars = resample_timeframe(full_prefix, "1d").dataframe
    assert len(bars) == 1
    assert bars.iloc[0]["bar_count"] == SESSION_MINUTES
    assert bool(bars.iloc[0]["bar_complete"]) is True

    visible = filter_as_of(bars, as_of="2026-08-31T17:00:00-04:00")
    assert len(visible) == 1
    assert visible.iloc[0]["timestamp"] == pd.Timestamp(
        "2026-08-30 18:00", tz=TRADING_TZ
    ).tz_convert("UTC")
    assert visible.iloc[0]["available_at"] == pd.Timestamp(
        "2026-08-31 17:00", tz=TRADING_TZ
    ).tz_convert("UTC")


def test_gapped_earlier_session_is_not_complete_merely_because_later_session_exists() -> None:
    # The verifier repro: an earlier session missing its constituent minutes
    # must stay incomplete even though a later session's bars exist in the data.
    df = _bars(
        [
            ("2026-08-30 18:00", 100.0, 101.0, 99.0, 100.0),  # session Aug 31: 1/1380 minutes
            ("2026-08-31 18:00", 200.0, 201.0, 199.0, 200.0),  # session Sep 1 exists
            ("2026-09-01 09:30", 201.0, 205.0, 198.0, 203.0),
        ]
    )
    bars = resample_timeframe(df, "1d").dataframe

    assert len(bars) == 2
    assert not bool(bars.iloc[0]["bar_complete"]), (
        "gapped earlier session marked complete merely because a later session exists"
    )
    assert not bool(bars.iloc[1]["bar_complete"])
    # Neither bucket is a production input at any later as_of.
    assert filter_as_of(
        bars, as_of="2026-09-02T00:00:00-04:00"
    ).empty


def test_finalized_prior_session_is_visible_while_current_session_develops() -> None:
    # A finalized (fully covered, closed) prior session is complete and visible
    # at its available_at; the still-developing current session is not.
    prior = _full_session("2026-08-31")  # session dated Aug 31, fully covered
    current = _session_through("2026-09-01", "2026-09-01 09:59")  # developing
    result = resample_timeframe(
        pd.concat([prior, current], ignore_index=True), "1d"
    )
    assert result.incomplete_bars == 1

    # At Sep 1 17:00 ET the Aug 31 session has closed and is fully covered; it
    # is visible, while the still-developing Sep 1 bar is not.
    visible = filter_as_of(result.dataframe, as_of="2026-09-01T17:00:00-04:00")
    assert len(visible) == 1
    assert visible.iloc[0]["timestamp"] == pd.Timestamp(
        "2026-08-30 18:00", tz=TRADING_TZ
    ).tz_convert("UTC")
    assert bool(visible.iloc[0]["bar_complete"]) is True


def test_daily_bias_consumes_only_finalized_sessions() -> None:
    # Three consecutive fully covered Globex sessions followed by a developing
    # one; the developing session must be dropped by the bias engine
    # (finalized-only daily input).
    finalized = pd.concat(
        [
            _full_session("2026-08-29"),
            _full_session("2026-08-30"),
            _full_session("2026-08-31"),
        ],
        ignore_index=True,
    )
    developing = _session_through("2026-09-01", "2026-09-01 09:59")
    daily = resample_timeframe(
        pd.concat([finalized, developing], ignore_index=True), "1d"
    ).dataframe
    assert len(daily) == 4
    assert int((~daily["bar_complete"]).sum()) == 1

    config = {
        "higher_timeframe_bias": {
            "structure": {
                "left_bars": 1,
                "right_bars": 1,
                "break_buffer_points": 0.0,
            }
        },
        "structure": {"break_buffer_points": 0.0},
    }
    biased = calculate_timeframe_bias(daily, timeframe="1d", config=config)

    # The incomplete developing session is dropped before bias is computed.
    assert len(biased) == 3
    assert biased["bar_complete"].all()
