from __future__ import annotations

import pandas as pd
import pytest

from rollover import (
    ContractWindow,
    RolloverError,
    prepare_contract_frame,
    split_rollover_segments,
    stitch_contract_frames,
    validate_contract_windows,
)


def _frame(
    contract: str,
    *,
    start: str = "2026-06-12 00:00:00",
    periods: int = 6,
    base_price: float = 100.0,
) -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=periods, freq="1min", tz="UTC")
    close = [base_price + index for index in range(periods)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "volume": [100 + index for index in range(periods)],
            "source": ["PROJECTX"] * periods,
            "symbol": ["MNQ"] * periods,
            "contract": [contract] * periods,
        }
    )


def _windows() -> list[ContractWindow]:
    boundary = pd.Timestamp("2026-06-12 00:03:00", tz="UTC")
    return [
        ContractWindow("MNQM6", start=None, end=boundary),
        ContractWindow("MNQU6", start=boundary, end=None),
    ]


def test_rollover_rejects_naive_contract_timestamps():
    df = _frame("MNQM6")
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    with pytest.raises(RolloverError, match="timezone-aware"):
        prepare_contract_frame(df, expected_contract="MNQM6")


def test_rollover_boundary_is_old_end_exclusive_and_new_start_inclusive():
    old = _frame("MNQM6", base_price=100.0)
    new = _frame("MNQU6", base_price=200.0)

    result = stitch_contract_frames(
        {"MNQM6": old, "MNQU6": new},
        _windows(),
    )

    boundary = pd.Timestamp("2026-06-12 00:03:00", tz="UTC")
    at_boundary = result.loc[result["timestamp"] == boundary]

    assert len(at_boundary) == 1
    assert at_boundary.iloc[0]["contract"] == "MNQU6"
    assert result.loc[result["timestamp"] < boundary, "contract"].eq("MNQM6").all()
    assert result.loc[result["timestamp"] >= boundary, "contract"].eq("MNQU6").all()


def test_stitch_preserves_raw_contract_prices_without_back_adjustment():
    old = _frame("MNQM6", base_price=100.0)
    new = _frame("MNQU6", base_price=200.0)

    result = stitch_contract_frames(
        {"MNQM6": old, "MNQU6": new},
        _windows(),
    )

    last_old = result.loc[result["contract"] == "MNQM6"].iloc[-1]
    first_new = result.loc[result["contract"] == "MNQU6"].iloc[0]

    assert last_old["close"] == pytest.approx(102.0)
    assert first_new["close"] == pytest.approx(203.0)
    assert first_new["close"] - last_old["close"] == pytest.approx(101.0)


def test_first_new_contract_bar_is_marked_as_rollover_boundary():
    result = stitch_contract_frames(
        {
            "MNQM6": _frame("MNQM6", base_price=100.0),
            "MNQU6": _frame("MNQU6", base_price=200.0),
        },
        _windows(),
    )

    boundary_rows = result.loc[result["rollover_boundary"]]

    assert len(boundary_rows) == 1
    boundary = boundary_rows.iloc[0]
    assert boundary["contract"] == "MNQU6"
    assert boundary["rollover_from_contract"] == "MNQM6"
    assert boundary["rollover_to_contract"] == "MNQU6"
    assert boundary["rollover_segment"] == 1


def test_contract_mismatch_is_rejected_instead_of_relabelled_silently():
    wrong = _frame("MNQU6")

    with pytest.raises(RolloverError, match="does not match expected contract"):
        prepare_contract_frame(wrong, expected_contract="MNQM6")


def test_duplicate_timestamps_inside_one_contract_are_rejected():
    df = _frame("MNQM6")
    duplicate = df.iloc[[0]].copy()
    df = pd.concat([df, duplicate], ignore_index=True)

    with pytest.raises(RolloverError, match="Duplicate timestamps"):
        prepare_contract_frame(df, expected_contract="MNQM6")


def test_rollover_schedule_rejects_overlap_and_uncovered_gap():
    boundary = pd.Timestamp("2026-06-12 00:03:00", tz="UTC")

    overlapping = [
        ContractWindow("MNQM6", end=boundary),
        ContractWindow("MNQU6", start=boundary - pd.Timedelta(minutes=1)),
    ]
    with pytest.raises(RolloverError, match="overlap"):
        validate_contract_windows(overlapping)

    gapped = [
        ContractWindow("MNQM6", end=boundary),
        ContractWindow("MNQU6", start=boundary + pd.Timedelta(minutes=1)),
    ]
    with pytest.raises(RolloverError, match="uncovered schedule gap"):
        validate_contract_windows(gapped)


def test_missing_contract_dataframe_is_rejected():
    with pytest.raises(RolloverError, match="Missing dataframe"):
        stitch_contract_frames(
            {"MNQM6": _frame("MNQM6")},
            _windows(),
        )


def test_split_rollover_segments_keeps_contracts_isolated_for_downstream_pipeline():
    stitched = stitch_contract_frames(
        {
            "MNQM6": _frame("MNQM6", base_price=100.0),
            "MNQU6": _frame("MNQU6", base_price=200.0),
        },
        _windows(),
    )

    segments = split_rollover_segments(stitched)

    assert len(segments) == 2
    assert segments[0]["contract"].unique().tolist() == ["MNQM6"]
    assert segments[1]["contract"].unique().tolist() == ["MNQU6"]
    assert segments[0]["rollover_segment"].unique().tolist() == [0]
    assert segments[1]["rollover_segment"].unique().tolist() == [1]
    assert segments[0]["timestamp"].max() < segments[1]["timestamp"].min()
