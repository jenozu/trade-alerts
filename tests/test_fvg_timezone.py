from __future__ import annotations

import warnings

import pandas as pd

from fvg import FVGSettings, track_fvg_lifecycle


def _settings() -> FVGSettings:
    return FVGSettings(
        tick_size=0.25,
        minimum_gap_ticks=1,
        minimum_gap_atr_fraction=0.0,
        require_displacement_candle=False,
        track_first_touch=True,
        track_fill_percentage=True,
        full_fill_percentage=1.0,
        invalidate_on_full_fill=False,
        retest_enabled=True,
        require_close_hold=True,
        maximum_bars_after_creation=20,
        inverse_fvg_enabled=True,
        require_close_through_original_fvg=True,
    )


def test_fvg_lifecycle_timestamp_columns_preserve_utc_dtype():
    timestamps = pd.date_range(
        "2026-08-31 13:30:00",
        periods=3,
        freq="1min",
        tz="UTC",
    )

    bars = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.5, 100.0],
            "close": [100.5, 101.5, 100.25],
        }
    )

    fvg_table = pd.DataFrame(
        {
            "fvg_id": [1],
            "direction": ["bullish"],
            "creation_index": [0],
            "creation_time": [timestamps[0]],
            "lower_bound": [100.0],
            "upper_bound": [101.0],
            "midpoint": [100.5],
            "size_points": [1.0],
            "session_date": [timestamps[0].date()],
        }
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        tracked = track_fvg_lifecycle(
            bars,
            fvg_table,
            settings=_settings(),
        )

    lifecycle_columns = [
        "first_touch_time",
        "full_fill_time",
        "retest_hold_time",
        "invalidation_time",
        "inverse_fvg_time",
    ]

    for column in lifecycle_columns:
        assert str(tracked[column].dtype) == "datetime64[ns, UTC]"

    dtype_warnings = [
        warning
        for warning in caught
        if issubclass(warning.category, FutureWarning)
        and "incompatible dtype" in str(warning.message)
    ]
    assert dtype_warnings == []
