"""Contract tests for the Phase 2 session vertical slice.

Approved strategy contract (2026-09-03):
- London fixed ET [02:00, 05:00), Asia fixed ET [20:00, 00:00),
  overnight [18:00, 09:30); all America/New_York, half-open.
- London/Asia/overnight extrema develop causally from completed bars and
  finalize at window end. Asia is an internal/secondary reference, not a
  premarket-breakout boundary.
- Previous close = prior RTH close; half-back = (prior RTH high + prior RTH
  low) / 2; PD levels are available at the next 18:00 ET session open.
- The futures week is half-open Sunday 18:00 ET through Friday 17:00 ET;
  current week high/low develop causally from the week start, and bars in the
  weekend gap after the Friday close update no futures-week extreme.
- Cash open (rth_open) is known only after the 09:30 bar completes at 09:31.
- config/sessions.yaml is authoritative for session windows, level
  availability times, opening-range definitions, and the generated
  timeframes.
"""

from datetime import date

import pandas as pd

from resample import TIMEFRAME_RULES
from sessions import enrich_with_sessions, load_sessions_config

TRADING_TZ = "America/New_York"


def _config() -> dict:
    return load_sessions_config("config/sessions.yaml")


def _make_bars(records: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
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


def _row_at(df: pd.DataFrame, timestamp_et: str) -> pd.Series:
    target = pd.Timestamp(timestamp_et, tz=TRADING_TZ)
    rows = df.loc[df["timestamp_et"] == target]
    assert len(rows) == 1, f"Expected exactly one row at {target}, found {len(rows)}"
    return rows.iloc[0]


# --------------------------------------------------------------------------
# Asia session: window mask, session identity, causal development, finalization
# --------------------------------------------------------------------------


def test_asia_window_is_fixed_et_2000_to_midnight():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                ("2026-08-31 18:00", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 19:59", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 20:00", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 23:59", 100.0, 101.0, 99.0, 100.0),
                ("2026-09-01 00:00", 100.0, 101.0, 99.0, 100.0),
                ("2026-09-01 00:59", 100.0, 101.0, 99.0, 100.0),
                ("2026-09-01 02:00", 100.0, 101.0, 99.0, 100.0),
            ]
        ),
        _config(),
        causal=True,
    )

    assert bool(_row_at(enriched, "2026-08-31 20:00")["is_asia"]) is True
    assert bool(_row_at(enriched, "2026-08-31 23:59")["is_asia"]) is True
    assert bool(_row_at(enriched, "2026-08-31 18:00")["is_asia"]) is False
    assert bool(_row_at(enriched, "2026-08-31 19:59")["is_asia"]) is False
    assert bool(_row_at(enriched, "2026-09-01 00:00")["is_asia"]) is False
    assert bool(_row_at(enriched, "2026-09-01 00:59")["is_asia"]) is False

    # Asia bars in the 20:00-24:00 ET evening belong to the NEXT futures
    # session (the session date rolled at 18:00 ET).
    evening = _row_at(enriched, "2026-08-31 20:00")
    assert evening["session_date"] == date(2026, 9, 1)


def test_asia_high_low_develop_causally_and_finalize_at_midnight():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Session 2026-09-01 Globex open; not Asia.
                ("2026-08-31 18:00", 149.0, 150.0, 148.0, 149.0),
                ("2026-08-31 19:59", 148.0, 149.0, 147.0, 148.0),
                # Asia window [20:00, 00:00).
                ("2026-08-31 20:00", 100.0, 120.0, 110.0, 115.0),
                ("2026-08-31 21:00", 115.0, 130.0, 105.0, 120.0),
                ("2026-08-31 23:00", 120.0, 118.0, 90.0, 100.0),
                ("2026-08-31 23:59", 100.0, 115.0, 95.0, 110.0),
                # After midnight: not Asia, but the Asia level is now final.
                ("2026-09-01 00:00", 110.0, 140.0, 80.0, 120.0),
                # Later premarket extremes must not move the finalized Asia H/L.
                ("2026-09-01 09:29", 200.0, 300.0, 70.0, 250.0),
            ]
        ),
        _config(),
        causal=True,
    )

    before = _row_at(enriched, "2026-08-31 19:59")
    at_2000 = _row_at(enriched, "2026-08-31 20:00")
    at_2100 = _row_at(enriched, "2026-08-31 21:00")
    at_2359 = _row_at(enriched, "2026-08-31 23:59")
    at_midnight = _row_at(enriched, "2026-09-01 00:00")
    at_0929 = _row_at(enriched, "2026-09-01 09:29")

    # Nothing before the Asia window, and no finalized value during it.
    assert pd.isna(before["developing_ash"])
    assert pd.isna(before["developing_asl"])
    assert pd.isna(before["ash"])
    assert pd.isna(before["asl"])

    # Developing values are causal: at 20:00 only the 20:00 bar is known.
    assert at_2000["developing_ash"] == 120.0
    assert at_2000["developing_asl"] == 110.0
    assert at_2100["developing_ash"] == 130.0
    assert at_2100["developing_asl"] == 105.0
    assert at_2359["developing_ash"] == 130.0
    assert at_2359["developing_asl"] == 90.0

    # Finalized Asia H/L is available at the window close (00:00 ET). The bar
    # opening at 23:59 completes exactly at 00:00, so it is the first row that
    # may carry the finalized level; rows completing before the close (21:00,
    # 23:00) still show NaN. The value never includes the 00:00 bar's own
    # extreme (140/80) or the 09:29 premarket extreme (300/70).
    assert pd.isna(at_2100["ash"])
    assert pd.isna(at_2100["asl"])
    assert pd.isna(_row_at(enriched, "2026-08-31 23:00")["ash"])
    assert pd.isna(_row_at(enriched, "2026-08-31 23:00")["asl"])
    assert at_2359["ash"] == 130.0
    assert at_2359["asl"] == 90.0
    assert at_midnight["ash"] == 130.0
    assert at_midnight["asl"] == 90.0
    assert at_0929["ash"] == 130.0
    assert at_0929["asl"] == 90.0


# --------------------------------------------------------------------------
# Previous close and half-back
# --------------------------------------------------------------------------


def test_previous_close_and_half_back_use_prior_rth_session():
    enriched, levels = enrich_with_sessions(
        _make_bars(
            [
                # Prior (Aug 31) RTH session: PDH=115, PDL=95, close=106.
                ("2026-08-31 09:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 15:59", 105.0, 115.0, 95.0, 106.0),
                # Next futures session (Sep 1) starts at 18:00 ET Aug 31.
                ("2026-08-31 18:00", 107.0, 108.0, 106.0, 107.0),
                ("2026-09-01 09:30", 110.0, 120.0, 105.0, 118.0),
            ]
        ),
        _config(),
        causal=True,
    )

    first_session = _row_at(enriched, "2026-08-31 09:30")
    evening = _row_at(enriched, "2026-08-31 18:00")
    next_rth = _row_at(enriched, "2026-09-01 09:30")

    # No prior session exists for the first session in the dataset.
    assert pd.isna(first_session["pdh"])
    assert pd.isna(first_session["pdl"])
    assert pd.isna(first_session["pdc"])
    assert pd.isna(first_session["half_back"])

    # PD levels, previous close, and half-back are known at the next 18:00 ET
    # session open and do not depend on the developing Sep 1 RTH session.
    assert evening["pdh"] == 115.0
    assert evening["pdl"] == 95.0
    assert evening["pdc"] == 106.0
    assert evening["half_back"] == 105.0
    assert next_rth["pdc"] == 106.0
    assert next_rth["half_back"] == 105.0
    assert next_rth["pdh"] == 115.0
    assert next_rth["pdl"] == 95.0

    # The levels table carries the new fields too.
    for column in ["pdh", "pdl", "pdc", "half_back"]:
        assert column in levels.columns


# --------------------------------------------------------------------------
# Current futures week high/low
# --------------------------------------------------------------------------


def test_week_high_low_follow_futures_week_boundaries():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Prior futures week (anchor Sunday 2026-08-23 18:00 ET).
                ("2026-08-24 09:30", 200.0, 300.0, 100.0, 250.0),
                # Weekend gap: the prior week ended Friday 2026-08-28 17:00 ET
                # and the next week has not started yet (Sunday 18:00 ET), so
                # this bar must not update any futures-week extreme.
                ("2026-08-30 17:59", 200.0, 301.0, 99.0, 250.0),
                # New futures week starts Sunday 2026-08-30 18:00 ET.
                ("2026-08-30 18:00", 95.0, 100.0, 88.0, 96.0),
                ("2026-08-31 09:30", 150.0, 250.0, 100.0, 240.0),
                # Friday close of the week (Friday 2026-09-04 17:00 ET end).
                ("2026-09-04 16:59", 300.0, 400.0, 50.0, 390.0),
                # Next futures week (anchor Sunday 2026-09-06 18:00 ET).
                ("2026-09-06 18:00", 115.0, 120.0, 110.0, 118.0),
            ]
        ),
        _config(),
        causal=True,
    )

    weekend_gap = _row_at(enriched, "2026-08-30 17:59")
    new_week_start = _row_at(enriched, "2026-08-30 18:00")
    monday = _row_at(enriched, "2026-08-31 09:30")
    friday = _row_at(enriched, "2026-09-04 16:59")
    next_week_start = _row_at(enriched, "2026-09-06 18:00")

    # The Sunday 17:59 bar lies between the Friday 17:00 week close and the
    # Sunday 18:00 open. No futures week is open, so no current-week extreme
    # is exposed and the bar cannot contaminate the prior week's H/L.
    assert pd.isna(weekend_gap["week_high"])
    assert pd.isna(weekend_gap["week_low"])

    # A new futures week resets the running extrema at Sunday 18:00 ET.
    assert new_week_start["week_high"] == 100.0
    assert new_week_start["week_low"] == 88.0
    assert monday["week_high"] == 250.0
    assert monday["week_low"] == 88.0
    assert friday["week_high"] == 400.0
    assert friday["week_low"] == 50.0

    # And the following Sunday 18:00 ET resets them again (no carry-over).
    assert next_week_start["week_high"] == 120.0
    assert next_week_start["week_low"] == 110.0


# --------------------------------------------------------------------------
# Cash open availability (rth_open only after the 09:30 bar completes)
# --------------------------------------------------------------------------


def test_cash_open_is_available_only_after_0930_bar_completes():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                ("2026-08-31 09:29", 100.0, 110.0, 90.0, 105.0),
                ("2026-08-31 09:30", 215.0, 220.0, 210.0, 216.0),
                ("2026-08-31 09:31", 216.0, 217.0, 214.0, 215.0),
                ("2026-08-31 09:34", 217.0, 219.0, 215.0, 218.0),
            ]
        ),
        _config(),
        causal=True,
    )

    at_0929 = _row_at(enriched, "2026-08-31 09:29")
    at_0930 = _row_at(enriched, "2026-08-31 09:30")
    at_0931 = _row_at(enriched, "2026-08-31 09:31")
    at_0934 = _row_at(enriched, "2026-08-31 09:34")

    assert pd.isna(at_0929["rth_open"])
    # The 09:30 cash-open bar completes at exactly 09:31 ET, so the 09:30 row
    # is the first row that may carry the cash open (a completed-bar analysis
    # at as_of 09:31 sees through the 09:30 bar).
    assert at_0930["rth_open"] == 215.0
    assert at_0931["rth_open"] == 215.0
    assert at_0934["rth_open"] == 215.0


# --------------------------------------------------------------------------
# config/sessions.yaml is authoritative
# --------------------------------------------------------------------------


def test_config_authority_for_session_windows():
    config = _config()
    config["sessions"]["asia"] = {"start": "19:00", "end": "21:00"}
    config["sessions"]["london"] = {"start": "06:00", "end": "07:00"}

    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                ("2026-08-31 06:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 07:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 18:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 19:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 20:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 21:00", 100.0, 101.0, 99.0, 100.0),
            ]
        ),
        config,
        causal=True,
    )

    assert bool(_row_at(enriched, "2026-08-31 06:30")["is_london"]) is True
    assert bool(_row_at(enriched, "2026-08-31 07:30")["is_london"]) is False
    assert bool(_row_at(enriched, "2026-08-31 18:30")["is_asia"]) is False
    assert bool(_row_at(enriched, "2026-08-31 19:30")["is_asia"]) is True
    assert bool(_row_at(enriched, "2026-08-31 20:30")["is_asia"]) is True
    assert bool(_row_at(enriched, "2026-08-31 21:00")["is_asia"]) is False


def test_config_authority_for_level_availability_times():
    config = _config()
    config["level_availability"]["pmh_pml"] = "10:00"
    config["level_availability"]["rth_open"] = "09:45"

    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                ("2026-09-01 09:29", 210.0, 220.0, 190.0, 215.0),
                ("2026-09-01 09:30", 215.0, 216.0, 214.0, 215.5),
                ("2026-09-01 09:44", 218.0, 222.0, 213.0, 220.0),
                ("2026-09-01 09:45", 220.0, 221.0, 215.0, 219.0),
                ("2026-09-01 09:59", 222.0, 225.0, 210.0, 223.0),
                ("2026-09-01 10:00", 223.0, 230.0, 205.0, 226.0),
            ]
        ),
        config,
        causal=True,
    )

    # pmh_pml availability moved from 09:30 to 10:00 by config. The row opening
    # at 09:59 completes at 10:00, so it is the first row carrying pmh.
    assert pd.isna(_row_at(enriched, "2026-09-01 09:44")["pmh"])
    assert _row_at(enriched, "2026-09-01 09:59")["pmh"] == 220.0
    assert _row_at(enriched, "2026-09-01 10:00")["pmh"] == 220.0

    # rth_open availability moved from 09:31 to 09:45 by config. The row
    # opening at 09:44 completes at 09:45, so it is the first row carrying it.
    assert pd.isna(_row_at(enriched, "2026-09-01 09:30")["rth_open"])
    assert _row_at(enriched, "2026-09-01 09:44")["rth_open"] == 215.0
    assert _row_at(enriched, "2026-09-01 09:45")["rth_open"] == 215.0


def test_config_authority_for_opening_ranges():
    config = _config()
    config["opening_ranges"]["availability"]["or5"] = "09:36"
    config["opening_ranges"]["durations_minutes"] = [5, 30]

    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                ("2026-09-01 09:30", 215.0, 216.0, 214.0, 215.5),
                ("2026-09-01 09:31", 216.0, 217.0, 214.0, 216.0),
                ("2026-09-01 09:32", 217.0, 218.0, 213.0, 217.0),
                ("2026-09-01 09:33", 218.0, 220.0, 215.0, 219.0),
                ("2026-09-01 09:34", 220.0, 225.0, 216.0, 224.0),
                ("2026-09-01 09:35", 224.0, 221.0, 215.0, 220.0),
                ("2026-09-01 09:36", 220.0, 222.0, 214.0, 221.0),
            ]
        ),
        config,
        causal=True,
    )

    # OR5 completion availability moved from 09:35 to 09:36 by config. The row
    # opening at 09:35 completes at 09:36, so it is the first row carrying OR5.
    assert _row_at(enriched, "2026-09-01 09:35")["or5_high"] == 225.0
    assert _row_at(enriched, "2026-09-01 09:35")["or5_low"] == 213.0
    assert _row_at(enriched, "2026-09-01 09:36")["or5_high"] == 225.0
    assert _row_at(enriched, "2026-09-01 09:36")["or5_low"] == 213.0

    # Durations come from config: 5 and 30 exist, 15 does not.
    assert "or5_high" in enriched.columns
    assert "or30_high" in enriched.columns
    assert "or15_high" not in enriched.columns


def test_config_authority_for_generated_timeframes():
    config = _config()
    generated = config["timeframes"]["generated"]
    master = config["timeframes"]["master"]

    assert master == "1m"
    assert "2m" in generated
    assert "3m" in generated
    assert len(generated) == len(set(generated)), "generated timeframes must be unique"
    assert set(generated) == set(TIMEFRAME_RULES) - {master}


# --------------------------------------------------------------------------
# Previous-day level availability (config previous_day_levels.available_from)
# --------------------------------------------------------------------------


def test_previous_day_levels_are_visible_during_next_day_premarket():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Prior (Aug 31) RTH session: PDH=115, PDL=95, close=106.
                ("2026-08-31 09:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 15:59", 105.0, 115.0, 95.0, 106.0),
                # Next futures session (Sep 1): evening and premarket rows.
                ("2026-08-31 18:00", 107.0, 108.0, 106.0, 107.0),
                ("2026-09-01 09:00", 108.0, 110.0, 107.0, 109.0),
                ("2026-09-01 09:25", 109.0, 111.0, 108.0, 110.0),
            ]
        ),
        _config(),
        causal=True,
    )

    # Approved contract: PD levels become authoritative at the 18:00 ET Globex
    # open and must be visible at 09:00 and 09:25 the next morning.
    for timestamp in ["2026-08-31 18:00", "2026-09-01 09:00", "2026-09-01 09:25"]:
        row = _row_at(enriched, timestamp)
        assert row["pdh"] == 115.0
        assert row["pdl"] == 95.0
        assert row["pdc"] == 106.0
        assert row["half_back"] == 105.0


def test_config_authority_for_previous_day_level_availability():
    config = _config()
    config["previous_day_levels"]["available_from"] = "18:30"

    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Prior (Aug 31) RTH session: PDH=115, PDL=95, close=106.
                ("2026-08-31 09:30", 100.0, 101.0, 99.0, 100.0),
                ("2026-08-31 15:59", 105.0, 115.0, 95.0, 106.0),
                # Next futures session (Sep 1), opening evening.
                ("2026-08-31 18:00", 107.0, 108.0, 106.0, 107.0),
                ("2026-08-31 18:29", 107.0, 109.0, 106.0, 108.0),
                ("2026-08-31 18:30", 108.0, 110.0, 107.0, 109.0),
                ("2026-09-01 09:25", 109.0, 111.0, 108.0, 110.0),
            ]
        ),
        config,
        causal=True,
    )

    # 18:00-18:29 ET evening bars run before the configured 18:30 authority
    # time. The 18:29 bar completes at exactly 18:30, so it is the first row on
    # which PD levels are visible; from the 18:30 row onward and through the
    # next morning they remain visible.
    assert pd.isna(_row_at(enriched, "2026-08-31 18:00")["pdh"])
    assert pd.isna(_row_at(enriched, "2026-08-31 18:00")["pdc"])
    assert _row_at(enriched, "2026-08-31 18:29")["pdh"] == 115.0
    assert _row_at(enriched, "2026-08-31 18:29")["half_back"] == 105.0
    assert _row_at(enriched, "2026-08-31 18:30")["pdh"] == 115.0
    assert _row_at(enriched, "2026-08-31 18:30")["half_back"] == 105.0
    assert _row_at(enriched, "2026-09-01 09:25")["pdc"] == 106.0


# --------------------------------------------------------------------------
# Futures-week end enforcement (Friday 17:00 ET)
# --------------------------------------------------------------------------


def test_week_high_low_ignore_bars_after_friday_close():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Futures week anchored Sunday 2026-08-23 18:00 ET.
                ("2026-08-24 09:30", 200.0, 300.0, 100.0, 250.0),
                # Friday 16:59 ET is still inside the week (ends 17:00).
                ("2026-08-28 16:59", 300.0, 400.0, 90.0, 390.0),
                # Bar opening exactly at the Friday 17:00 ET close belongs to
                # no futures week.
                ("2026-08-28 17:00", 400.0, 999.0, 1.0, 500.0),
                # Weekend gap bars must never contaminate week extremes.
                ("2026-08-29 12:00", 100.0, 888.0, 2.0, 120.0),
                # Next futures week starts Sunday 2026-08-30 18:00 ET.
                ("2026-08-30 18:00", 95.0, 120.0, 110.0, 115.0),
                ("2026-08-31 09:30", 115.0, 130.0, 105.0, 125.0),
            ]
        ),
        _config(),
        causal=True,
    )

    friday_1659 = _row_at(enriched, "2026-08-28 16:59")
    friday_1700 = _row_at(enriched, "2026-08-28 17:00")
    saturday = _row_at(enriched, "2026-08-29 12:00")
    next_week_start = _row_at(enriched, "2026-08-30 18:00")
    monday = _row_at(enriched, "2026-08-31 09:30")

    # The Friday 16:59 bar legitimately updates its futures week.
    assert friday_1659["week_high"] == 400.0
    assert friday_1659["week_low"] == 90.0

    # From the Friday 17:00 close until the next Sunday 18:00 open no futures
    # week is open: the extremes are NaN and later weeks never see these bars.
    assert pd.isna(friday_1700["week_high"])
    assert pd.isna(friday_1700["week_low"])
    assert pd.isna(saturday["week_high"])
    assert pd.isna(saturday["week_low"])

    assert next_week_start["week_high"] == 120.0
    assert next_week_start["week_low"] == 110.0
    assert monday["week_high"] == 130.0
    assert monday["week_low"] == 105.0


# --------------------------------------------------------------------------
# Multi-day session chain and previous-day level chaining
# --------------------------------------------------------------------------


def test_session_dates_chain_across_multiple_globex_days():
    enriched, _ = enrich_with_sessions(
        _make_bars(
            [
                # Tuesday 2026-08-25.
                ("2026-08-25 09:30", 100.0, 110.0, 90.0, 105.0),
                # Roll at 18:00 ET -> session Wed 2026-08-26.
                ("2026-08-25 18:00", 106.0, 112.0, 104.0, 108.0),
                ("2026-08-26 00:30", 108.0, 109.0, 107.0, 108.5),
                ("2026-08-26 09:30", 108.5, 200.0, 95.0, 190.0),
                # Roll at 18:00 ET -> session Thu 2026-08-27.
                ("2026-08-26 18:00", 191.0, 195.0, 188.0, 193.0),
                ("2026-08-27 02:00", 193.0, 210.0, 150.0, 205.0),
                ("2026-08-27 09:30", 205.0, 300.0, 100.0, 290.0),
            ]
        ),
        _config(),
        causal=True,
    )

    assert _row_at(enriched, "2026-08-25 09:30")["session_date"] == date(2026, 8, 25)
    assert _row_at(enriched, "2026-08-25 18:00")["session_date"] == date(2026, 8, 26)
    assert _row_at(enriched, "2026-08-26 00:30")["session_date"] == date(2026, 8, 26)
    assert _row_at(enriched, "2026-08-26 09:30")["session_date"] == date(2026, 8, 26)
    assert _row_at(enriched, "2026-08-26 18:00")["session_date"] == date(2026, 8, 27)
    assert _row_at(enriched, "2026-08-27 02:00")["session_date"] == date(2026, 8, 27)
    assert _row_at(enriched, "2026-08-27 09:30")["session_date"] == date(2026, 8, 27)

    # After-midnight bars keep the same session date (no double roll) and the
    # Asia window is not active at 00:30 ET.
    assert bool(_row_at(enriched, "2026-08-26 00:30")["is_asia"]) is False
    assert bool(_row_at(enriched, "2026-08-27 02:00")["is_london"]) is True

    # PD levels chain across consecutive trading sessions: PDH on the Aug 26
    # session is the Aug 25 RTH high (110) and on the Aug 27 session (even
    # from its first bar at Aug 26 18:00 ET) is the Aug 26 RTH high (200).
    # No intra-week day is skipped.
    assert _row_at(enriched, "2026-08-26 09:30")["pdh"] == 110.0
    assert _row_at(enriched, "2026-08-26 18:00")["pdh"] == 200.0
    assert _row_at(enriched, "2026-08-27 09:30")["pdh"] == 200.0
    assert _row_at(enriched, "2026-08-27 02:00")["pdh"] == 200.0


# --------------------------------------------------------------------------
# Fixed-ET session windows through DST transitions
# --------------------------------------------------------------------------


def _utc_bars(records: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    timestamps = [pd.Timestamp(timestamp_utc) for timestamp_utc, *_ in records]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [record[1] for record in records],
            "high": [record[2] for record in records],
            "low": [record[3] for record in records],
            "close": [record[4] for record in records],
            "volume": [100 for _ in records],
        }
    )


def test_fixed_et_session_windows_survive_spring_forward():
    # US DST begins 2026-03-08 02:00 ET. Sessions are defined by fixed ET
    # clock time, so the UTC instants inside each window shift by an hour.
    enriched, _ = enrich_with_sessions(
        _utc_bars(
            [
                # 06:30Z on Mar 6 = 01:30 EST: before London [02:00,05:00).
                ("2026-03-06T06:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 06:30Z on Mar 9 = 02:30 EDT: inside London after the shift.
                ("2026-03-09T06:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 13:30Z on Mar 9 = 09:30 EDT: RTH open.
                ("2026-03-09T13:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 00:30Z on Mar 10 = 20:30 EDT Mar 9: Asia after the 18:00
                # roll and inside the fixed-ET [20:00,00:00) window.
                ("2026-03-10T00:30:00Z", 100.0, 101.0, 99.0, 100.0),
            ]
        ),
        _config(),
        causal=True,
    )

    before = enriched.iloc[0]
    after = enriched.iloc[1]
    rth = enriched.iloc[2]
    evening = enriched.iloc[3]

    assert bool(before["is_london"]) is False
    assert bool(after["is_london"]) is True
    assert bool(rth["is_rth"]) is True
    assert rth["session_date"] == date(2026, 3, 9)
    assert bool(evening["is_asia"]) is True
    assert evening["session_date"] == date(2026, 3, 10)


def test_session_dates_chain_across_spring_forward_weekend():
    # Saturday 2026-03-07 18:00 EST -> Sunday session; Sunday 2026-03-08
    # 18:00 EDT -> Monday session. The two rolls are 23 hours apart in UTC,
    # which must not skip or duplicate a session date.
    enriched, _ = enrich_with_sessions(
        _utc_bars(
            [
                ("2026-03-06T14:30:00Z", 100.0, 101.0, 99.0, 100.0),  # Fri 09:30 EST
                ("2026-03-07T23:00:00Z", 100.0, 101.0, 99.0, 100.0),  # Sat 18:00 EST
                ("2026-03-08T13:30:00Z", 100.0, 101.0, 99.0, 100.0),  # Sun 09:30 EDT
                ("2026-03-08T22:00:00Z", 100.0, 101.0, 99.0, 100.0),  # Sun 18:00 EDT
                ("2026-03-09T13:30:00Z", 100.0, 101.0, 99.0, 100.0),  # Mon 09:30 EDT
            ]
        ),
        _config(),
        causal=True,
    )

    expected_dates = [
        date(2026, 3, 6),
        date(2026, 3, 8),
        date(2026, 3, 8),
        date(2026, 3, 9),
        date(2026, 3, 9),
    ]
    assert enriched["session_date"].tolist() == expected_dates


def test_fixed_et_session_windows_survive_fall_back():
    # US DST ends 2026-11-01 02:00 ET. After the change the clocks run UTC-5:
    # the RTH open (09:30 ET) is 14:30Z and the Asia window opens at 01:30Z.
    enriched, _ = enrich_with_sessions(
        _utc_bars(
            [
                # 00:30Z on Oct 31 = 20:30 EDT Oct 30: Asia, session Oct 31.
                ("2026-10-31T00:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 22:30Z on Nov 2 = 17:30 EST: before the 18:00 roll and
                # before Asia [20:00,00:00): session Nov 2, not Asia.
                ("2026-11-02T22:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 01:30Z on Nov 3 = 20:30 EST Nov 2: Asia, session Nov 3.
                ("2026-11-03T01:30:00Z", 100.0, 101.0, 99.0, 100.0),
                # 14:30Z on Nov 3 = 09:30 EST: RTH open at UTC-5.
                ("2026-11-03T14:30:00Z", 100.0, 101.0, 99.0, 100.0),
            ]
        ),
        _config(),
        causal=True,
    )

    before = enriched.iloc[0]
    asia_not_yet = enriched.iloc[1]
    asia = enriched.iloc[2]
    rth = enriched.iloc[3]

    assert bool(before["is_asia"]) is True
    assert before["session_date"] == date(2026, 10, 31)
    assert bool(asia_not_yet["is_asia"]) is False
    assert asia_not_yet["session_date"] == date(2026, 11, 2)
    assert bool(asia["is_asia"]) is True
    assert asia["session_date"] == date(2026, 11, 3)
    assert bool(rth["is_rth"]) is True
    assert rth["session_date"] == date(2026, 11, 3)


# ---------------------------------------------------------------------------
# Production as_of-boundary visibility (final-gate regressions)
#
# In production the pipeline first cuts the 1m frame to the completed prefix
# at ``as_of``, so the last row of the enriched prefix opens at as_of - 1m.
# Finalized levels must be visible on that edge row at their approved as_of
# instants (05:00 London H/L, 09:30 overnight/premarket H/L, 09:31 cash open)
# -- never one minute late, and never before the window's bar has completed.
# ---------------------------------------------------------------------------


def _session_records() -> list[tuple[str, float, float, float, float]]:
    return [
        ("2026-08-31 18:00", 100.0, 105.0, 95.0, 100.0),   # overnight open
        ("2026-09-01 02:00", 101.0, 106.0, 99.0, 103.0),   # london
        ("2026-09-01 04:59", 103.0, 104.0, 100.0, 105.0),  # last london minute
        ("2026-09-01 09:29", 200.0, 220.0, 90.0, 215.0),   # last pm/on minute
        ("2026-09-01 09:30", 215.0, 216.0, 214.0, 215.5),  # cash open
    ]


def _enrich_prefix_as_of(records, as_of_et: str):
    from data_clock import filter_as_of

    full = _make_bars(records)
    prefix = filter_as_of(
        full, as_of=pd.Timestamp(as_of_et, tz=TRADING_TZ)
    )
    enriched, _ = enrich_with_sessions(prefix, _config(), causal=True)
    return enriched


def test_london_final_levels_visible_at_0500_as_of() -> None:
    # At as_of=05:00 ET the completed prefix ends with the bar opening 04:59
    # (which completes at exactly 05:00): the finalized London H/L must be
    # present on that edge row, not one minute later.
    enriched = _enrich_prefix_as_of(_session_records(), "2026-09-01T05:00:00-04:00")
    assert enriched["timestamp_et"].iloc[-1] == pd.Timestamp(
        "2026-09-01 04:59", tz=TRADING_TZ
    )
    last = enriched.iloc[-1]
    assert last["loh"] == 106.0
    assert last["lol"] == 99.0
    # Overnight/premarket are NOT final until 09:30 ET.
    assert pd.isna(last["onh"])
    assert pd.isna(last["pmh"])

    # One minute earlier (04:59 as_of) no London bar has completed yet.
    early = _enrich_prefix_as_of(_session_records(), "2026-09-01T04:59:00-04:00")
    assert pd.isna(early.iloc[-1]["loh"])
    assert pd.isna(early.iloc[-1]["lol"])


def test_overnight_and_premarket_final_levels_visible_at_0930_as_of() -> None:
    # At as_of=09:30 ET the completed prefix ends with the bar opening 09:29
    # (which completes at exactly 09:30): ONH/ONL and PMH/PML must be present
    # on that edge row.
    enriched = _enrich_prefix_as_of(_session_records(), "2026-09-01T09:30:00-04:00")
    assert enriched["timestamp_et"].iloc[-1] == pd.Timestamp(
        "2026-09-01 09:29", tz=TRADING_TZ
    )
    last = enriched.iloc[-1]
    assert last["onh"] == 220.0
    assert last["onl"] == 90.0
    assert last["pmh"] == 220.0
    assert last["pml"] == 90.0
    # The cash open (09:30 bar) is not complete until 09:31 ET.
    assert pd.isna(last["rth_open"])

    # One minute earlier (09:29 as_of) PM/ON are still developing.
    early = _enrich_prefix_as_of(_session_records(), "2026-09-01T09:29:00-04:00")
    assert pd.isna(early.iloc[-1]["onh"])
    assert pd.isna(early.iloc[-1]["pmh"])


def test_cash_open_visible_at_0931_as_of() -> None:
    # At as_of=09:31 ET the completed prefix includes the 09:30 bar (which
    # completes at exactly 09:31): the cash open must be present on it.
    enriched = _enrich_prefix_as_of(_session_records(), "2026-09-01T09:31:00-04:00")
    assert enriched["timestamp_et"].iloc[-1] == pd.Timestamp(
        "2026-09-01 09:30", tz=TRADING_TZ
    )
    assert enriched.iloc[-1]["rth_open"] == 215.0

    # One minute earlier (09:30 as_of) the cash-open bar is not yet complete.
    early = _enrich_prefix_as_of(_session_records(), "2026-09-01T09:30:00-04:00")
    assert pd.isna(early.iloc[-1]["rth_open"])
