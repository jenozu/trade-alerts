"""R4.6 replay must change eligibility, not filter an executed-trade ledger."""
import pandas as pd
import pytest

from scripts.run_r46_threshold_replay import apply_threshold, assert_frozen_70


def test_threshold_requires_existing_setup_eligibility_and_directional_score():
    frame = pd.DataFrame({
        "long_candidate": [True, True, False, True],
        "short_candidate": [False, True, True, True],
        "long_raw_score": [72., 85., 95., 79.],
        "short_raw_score": [95., 74., 81., 80.],
    })
    result = apply_threshold(frame, 80)
    assert result.long_candidate.tolist() == [False, True, False, False]
    assert result.short_candidate.tolist() == [False, False, True, True]
    pd.testing.assert_frame_equal(frame, pd.DataFrame({
        "long_candidate": [True, True, False, True],
        "short_candidate": [False, True, True, True],
        "long_raw_score": [72., 85., 95., 79.],
        "short_raw_score": [95., 74., 81., 80.],
    }))


def test_frozen_parity_gate_rejects_changes_in_execution():
    frozen = pd.DataFrame({"entry_price": [100.], "net_result_points": [25.]})
    assert_frozen_70(frozen.copy(), frozen)
    with pytest.raises(AssertionError):
        assert_frozen_70(
            pd.DataFrame({"entry_price": [101.], "net_result_points": [25.]}),
            frozen,
        )


def test_rejects_out_of_range_threshold():
    with pytest.raises(ValueError):
        apply_threshold(
            pd.DataFrame({
                "long_candidate": [True], "short_candidate": [False],
                "long_raw_score": [80.], "short_raw_score": [20.],
            }), 110
        )


def test_frozen_parity_normalizes_archived_timestamps():
    from io import StringIO

    actual = pd.DataFrame({
        "trade_id": [1, 2],
        "signal_time": pd.to_datetime([
            "2024-01-02T14:30:00Z",
            "2024-01-02T14:40:00Z",
        ], utc=True),
        "entry_time": pd.to_datetime([
            "2024-01-02T14:31:00Z",
            "2024-01-02T14:41:00Z",
        ], utc=True),
        "exit_time": pd.to_datetime([
            "2024-01-02T14:35:00Z",
            "2024-01-02T14:45:00Z",
        ], utc=True),
        "net_result_points": [25.25, -25.25],
    })

    frozen = pd.read_csv(
        StringIO(actual.to_csv(index=False))
    )

    # Identical trades must pass despite CSV timestamp types.
    assert_frozen_70(actual, frozen)

    # A genuine timestamp difference must still fail.
    changed = actual.copy()
    changed.loc[0, "signal_time"] += pd.Timedelta(minutes=1)

    with pytest.raises(AssertionError):
        assert_frozen_70(changed, frozen)

    # A changed financial result must still fail.
    changed = actual.copy()
    changed.loc[1, "net_result_points"] = -30.25

    with pytest.raises(AssertionError):
        assert_frozen_70(changed, frozen)

    # Chronological trade order must remain identical.
    with pytest.raises(AssertionError):
        assert_frozen_70(
            actual.iloc[::-1].reset_index(drop=True),
            frozen,
        )


def test_frozen_parity_handles_session_dates():
    from io import StringIO

    actual = pd.DataFrame({
        "trade_id": [1, 2],
        "signal_time": pd.to_datetime([
            "2023-10-02T13:30:00Z",
            "2023-10-02T13:36:00Z",
        ], utc=True),
        "session_date": [
            pd.Timestamp("2023-10-02").date(),
            pd.Timestamp("2023-10-02").date(),
        ],
        "net_result_points": [25.25, -25.25],
        "stop_hit": [False, True],
        "rvol_time_of_day": [None, 3.7],
    })

    frozen = pd.read_csv(
        StringIO(actual.to_csv(index=False))
    )

    # Equivalent trades with different date representations pass.
    assert_frozen_70(actual, frozen)

    # Genuine date differences still fail.
    changed = actual.copy()
    changed.loc[0, "session_date"] = (
        pd.Timestamp("2023-10-03").date()
    )

    with pytest.raises(AssertionError):
        assert_frozen_70(changed, frozen)

    # Genuine financial differences still fail.
    changed = actual.copy()
    changed.loc[1, "net_result_points"] = -30.25

    with pytest.raises(AssertionError):
        assert_frozen_70(changed, frozen)

    # Changing the trade order must still fail.
    with pytest.raises(AssertionError):
        assert_frozen_70(
            actual.iloc[::-1].reset_index(drop=True),
            frozen,
        )
