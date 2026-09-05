import pandas as pd
import pytest

from tools.barchart.stitch_barchart_history import BarchartStitchError, stitch_frames


def _frame(contract: str, timestamps: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [pd.Timestamp(x, tz="UTC") for x in timestamps],
            "open": [100.0] * len(timestamps),
            "high": [101.0] * len(timestamps),
            "low": [99.0] * len(timestamps),
            "close": [100.5] * len(timestamps),
            "volume": [10] * len(timestamps),
            "source": ["BARCHART"] * len(timestamps),
            "symbol": ["MNQ"] * len(timestamps),
            "contract": [contract] * len(timestamps),
        }
    )


def test_stitch_frames_uses_new_contract_at_rollover_timestamp():
    old = _frame("NMH22", ["2022-03-13 21:59", "2022-03-13 22:00"])
    new = _frame("NMM22", ["2022-03-13 22:00", "2022-03-13 22:01"])
    rollover = pd.Timestamp("2022-03-13 22:00", tz="UTC")

    stitched, segments = stitch_frames(
        [old, new], ["NMH22", "NMM22"], [rollover]
    )

    assert stitched["timestamp"].tolist() == [
        pd.Timestamp("2022-03-13 21:59", tz="UTC"),
        pd.Timestamp("2022-03-13 22:00", tz="UTC"),
        pd.Timestamp("2022-03-13 22:01", tz="UTC"),
    ]
    assert stitched["contract"].tolist() == ["NMH22", "NMM22", "NMM22"]
    assert stitched["rollover_boundary"].tolist() == [False, True, False]
    assert len(segments) == 2


def test_stitch_frames_rejects_missing_segment_data():
    old = _frame("NMH22", ["2022-03-01 00:00"])
    new = _frame("NMM22", ["2022-03-01 00:00"])
    rollover = pd.Timestamp("2022-04-01 00:00", tz="UTC")

    with pytest.raises(BarchartStitchError, match="no rows in assigned rollover window"):
        stitch_frames([old, new], ["NMH22", "NMM22"], [rollover])


def test_stitch_frames_marks_every_contract_change_once():
    a = _frame("NMH22", ["2022-03-01 00:00", "2022-03-01 00:01"])
    b = _frame("NMM22", ["2022-03-01 00:01", "2022-03-01 00:02"])
    c = _frame("NMU22", ["2022-03-01 00:02", "2022-03-01 00:03"])

    stitched, _ = stitch_frames(
        [a, b, c],
        ["NMH22", "NMM22", "NMU22"],
        [
            pd.Timestamp("2022-03-01 00:01", tz="UTC"),
            pd.Timestamp("2022-03-01 00:02", tz="UTC"),
        ],
    )

    assert int(stitched["rollover_boundary"].sum()) == 2
    assert stitched["timestamp"].duplicated().sum() == 0
    assert stitched["contract"].tolist() == ["NMH22", "NMM22", "NMU22", "NMU22"]
