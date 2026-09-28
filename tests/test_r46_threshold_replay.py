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
