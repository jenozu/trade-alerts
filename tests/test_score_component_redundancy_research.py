import pandas as pd

from score_component_lift_research import COMPONENTS
from score_component_redundancy_research import (
    analyze,
    summary_frame,
)


def test_r43_smoke():
    rows = []

    for i in range(10):
        row = {
            "raw_score":
                80.0 if i >= 5 else 70.0,

            "net_result_points":
                25.0 if i >= 5 else -25.0,

            "tp1_hit":
                i >= 5,

            "tp2_hit":
                False,

            "tp3_hit":
                False,

            "tp4_hit":
                False,

            "stop_hit":
                i < 5,

            "mfe_points":
                30.0 if i >= 5 else 5.0,

            "mae_points":
                5.0 if i >= 5 else 25.0,
        }

        for component in COMPONENTS:
            row[f"{component}_active"] = (
                i >= 5
            )

        rows.append(row)

    df = pd.DataFrame(rows)

    result = analyze(df)

    summary = summary_frame(result)

    assert len(result["pairs"]) > 0
    assert not summary.empty
    assert "phi" in summary.columns
