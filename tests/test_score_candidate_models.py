import pandas as pd

from score_candidate_models import (
    CANDIDATE_WEIGHTS,
    POSITIVE_COMPONENTS,
    analyze,
    validate_candidates,
)


def test_candidate_totals():
    validate_candidates()

    for weights in (
        CANDIDATE_WEIGHTS.values()
    ):
        assert sum(weights.values()) == 100


def test_candidate_rescore_smoke(tmp_path):
    current = {
        "higher_timeframe_bias": 10,
        "draw_on_liquidity": 10,
        "key_location": 8,
        "liquidity_sweep": 14,
        "displacement": 12,
        "structure_shift": 12,
        "fvg_or_retest": 8,
        "relative_volume": 6,
        "signal_to_noise": 10,
        "premium_discount": 4,
        "room_to_target": 6,
    }

    config = tmp_path / "strategy.yaml"

    import yaml

    config.write_text(
        yaml.safe_dump({
            "scoring": {
                "positive_weights":
                    current
            }
        })
    )

    rows = []

    for i in range(10):
        row = {
            "raw_score": 100.0,
            "net_result_points":
                25.0 if i >= 5 else -25.0,
            "tp1_hit": i >= 5,
            "tp2_hit": False,
            "tp3_hit": False,
            "tp4_hit": False,
            "stop_hit": i < 5,
            "mfe_points":
                30.0 if i >= 5 else 5.0,
            "mae_points":
                5.0 if i >= 5 else 25.0,
        }

        for component in (
            POSITIVE_COMPONENTS
        ):
            row[
                f"{component}_value"
            ] = current[component]

        for penalty in [
            "penalty_data_quality",
            "penalty_failed_retest",
            "penalty_htf_conflict",
            "penalty_major_obstacle",
            "penalty_snr_conflict",
            "penalty_stale_setup",
        ]:
            row[
                f"{penalty}_value"
            ] = 0.0

        rows.append(row)

    df = pd.DataFrame(rows)

    result, scored = analyze(
        df,
        config,
    )

    assert len(scored) == 10

    assert (
        result[
            "baseline_reconstruction"
        ]["mae"]
        == 0.0
    )

    assert set(
        result["performance"]
    ) == set(
        CANDIDATE_WEIGHTS
    )
