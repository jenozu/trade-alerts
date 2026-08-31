from __future__ import annotations

from datetime import date

import pandas as pd

from sessions import enrich_with_sessions, load_sessions_config


TRADING_TZ = "America/New_York"


def _config() -> dict:
    return load_sessions_config("config/sessions.yaml")


def _make_bars(records: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    """Build synthetic 1-minute-style bars from New York timestamps."""
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


def _two_session_fixture() -> pd.DataFrame:
    """
    Synthetic data spanning a completed prior RTH session and the next
    Globex session. Future morning values are intentionally much more extreme
    than the first evening bar so lookahead is easy to detect.
    """
    return _make_bars(
        [
            # Prior session RTH: PDH=115, PDL=95 for the Sep 1 session.
            ("2026-08-31 09:30", 100.0, 101.0, 99.0, 100.0),
            ("2026-08-31 15:59", 105.0, 115.0, 95.0, 106.0),
            # Just before and at the Globex session-date rollover.
            ("2026-08-31 17:59", 107.0, 108.0, 106.0, 107.0),
            ("2026-08-31 18:00", 200.0, 201.0, 199.0, 200.0),
            # Same Sep 1 futures session, later windows.
            ("2026-09-01 02:00", 202.0, 205.0, 198.0, 203.0),
            ("2026-09-01 04:00", 204.0, 207.0, 197.0, 205.0),
            ("2026-09-01 04:59", 206.0, 209.0, 196.0, 207.0),
            ("2026-09-01 05:00", 207.0, 208.0, 197.0, 207.5),
            ("2026-09-01 09:29", 210.0, 220.0, 190.0, 215.0),
            # RTH / opening ranges.
            ("2026-09-01 09:30", 215.0, 216.0, 214.0, 215.5),
            ("2026-09-01 09:34", 218.0, 225.0, 213.0, 220.0),
            ("2026-09-01 09:35", 220.0, 221.0, 215.0, 219.0),
            ("2026-09-01 09:44", 222.0, 230.0, 210.0, 225.0),
            ("2026-09-01 09:45", 225.0, 228.0, 211.0, 226.0),
            ("2026-09-01 09:59", 227.0, 235.0, 205.0, 230.0),
            ("2026-09-01 10:00", 230.0, 233.0, 206.0, 231.0),
            ("2026-09-01 10:29", 231.0, 234.0, 229.0, 232.0),
            ("2026-09-01 10:30", 232.0, 235.0, 230.0, 233.0),
        ]
    )


def test_session_date_rolls_at_1800_et():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    before_roll = _row_at(enriched, "2026-08-31 17:59")
    after_roll = _row_at(enriched, "2026-08-31 18:00")

    assert before_roll["session_date"] == date(2026, 8, 31)
    assert after_roll["session_date"] == date(2026, 9, 1)


def test_developing_overnight_level_uses_only_information_seen_so_far():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    evening = _row_at(enriched, "2026-08-31 18:00")

    # The future overnight high eventually reaches 220, but at 18:00 only
    # the current 201 high is known.
    assert evening["developing_onh"] == 201.0
    assert evening["developing_onl"] == 199.0


def test_finalized_premarket_and_overnight_levels_wait_until_0930():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    before = _row_at(enriched, "2026-09-01 09:29")
    available = _row_at(enriched, "2026-09-01 09:30")

    for column in ["pmh", "pml", "onh", "onl"]:
        assert pd.isna(before[column]), f"{column} leaked before 09:30 ET"

    assert available["pmh"] == 220.0
    assert available["pml"] == 190.0
    assert available["onh"] == 220.0
    assert available["onl"] == 190.0


def test_london_final_levels_wait_until_0500():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    before = _row_at(enriched, "2026-09-01 04:59")
    available = _row_at(enriched, "2026-09-01 05:00")

    assert pd.isna(before["loh"])
    assert pd.isna(before["lol"])
    assert available["loh"] == 209.0
    assert available["lol"] == 196.0


def test_previous_rth_high_low_are_available_during_next_evening_session():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    evening = _row_at(enriched, "2026-08-31 18:00")

    # PDH/PDL refer to the already-completed Aug 31 RTH session, so unlike
    # same-session PM/ON/London levels they are legitimately known at 18:00.
    assert evening["pdh"] == 115.0
    assert evening["pdl"] == 95.0


def test_finalized_same_session_levels_do_not_leak_into_prior_evening():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    evening = _row_at(enriched, "2026-08-31 18:00")

    # These Sep 1 levels are not finalized until hours after this 18:00 bar.
    # A causal replay must never expose their future final values here.
    for column in ["pmh", "pml", "onh", "onl", "loh", "lol"]:
        assert pd.isna(evening[column]), (
            f"{column} leaked into the prior evening; value={evening[column]}"
        )


def test_rth_open_does_not_leak_into_prior_evening():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    evening = _row_at(enriched, "2026-08-31 18:00")
    rth_open_bar = _row_at(enriched, "2026-09-01 09:30")

    assert pd.isna(evening["rth_open"]), "Future RTH open leaked into prior evening"
    assert rth_open_bar["rth_open"] == 215.0


def test_opening_ranges_are_hidden_until_completion_and_never_leak_to_evening():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    evening = _row_at(enriched, "2026-08-31 18:00")
    at_0934 = _row_at(enriched, "2026-09-01 09:34")
    at_0935 = _row_at(enriched, "2026-09-01 09:35")
    at_0944 = _row_at(enriched, "2026-09-01 09:44")
    at_0945 = _row_at(enriched, "2026-09-01 09:45")
    at_0959 = _row_at(enriched, "2026-09-01 09:59")
    at_1000 = _row_at(enriched, "2026-09-01 10:00")

    for column in [
        "or5_high",
        "or5_low",
        "or15_high",
        "or15_low",
        "or30_high",
        "or30_low",
    ]:
        assert pd.isna(evening[column]), f"{column} leaked into prior evening"

    assert pd.isna(at_0934["or5_high"])
    assert pd.isna(at_0934["or5_low"])
    assert at_0935["or5_high"] == 225.0
    assert at_0935["or5_low"] == 213.0

    assert pd.isna(at_0944["or15_high"])
    assert pd.isna(at_0944["or15_low"])
    assert at_0945["or15_high"] == 230.0
    assert at_0945["or15_low"] == 210.0

    assert pd.isna(at_0959["or30_high"])
    assert pd.isna(at_0959["or30_low"])
    assert at_1000["or30_high"] == 235.0
    assert at_1000["or30_low"] == 205.0


def test_strategy_window_allows_new_entries_only_from_0930_until_before_1030():
    enriched, _ = enrich_with_sessions(_two_session_fixture(), _config(), causal=True)

    assert bool(_row_at(enriched, "2026-09-01 09:30")["new_entry_allowed"])
    assert bool(_row_at(enriched, "2026-09-01 10:29")["new_entry_allowed"])
    assert not bool(_row_at(enriched, "2026-09-01 10:30")["new_entry_allowed"])
