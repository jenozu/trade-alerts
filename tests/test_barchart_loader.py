from __future__ import annotations

import pandas as pd

from data_loader import DatasetMetadata, load_csv


def test_barchart_intraday_csv_normalizes_latest_and_drops_footer(tmp_path):
    csv_path = tmp_path / "barchart.csv"

    csv_path.write_text(
        "\n".join(
            [
                "Time,Open,High,Low,Latest,Change,%Change,Volume",
                "2026-06-01 00:00,30573.25,30575.50,30571.00,30572.25,-0.75,0.00%,317",
                "2026-06-01 00:01,30571.50,30571.75,30569.75,30569.75,-2.50,-0.01%,217",
                "Downloaded from Barchart.com as of 09-01-2026 05:57pm CDT,,,,,,,",
            ]
        ),
        encoding="utf-8",
    )

    metadata = DatasetMetadata(
        source="BARCHART",
        symbol="MNQ",
        contract="MNQM6",
        source_timezone="America/Chicago",
        filename=csv_path.name,
    )

    result = load_csv(
        csv_path,
        metadata=metadata,
    )

    assert len(result) == 2

    assert list(result["close"]) == [
        30572.25,
        30569.75,
    ]

    assert result["source"].unique().tolist() == [
        "BARCHART"
    ]

    assert result["symbol"].unique().tolist() == [
        "MNQ"
    ]

    assert result["contract"].unique().tolist() == [
        "MNQM6"
    ]

    assert str(result["timestamp"].dt.tz) == "UTC"
    assert str(result["timestamp_et"].dt.tz) == "America/New_York"

    # Midnight Chicago in June = 01:00 New York.
    assert result["timestamp_et"].iloc[0].hour == 1

    assert "Change" in result.columns
    assert "%Change" in result.columns
