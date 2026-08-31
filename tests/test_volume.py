from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volume import VolumeError, enrich_volume_features


def _config() -> dict:
    return {
        "relative_volume": {
            "initial_signal_threshold": 1.50,
            "zscore_threshold": 2.0,
            "rolling": {
                "lookback_bars": 2,
                "minimum_periods": 2,
                "baseline_uses_previous_bars_only": True,
            },
            "time_of_day": {
                "lookback_sessions": 2,
                "minimum_sessions": 2,
                "baseline_uses_previous_sessions_only": True,
            },
        }
    }


def _bars(
    timestamps: list[pd.Timestamp] | pd.DatetimeIndex,
    volumes: list[float],
    *,
    opens: list[float] | None = None,
    closes: list[float] | None = None,
    session_dates: list[object] | None = None,
) -> pd.DataFrame:
    timestamps = pd.DatetimeIndex(timestamps)
    n = len(timestamps)
    opens = opens or [100.0] * n
    closes = closes or [100.25] * n

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": [max(o, c) + 0.25 for o, c in zip(opens, closes)],
            "low": [min(o, c) - 0.25 for o, c in zip(opens, closes)],
            "close": closes,
            "volume": volumes,
        }
    )
    df["timestamp_et"] = df["timestamp"].dt.tz_convert("America/New_York")
    if session_dates is not None:
        df["session_date"] = session_dates
    return df


def _same_et_minute_sessions(volumes: list[float]) -> pd.DataFrame:
    # 13:30 UTC is 09:30 ET during EDT in August 2026.
    timestamps = pd.to_datetime(
        [
            "2026-08-27 13:30:00+00:00",
            "2026-08-28 13:30:00+00:00",
            "2026-08-31 13:30:00+00:00",
            "2026-09-01 13:30:00+00:00",
        ][: len(volumes)],
        utc=True,
    )
    sessions = [ts.tz_convert("America/New_York").date() for ts in timestamps]
    return _bars(timestamps, volumes, session_dates=sessions)


def test_volume_rejects_naive_timestamps():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-31 09:30", periods=3, freq="1min"),
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.5, 100.5, 100.5],
            "volume": [10.0, 20.0, 30.0],
        }
    )

    with pytest.raises(VolumeError, match="timezone-aware"):
        enrich_volume_features(df, _config())


def test_rolling_rvol_baseline_uses_previous_bars_only():
    timestamps = pd.date_range("2026-08-31 13:30", periods=3, freq="1min", tz="UTC")
    enriched = enrich_volume_features(_bars(timestamps, [10.0, 20.0, 100.0]), _config())

    # At bar 3, the two-bar baseline must be mean(10, 20) = 15.
    # The current volume of 100 must not be included in its own baseline.
    row = enriched.iloc[2]
    assert row["volume_mean_rolling"] == pytest.approx(15.0)
    assert row["volume_median_rolling"] == pytest.approx(15.0)
    assert row["rvol_rolling"] == pytest.approx(100.0 / 15.0)


def test_rolling_rvol_waits_for_required_prior_history():
    timestamps = pd.date_range("2026-08-31 13:30", periods=3, freq="1min", tz="UTC")
    enriched = enrich_volume_features(_bars(timestamps, [10.0, 20.0, 30.0]), _config())

    assert pd.isna(enriched.loc[0, "rvol_rolling"])
    assert pd.isna(enriched.loc[1, "rvol_rolling"])
    assert enriched.loc[2, "rvol_rolling"] == pytest.approx(2.0)


def test_time_of_day_baseline_excludes_current_session():
    enriched = enrich_volume_features(
        _same_et_minute_sessions([100.0, 200.0, 1000.0]),
        _config(),
    )

    # Session 3 baseline must use only sessions 1 and 2: mean(100, 200) = 150.
    row = enriched.iloc[2]
    assert row["volume_tod_baseline"] == pytest.approx(150.0)
    assert row["rvol_time_of_day"] == pytest.approx(1000.0 / 150.0)


def test_time_of_day_rvol_waits_for_minimum_prior_sessions():
    enriched = enrich_volume_features(
        _same_et_minute_sessions([100.0, 200.0, 300.0]),
        _config(),
    )

    assert pd.isna(enriched.loc[0, "volume_tod_baseline"])
    assert pd.isna(enriched.loc[1, "volume_tod_baseline"])
    assert enriched.loc[2, "volume_tod_baseline"] == pytest.approx(150.0)


def test_future_session_volume_does_not_rewrite_past_time_of_day_features():
    first_three = _same_et_minute_sessions([100.0, 200.0, 300.0])
    four_sessions = _same_et_minute_sessions([100.0, 200.0, 300.0, 999999.0])

    early = enrich_volume_features(first_three, _config())
    extended = enrich_volume_features(four_sessions, _config()).iloc[:3].reset_index(drop=True)

    for column in ["volume_tod_baseline", "rvol_time_of_day"]:
        pd.testing.assert_series_equal(
            early[column].reset_index(drop=True),
            extended[column],
            check_names=False,
        )


def test_duplicate_same_minute_current_session_does_not_leak_into_its_baseline():
    timestamps = pd.to_datetime(
        [
            "2026-08-27 13:30:00+00:00",
            "2026-08-28 13:30:00+00:00",
            "2026-08-31 13:30:00+00:00",
            "2026-08-31 13:30:30+00:00",
        ],
        utc=True,
    )
    sessions = [
        pd.Timestamp("2026-08-27").date(),
        pd.Timestamp("2026-08-28").date(),
        pd.Timestamp("2026-08-31").date(),
        pd.Timestamp("2026-08-31").date(),
    ]
    df = _bars(
        timestamps,
        [100.0, 200.0, 1000.0, 500.0],
        session_dates=sessions,
    )
    enriched = enrich_volume_features(df, _config())

    # The current session's duplicate minute aggregates to 1500, but that entire
    # current-session amount must still be excluded from its own 09:30 baseline.
    current = enriched.loc[enriched["session_date"] == pd.Timestamp("2026-08-31").date()]
    assert len(current) == 2
    assert current["volume_tod_baseline"].tolist() == pytest.approx([150.0, 150.0])


def test_unsorted_input_is_sorted_before_causal_volume_features_are_calculated():
    timestamps = pd.to_datetime(
        [
            "2026-08-31 13:32:00+00:00",
            "2026-08-31 13:30:00+00:00",
            "2026-08-31 13:31:00+00:00",
        ],
        utc=True,
    )
    df = _bars(timestamps, [30.0, 10.0, 20.0])

    enriched = enrich_volume_features(df, _config())

    assert enriched["timestamp"].is_monotonic_increasing
    assert enriched["volume"].tolist() == [10.0, 20.0, 30.0]
    assert enriched.loc[2, "volume_mean_rolling"] == pytest.approx(15.0)
    assert enriched.loc[2, "rvol_rolling"] == pytest.approx(2.0)
