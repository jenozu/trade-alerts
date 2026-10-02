"""Targeted tests for R7.0 continuation-proxy + displacement gating."""

import pandas as pd
import pytest

from scripts.run_r7_continuation_displacement import (
    MODEL,
    apply_continuation_displacement_gate,
    summarize_r7,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "long_candidate": [True, True, True, False],
            "short_candidate": [False, False, False, True],
            "long_score_band": [
                "near_trigger",
                "near_trigger",
                "near_trigger",
                "near_trigger",
            ],
            "short_score_band": [
                "no_trade",
                "no_trade",
                "no_trade",
                "near_trigger",
            ],
            # Long row 0 is reversal-proxy and must survive without displacement.
            # Long row 1 is continuation-proxy with displacement and survives.
            # Long row 2 is continuation-proxy without displacement and is excluded.
            "recent_sell_side_sweep": [True, False, False, False],
            "recent_buy_side_sweep": [False, False, False, False],
            "recent_bullish_displacement": [False, True, False, False],
            "recent_bearish_displacement": [False, False, False, True],
            "long_raw_score": [75.0, 75.0, 75.0, 75.0],
            "short_raw_score": [10.0, 10.0, 10.0, 75.0],
        }
    )


def test_gate_preserves_reversals_and_requires_displacement_only_for_continuations():
    frame = sample_frame()
    original = frame.copy(deep=True)

    gated, diagnostics = apply_continuation_displacement_gate(frame)

    assert gated["long_candidate"].tolist() == [True, True, False, False]
    assert gated["short_candidate"].tolist() == [False, False, False, True]

    long_diag = diagnostics.set_index("direction").loc["long"]
    assert long_diag["baseline_eligible_rows"] == 3
    assert long_diag["reversal_proxy_rows"] == 1
    assert long_diag["continuation_proxy_rows"] == 2
    assert long_diag["continuation_with_displacement_rows"] == 1
    assert long_diag["continuation_without_displacement_rows"] == 1
    assert long_diag["excluded_rows"] == 1

    # Research gating must not rewrite source scores or mutate the input frame.
    pd.testing.assert_frame_equal(frame, original)
    assert gated["long_raw_score"].tolist() == original["long_raw_score"].tolist()
    assert gated["short_raw_score"].tolist() == original["short_raw_score"].tolist()


def test_gate_uses_direction_specific_sweep_and_displacement_fields():
    frame = pd.DataFrame(
        {
            "long_candidate": [True, True],
            "short_candidate": [True, True],
            "recent_sell_side_sweep": [False, True],
            "recent_buy_side_sweep": [True, False],
            "recent_bullish_displacement": [True, False],
            "recent_bearish_displacement": [False, True],
        }
    )

    gated, _ = apply_continuation_displacement_gate(frame)

    assert gated["long_candidate"].tolist() == [True, True]
    assert gated["short_candidate"].tolist() == [True, True]


def test_gate_refuses_missing_historical_fields_instead_of_inventing_proxy():
    frame = sample_frame().drop(columns=["recent_bullish_displacement"])

    with pytest.raises(ValueError, match="recent_bullish_displacement"):
        apply_continuation_displacement_gate(frame)


def test_gate_preserves_existing_baseline_ineligibility():
    frame = sample_frame()
    frame.loc[3, "short_candidate"] = False

    gated, diagnostics = apply_continuation_displacement_gate(frame)

    assert not gated.loc[3, "short_candidate"]
    short_diag = diagnostics.set_index("direction").loc["short"]
    assert short_diag["baseline_eligible_rows"] == 0
    assert short_diag["candidate_rows_after_gate"] == 0


def test_summary_exposes_required_r7_metrics():
    trades = pd.DataFrame(
        {
            "net_result_points": [10.0, -5.0],
            "net_result_r": [0.5, -0.25],
            "mfe_points": [20.0, 5.0],
            "mae_points": [4.0, 8.0],
            "tp1_hit": [True, False],
            "tp2_hit": [False, False],
            "tp3_hit": [False, False],
            "tp4_hit": [False, False],
            "stop_hit": [False, True],
            "minutes_held": [10.0, 15.0],
            "raw_score": [75.0, 75.0],
        }
    )

    summary = summarize_r7(2023, MODEL, trades)

    assert summary["trades"] == 2
    assert summary["net_points"] == pytest.approx(5.0)
    assert summary["expectancy_points"] == pytest.approx(2.5)
    assert summary["tp1_hit_rate"] == pytest.approx(0.5)
    assert summary["stop_hit_rate"] == pytest.approx(0.5)
    assert summary["max_drawdown_points"] == pytest.approx(5.0)
