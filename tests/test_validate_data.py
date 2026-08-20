from __future__ import annotations

import pandas as pd
import pytest

from validate_data import (
    DataValidationError,
    daily_coverage_summary,
    find_continuous_missing_timestamps,
    find_duplicate_timestamps,
    find_extreme_bar_ranges,
    find_invalid_ohlc_relationships,
    find_invalid_prices,
    find_large_price_jumps,
    find_missing_values,
    find_negative_volume,
    find_off_tick_prices,
    find_out_of_order_rows,
    find_timestamp_gaps,
    find_zero_volume,
    session_hour_summary,
    validate_market_data,
)


@pytest.fixture
def valid_dataframe() -> pd.DataFrame:
    timestamp = pd.date_range(
        start="2026-08-10 13:30:00",
        periods=6,
        freq="1min",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "timestamp_et": timestamp.tz_convert("America/New_York"),
            "open": [25000.00, 25001.00, 25002.00, 25003.00, 25004.00, 25005.00],
            "high": [25002.00, 25003.00, 25004.00, 25005.00, 25006.00, 25007.00],
            "low": [24999.00, 25000.00, 25001.00, 25002.00, 25003.00, 25004.00],
            "close": [25001.00, 25002.00, 25003.00, 25004.00, 25005.00, 25006.00],
            "volume": [1000, 1100, 1200, 1300, 1250, 1400],
            "source": ["LSE"] * 6,
            "symbol": ["NQ"] * 6,
            "contract": ["NQU26"] * 6,
        }
    )


def test_validation_rejects_missing_required_column(valid_dataframe):
    df = valid_dataframe.drop(columns=["close"])
    with pytest.raises(DataValidationError):
        validate_market_data(df)


def test_validation_rejects_naive_timestamp(valid_dataframe):
    df = valid_dataframe.copy()
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    with pytest.raises(DataValidationError):
        validate_market_data(df)


def test_valid_dataframe_passes(valid_dataframe):
    report = validate_market_data(valid_dataframe)
    assert report.passed is True
    assert report.duplicate_timestamps == 0
    assert report.invalid_prices == 0
    assert report.invalid_ohlc_relationships == 0
    assert report.negative_volume_rows == 0


def test_find_duplicate_timestamps(valid_dataframe):
    duplicate = valid_dataframe.iloc[[0]].copy()
    df = pd.concat([valid_dataframe, duplicate], ignore_index=True)
    result = find_duplicate_timestamps(df)
    assert len(result) == 2


def test_duplicates_fail_validation(valid_dataframe):
    duplicate = valid_dataframe.iloc[[0]].copy()
    df = pd.concat([valid_dataframe, duplicate], ignore_index=True)
    report = validate_market_data(df)
    assert report.passed is False
    assert report.duplicate_timestamps == 2


def test_find_out_of_order_rows(valid_dataframe):
    df = valid_dataframe.iloc[[0, 2, 1, 3, 4, 5]].reset_index(drop=True)
    result = find_out_of_order_rows(df)
    assert len(result) == 1


def test_find_missing_values(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[2, "close"] = float("nan")
    result = find_missing_values(df)
    assert len(result) == 1


def test_missing_value_fails_validation(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[2, "volume"] = float("nan")
    report = validate_market_data(df)
    assert report.passed is False
    assert report.missing_values == 1


def test_find_negative_price(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "open"] = -10
    result = find_invalid_prices(df)
    assert len(result) == 1


def test_find_zero_price(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "close"] = 0
    result = find_invalid_prices(df)
    assert len(result) == 1


def test_high_below_close_is_invalid(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[1, "high"] = 25001.00
    df.loc[1, "close"] = 25002.00
    result = find_invalid_ohlc_relationships(df)
    assert len(result) == 1


def test_low_above_open_is_invalid(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[1, "low"] = 25002.00
    df.loc[1, "open"] = 25001.00
    result = find_invalid_ohlc_relationships(df)
    assert len(result) == 1


def test_find_negative_volume(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[2, "volume"] = -1
    result = find_negative_volume(df)
    assert len(result) == 1


def test_negative_volume_fails_validation(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[2, "volume"] = -100
    report = validate_market_data(df)
    assert report.passed is False
    assert report.negative_volume_rows == 1


def test_zero_volume_is_warning_not_failure(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[2, "volume"] = 0
    result = find_zero_volume(df)
    assert len(result) == 1

    report = validate_market_data(df)
    assert report.passed is True
    assert report.zero_volume_rows == 1


def test_valid_nq_tick_prices_pass(valid_dataframe):
    result = find_off_tick_prices(valid_dataframe, tick_size=0.25)
    assert result.empty


def test_off_tick_price_is_detected(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[1, "open"] = 25001.13
    result = find_off_tick_prices(df, tick_size=0.25)
    assert len(result) == 1


def test_off_tick_is_warning_not_failure(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "open"] = 25000.13
    report = validate_market_data(df, tick_size=0.25)
    assert report.passed is True
    assert report.off_tick_price_rows == 1


def test_no_timestamp_gaps_in_continuous_data(valid_dataframe):
    result = find_timestamp_gaps(valid_dataframe, expected_interval_minutes=1)
    assert result.empty


def test_timestamp_gap_is_detected(valid_dataframe):
    df = valid_dataframe.drop(index=[2]).reset_index(drop=True)
    result = find_timestamp_gaps(df, expected_interval_minutes=1)
    assert len(result) == 1
    assert result["gap_minutes"].iloc[0] == 2


def test_continuous_missing_timestamp_detected(valid_dataframe):
    df = valid_dataframe.drop(index=[2]).reset_index(drop=True)
    missing = find_continuous_missing_timestamps(df)
    assert len(missing) == 1

    expected_missing = pd.Timestamp("2026-08-10 13:32:00", tz="UTC")
    assert missing[0] == expected_missing


def test_large_price_jump_is_detected(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[3, "open"] = 25200.00
    df.loc[3, "high"] = 25202.00
    df.loc[3, "low"] = 25199.00
    df.loc[3, "close"] = 25201.00

    result = find_large_price_jumps(df, threshold_points=100)
    assert len(result) == 1
    assert result["open_gap_points"].iloc[0] > 100


def test_extreme_bar_range_is_detected():
    timestamp = pd.date_range(
        start="2026-08-10 13:30:00",
        periods=30,
        freq="1min",
        tz="UTC",
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamp,
            "timestamp_et": timestamp.tz_convert("America/New_York"),
            "open": [25000.0] * 30,
            "high": [25002.0] * 30,
            "low": [25000.0] * 30,
            "close": [25001.0] * 30,
            "volume": [1000] * 30,
            "source": ["LSE"] * 30,
            "symbol": ["NQ"] * 30,
            "contract": ["NQU26"] * 30,
        }
    )

    df.loc[25, "high"] = 25030.0

    result = find_extreme_bar_ranges(
        df,
        rolling_window=20,
        multiplier=10.0,
    )

    assert 25 in result.index


def test_session_hour_summary(valid_dataframe):
    result = session_hour_summary(valid_dataframe)
    assert len(result) == 1
    assert result["et_hour"].iloc[0] == 9
    assert result["bars"].iloc[0] == 6


def test_daily_coverage_summary(valid_dataframe):
    result = daily_coverage_summary(valid_dataframe)
    assert len(result) == 1
    assert result["bars"].iloc[0] == 6
    assert result["day_high"].iloc[0] == 25007.0
    assert result["day_low"].iloc[0] == 24999.0
    assert result["total_volume"].iloc[0] == 7250


def test_report_contains_error_for_duplicates(valid_dataframe):
    duplicate = valid_dataframe.iloc[[0]].copy()
    df = pd.concat([valid_dataframe, duplicate], ignore_index=True)
    report = validate_market_data(df)

    error_categories = {
        issue.category
        for issue in report.issues
        if issue.severity == "ERROR"
    }

    assert "duplicate_timestamps" in error_categories


def test_report_contains_warning_for_zero_volume(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "volume"] = 0
    report = validate_market_data(df)

    warning_categories = {
        issue.category
        for issue in report.issues
        if issue.severity == "WARNING"
    }

    assert "zero_volume" in warning_categories


def test_warnings_do_not_fail_dataset(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "volume"] = 0
    report = validate_market_data(df)
    assert report.passed is True


def test_multiple_errors_are_all_reported(valid_dataframe):
    df = valid_dataframe.copy()
    df.loc[0, "volume"] = -100
    df.loc[1, "open"] = 0
    df.loc[2, "high"] = 24000

    report = validate_market_data(df)

    assert report.passed is False
    assert report.negative_volume_rows == 1
    assert report.invalid_prices >= 1
    assert report.invalid_ohlc_relationships >= 1
