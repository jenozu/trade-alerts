from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

DEFAULT_STRATEGY_CONFIG = Path("config/strategy.yaml")
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}


class ScoringError(RuntimeError):
    """Raised when setup scoring cannot be completed safely."""


@dataclass(frozen=True)
class ScoreResult:
    direction: str
    raw_score: float
    score_band: str
    positive_points: float
    penalty_points: float
    disabled: bool
    disable_reason: str | None
    contributions: dict[str, float]


@dataclass(frozen=True)
class ScoringSummary:
    rows: int
    long_candidates: int
    short_candidates: int
    long_high_probability: int
    short_high_probability: int
    long_a_plus_plus: int
    short_a_plus_plus: int
    long_disabled: int
    short_disabled: int
    mean_long_score: float | None
    mean_short_score: float | None
    max_long_score: float | None
    max_short_score: float | None


def load_strategy_config(filepath: str | Path = DEFAULT_STRATEGY_CONFIG) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Strategy configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as exc:
        raise ScoringError(f"Could not load strategy configuration: {path}") from exc
    if not isinstance(config, dict):
        raise ScoringError("strategy.yaml did not produce a dictionary.")
    return config


def validate_input_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ScoringError(f"Missing required columns for scoring: {sorted(missing)}")
    if df.empty:
        raise ScoringError("Cannot score an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise ScoringError("'timestamp' must be a pandas datetime column.")


def bool_value(row: pd.Series, column: str, default: bool = False) -> bool:
    if column not in row.index:
        return default
    value = row[column]
    if pd.isna(value):
        return default
    return bool(value)


def string_value(row: pd.Series, column: str, default: str = "") -> str:
    if column not in row.index:
        return default
    value = row[column]
    if pd.isna(value):
        return default
    return str(value).strip().lower()


def numeric_value(row: pd.Series, column: str, default: float | None = None) -> float | None:
    if column not in row.index:
        return default
    value = row[column]
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def determine_score_band(score: float, config: dict[str, Any]) -> str:
    bands = config.get("score_bands", {})
    for band_name, settings in bands.items():
        minimum = float(settings.get("minimum", 0))
        maximum = float(settings.get("maximum", 100))
        if score >= minimum and score <= maximum:
            return band_name
    return "unknown"


def is_bullish_htf_bias(row: pd.Series) -> bool:
    for column in ["htf_bias", "higher_timeframe_bias", "bias"]:
        value = string_value(row, column)
        if value:
            return value == "bullish"
    return False


def is_bearish_htf_bias(row: pd.Series) -> bool:
    for column in ["htf_bias", "higher_timeframe_bias", "bias"]:
        value = string_value(row, column)
        if value:
            return value == "bearish"
    return False


def htf_bias_known(row: pd.Series) -> bool:
    for column in ["htf_bias", "higher_timeframe_bias", "bias"]:
        value = string_value(row, column)
        if value in {"bullish", "bearish", "neutral"}:
            return True
    return False


def dol_alignment(row: pd.Series, direction: str) -> bool:
    for column in ["dol_direction", "draw_on_liquidity_direction"]:
        value = string_value(row, column)
        if not value:
            continue
        if direction == "long":
            return value in {"bullish", "up", "higher", "buy_side"}
        if direction == "short":
            return value in {"bearish", "down", "lower", "sell_side"}
    return False


def key_location_alignment(row: pd.Series, direction: str) -> bool:
    if direction == "long":
        if bool_value(row, "recent_sell_side_sweep"):
            return True
        if bool_value(row, "bullish_fvg_retest_hold"):
            return True
        if string_value(row, "external_premium_discount") == "discount":
            return True
    else:
        if bool_value(row, "recent_buy_side_sweep"):
            return True
        if bool_value(row, "bearish_fvg_retest_hold"):
            return True
        if string_value(row, "external_premium_discount") == "premium":
            return True
    return False


def liquidity_sweep_alignment(row: pd.Series, direction: str) -> bool:
    if direction == "long":
        return bool_value(row, "sell_side_liquidity_sweep") or bool_value(row, "recent_sell_side_sweep")
    return bool_value(row, "buy_side_liquidity_sweep") or bool_value(row, "recent_buy_side_sweep")


def displacement_alignment(row: pd.Series, direction: str) -> bool:
    if direction == "long":
        return bool_value(row, "bullish_displacement") or bool_value(row, "recent_bullish_displacement")
    return bool_value(row, "bearish_displacement") or bool_value(row, "recent_bearish_displacement")


def structure_shift_alignment(row: pd.Series, direction: str) -> bool:
    if direction == "long":
        return (
            bool_value(row, "bullish_mss")
            or bool_value(row, "recent_bullish_mss")
            or bool_value(row, "bullish_bos")
            or bool_value(row, "recent_bullish_bos")
        )
    return (
        bool_value(row, "bearish_mss")
        or bool_value(row, "recent_bearish_mss")
        or bool_value(row, "bearish_bos")
        or bool_value(row, "recent_bearish_bos")
    )


def fvg_alignment(row: pd.Series, direction: str) -> bool:
    if direction == "long":
        return (
            bool_value(row, "bullish_fvg_created")
            or bool_value(row, "bullish_fvg_retest_hold")
            or bool_value(row, "bullish_ifvg_created")
            or bool_value(row, "bullish_core_plus_fvg")
            or bool_value(row, "bullish_core_plus_fvg_retest")
            or bool_value(row, "bullish_pd_array_respected_recent")
            or bool_value(row, "bullish_ifvg_respected_recent")
        )
    return (
        bool_value(row, "bearish_fvg_created")
        or bool_value(row, "bearish_fvg_retest_hold")
        or bool_value(row, "bearish_ifvg_created")
        or bool_value(row, "bearish_core_plus_fvg")
        or bool_value(row, "bearish_core_plus_fvg_retest")
        or bool_value(row, "bearish_pd_array_respected_recent")
        or bool_value(row, "bearish_ifvg_respected_recent")
    )


def relative_volume_confirmation(row: pd.Series, config: dict[str, Any]) -> bool:
    if bool_value(row, "volume_spike_both") or bool_value(row, "volume_spike_any"):
        return True
    section = config.get("relative_volume", {})
    threshold = float(section.get("initial_signal_threshold", 1.50))
    for column in ["rvol_time_of_day", "rvol_rolling"]:
        value = numeric_value(row, column)
        if value is not None and value >= threshold:
            return True
    return False


def snr_confirmation(row: pd.Series, direction: str, config: dict[str, Any]) -> bool:
    section = config.get("snr", {})
    thresholds = section.get("initial_thresholds", {})
    strong_minimum = float(thresholds.get("strong_minimum", 1.20))
    snr_5m = numeric_value(row, "snr_5m")
    direction_5m = string_value(row, "snr_direction_5m")
    alignment = string_value(row, "snr_alignment")

    if direction == "long":
        direction_ok = direction_5m == "bullish"
        alignment_ok = alignment in {"strong_bullish", "partial_bullish"}
    else:
        direction_ok = direction_5m == "bearish"
        alignment_ok = alignment in {"strong_bearish", "partial_bearish"}

    magnitude_ok = snr_5m is not None and snr_5m >= strong_minimum
    return magnitude_ok and (direction_ok or alignment_ok)


def snr_conflict(row: pd.Series, direction: str) -> bool:
    snr_direction = string_value(row, "snr_direction_5m")
    if direction == "long":
        return snr_direction == "bearish"
    return snr_direction == "bullish"


def premium_discount_alignment(row: pd.Series, direction: str) -> bool:
    location = string_value(row, "external_premium_discount")
    if not location:
        location = string_value(row, "internal_premium_discount")
    if direction == "long":
        return location == "discount"
    return location == "premium"


def calculate_room_to_target(
    row: pd.Series,
    direction: str,
    config: dict[str, Any],
) -> tuple[bool, float | None]:
    section = config.get("room_to_target", {})
    minimum = float(section.get("minimum_points", 25.0))
    if direction == "long":
        distance = numeric_value(row, "distance_to_unswept_liquidity_above")
    else:
        distance = numeric_value(row, "distance_to_unswept_liquidity_below")
    if distance is None:
        return False, None
    return distance >= minimum, distance


def major_obstacle_present(row: pd.Series, direction: str, config: dict[str, Any]) -> bool:
    room_ok, distance = calculate_room_to_target(row, direction, config)
    if distance is None:
        return False
    return not room_ok


def data_is_healthy(row: pd.Series) -> bool:
    for column in ["data_healthy", "healthy_data"]:
        if column in row.index:
            return bool_value(row, column, default=True)
    return True


def entry_window_valid(row: pd.Series) -> bool:
    if "new_entry_allowed" in row.index:
        return bool_value(row, "new_entry_allowed")
    if "is_strategy_window" in row.index:
        return bool_value(row, "is_strategy_window")
    return True


def thesis_valid(row: pd.Series, direction: str) -> bool:
    specific_column = "bullish_thesis_valid" if direction == "long" else "bearish_thesis_valid"
    if specific_column in row.index:
        return bool_value(row, specific_column)
    if "thesis_invalidated" in row.index:
        return not bool_value(row, "thesis_invalidated")
    return True


def stale_setup(row: pd.Series, direction: str) -> bool:
    column = "bullish_setup_stale" if direction == "long" else "bearish_setup_stale"
    return bool_value(row, column, default=False)


def failed_retest(row: pd.Series, direction: str) -> bool:
    directional = "bullish_failed_retest" if direction == "long" else "bearish_failed_retest"
    if directional in row.index:
        return bool_value(row, directional)
    return bool_value(row, "failed_retest", default=False)


def score_setup(
    row: pd.Series,
    *,
    direction: str,
    config: dict[str, Any],
) -> ScoreResult:
    direction = direction.strip().lower()
    if direction not in {"long", "short"}:
        raise ValueError("direction must be 'long' or 'short'.")

    scoring = config.get("scoring", {})
    positive_weights = scoring.get("positive_weights", {})
    penalties = scoring.get("penalties", {})
    hard_disable = scoring.get("hard_disable", {})
    clamp = scoring.get("clamp", {})
    contributions: dict[str, float] = {}

    htf_aligned = is_bullish_htf_bias(row) if direction == "long" else is_bearish_htf_bias(row)
    contributions["higher_timeframe_bias"] = float(positive_weights.get("higher_timeframe_bias", 0)) if htf_aligned else 0.0

    dol_ok = dol_alignment(row, direction)
    contributions["draw_on_liquidity"] = float(positive_weights.get("draw_on_liquidity", 0)) if dol_ok else 0.0

    location_ok = key_location_alignment(row, direction)
    contributions["key_location"] = float(positive_weights.get("key_location", 0)) if location_ok else 0.0

    sweep_ok = liquidity_sweep_alignment(row, direction)
    contributions["liquidity_sweep"] = float(positive_weights.get("liquidity_sweep", 0)) if sweep_ok else 0.0

    displacement_ok = displacement_alignment(row, direction)
    contributions["displacement"] = float(positive_weights.get("displacement", 0)) if displacement_ok else 0.0

    structure_ok = structure_shift_alignment(row, direction)
    contributions["structure_shift"] = float(positive_weights.get("structure_shift", 0)) if structure_ok else 0.0

    fvg_ok = fvg_alignment(row, direction)
    contributions["fvg_or_retest"] = float(positive_weights.get("fvg_or_retest", 0)) if fvg_ok else 0.0

    rvol_ok = relative_volume_confirmation(row, config)
    contributions["relative_volume"] = float(positive_weights.get("relative_volume", 0)) if rvol_ok else 0.0

    snr_ok = snr_confirmation(row, direction, config)
    contributions["signal_to_noise"] = float(positive_weights.get("signal_to_noise", 0)) if snr_ok else 0.0

    pd_ok = premium_discount_alignment(row, direction)
    contributions["premium_discount"] = float(positive_weights.get("premium_discount", 0)) if pd_ok else 0.0

    room_ok, _ = calculate_room_to_target(row, direction, config)
    contributions["room_to_target"] = float(positive_weights.get("room_to_target", 0)) if room_ok else 0.0

    bias_known = htf_bias_known(row)
    htf_conflict = (
        bias_known and is_bearish_htf_bias(row)
        if direction == "long"
        else bias_known and is_bullish_htf_bias(row)
    )
    contributions["penalty_htf_conflict"] = float(penalties.get("higher_timeframe_conflict", 0)) if htf_conflict else 0.0

    snr_is_conflict = snr_conflict(row, direction)
    contributions["penalty_snr_conflict"] = float(penalties.get("snr_conflict", 0)) if snr_is_conflict else 0.0

    obstacle = major_obstacle_present(row, direction, config)
    contributions["penalty_major_obstacle"] = float(penalties.get("major_obstacle", 0)) if obstacle else 0.0

    stale = stale_setup(row, direction)
    contributions["penalty_stale_setup"] = float(penalties.get("stale_setup", 0)) if stale else 0.0

    failed = failed_retest(row, direction)
    contributions["penalty_failed_retest"] = float(penalties.get("failed_retest", 0)) if failed else 0.0

    healthy = data_is_healthy(row)
    contributions["penalty_data_quality"] = float(penalties.get("data_quality_warning", 0)) if not healthy else 0.0

    positive_points = sum(value for key, value in contributions.items() if not key.startswith("penalty_"))
    penalty_points = sum(value for key, value in contributions.items() if key.startswith("penalty_"))
    raw_score = positive_points + penalty_points
    minimum_score = float(clamp.get("minimum", 0))
    maximum_score = float(clamp.get("maximum", 100))
    raw_score = float(np.clip(raw_score, minimum_score, maximum_score))

    disabled = False
    disable_reason: str | None = None
    if hard_disable.get("unhealthy_data", True) and not healthy:
        disabled = True
        disable_reason = "unhealthy_data"
    elif hard_disable.get("invalidated_thesis", True) and not thesis_valid(row, direction):
        disabled = True
        disable_reason = "invalidated_thesis"
    elif hard_disable.get("outside_entry_window", True) and not entry_window_valid(row):
        disabled = True
        disable_reason = "outside_entry_window"

    score_band = "disabled" if disabled else determine_score_band(raw_score, config)

    return ScoreResult(
        direction=direction,
        raw_score=raw_score,
        score_band=score_band,
        positive_points=float(positive_points),
        penalty_points=float(penalty_points),
        disabled=disabled,
        disable_reason=disable_reason,
        contributions=contributions,
    )


def enrich_scores(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    validate_input_dataframe(df)
    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    scoring = config.get("scoring", {})
    if not scoring.get("enabled", True):
        return result

    long_scores = []
    short_scores = []
    for _, row in result.iterrows():
        long_scores.append(score_setup(row, direction="long", config=config))
        short_scores.append(score_setup(row, direction="short", config=config))

    result["long_raw_score"] = [score.raw_score for score in long_scores]
    result["short_raw_score"] = [score.raw_score for score in short_scores]
    result["long_score_band"] = [score.score_band for score in long_scores]
    result["short_score_band"] = [score.score_band for score in short_scores]
    result["long_positive_points"] = [score.positive_points for score in long_scores]
    result["short_positive_points"] = [score.positive_points for score in short_scores]
    result["long_penalty_points"] = [score.penalty_points for score in long_scores]
    result["short_penalty_points"] = [score.penalty_points for score in short_scores]
    result["long_disabled"] = [score.disabled for score in long_scores]
    result["short_disabled"] = [score.disabled for score in short_scores]
    result["long_disable_reason"] = [score.disable_reason for score in long_scores]
    result["short_disable_reason"] = [score.disable_reason for score in short_scores]

    contribution_names = set()
    for score in long_scores + short_scores:
        contribution_names.update(score.contributions.keys())

    for contribution in sorted(contribution_names):
        result[f"long_score_{contribution}"] = [score.contributions.get(contribution, 0.0) for score in long_scores]
        result[f"short_score_{contribution}"] = [score.contributions.get(contribution, 0.0) for score in short_scores]

    result["score_edge"] = result["long_raw_score"] - result["short_raw_score"]
    result["score_edge_abs"] = result["score_edge"].abs()
    result["preferred_score_direction"] = np.select(
        [
            result["long_raw_score"] > result["short_raw_score"],
            result["short_raw_score"] > result["long_raw_score"],
        ],
        ["long", "short"],
        default="neutral",
    )

    actionable_bands = {"near_trigger", "high_probability", "a_plus_plus"}
    result["long_candidate"] = result["long_score_band"].isin(actionable_bands) & ~result["long_disabled"]
    result["short_candidate"] = result["short_score_band"].isin(actionable_bands) & ~result["short_disabled"]
    result["candidate_any"] = result["long_candidate"] | result["short_candidate"]
    return result


def add_score_change_events(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    events = config.get("events", {})
    threshold = float(events.get("score_change_threshold", 8))
    for direction in ["long", "short"]:
        score_col = f"{direction}_raw_score"
        band_col = f"{direction}_score_band"
        result[f"{direction}_score_delta"] = result[score_col] - result[score_col].shift(1)
        result[f"{direction}_score_large_change"] = result[f"{direction}_score_delta"].abs() >= threshold
        result[f"{direction}_score_band_changed"] = result[band_col] != result[band_col].shift(1)
        result[f"{direction}_score_improved"] = result[f"{direction}_score_delta"] > 0
        result[f"{direction}_score_deteriorated"] = result[f"{direction}_score_delta"] < 0

    result["score_event_any"] = (
        result["long_score_large_change"]
        | result["short_score_large_change"]
        | result["long_score_band_changed"]
        | result["short_score_band_changed"]
    )
    return result


def build_candidate_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        for direction in ["long", "short"]:
            candidate_col = f"{direction}_candidate"
            if not bool_value(row, candidate_col):
                continue
            prefix = f"{direction}_"
            record: dict[str, Any] = {
                "timestamp": row["timestamp"],
                "timestamp_et": row.get("timestamp_et"),
                "session_date": row.get("session_date"),
                "direction": direction,
                "close": float(row["close"]),
                "raw_score": row[f"{direction}_raw_score"],
                "score_band": row[f"{direction}_score_band"],
                "positive_points": row[f"{direction}_positive_points"],
                "penalty_points": row[f"{direction}_penalty_points"],
                "score_edge": row.get("score_edge"),
                "preferred_score_direction": row.get("preferred_score_direction"),
                "htf_bias": row.get("htf_bias"),
                "dol_direction": row.get("dol_direction"),
                "snr_1m": row.get("snr_1m"),
                "snr_5m": row.get("snr_5m"),
                "snr_15m": row.get("snr_15m"),
                "snr_alignment": row.get("snr_alignment"),
                "rvol_rolling": row.get("rvol_rolling"),
                "rvol_time_of_day": row.get("rvol_time_of_day"),
                "distance_to_liquidity_above": row.get("distance_to_unswept_liquidity_above"),
                "distance_to_liquidity_below": row.get("distance_to_unswept_liquidity_below"),
            }
            for column in df.columns:
                if column.startswith(f"{direction}_score_"):
                    generic_name = column[len(prefix):]
                    record[generic_name] = row[column]
            rows.append(record)

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["timestamp", "direction"]).reset_index(drop=True)
    return result


def scoring_summary(df: pd.DataFrame) -> ScoringSummary:
    long_scores = df["long_raw_score"].dropna()
    short_scores = df["short_raw_score"].dropna()
    return ScoringSummary(
        rows=len(df),
        long_candidates=int(df["long_candidate"].sum()),
        short_candidates=int(df["short_candidate"].sum()),
        long_high_probability=int((df["long_score_band"] == "high_probability").sum()),
        short_high_probability=int((df["short_score_band"] == "high_probability").sum()),
        long_a_plus_plus=int((df["long_score_band"] == "a_plus_plus").sum()),
        short_a_plus_plus=int((df["short_score_band"] == "a_plus_plus").sum()),
        long_disabled=int(df["long_disabled"].sum()),
        short_disabled=int(df["short_disabled"].sum()),
        mean_long_score=float(long_scores.mean()) if not long_scores.empty else None,
        mean_short_score=float(short_scores.mean()) if not short_scores.empty else None,
        max_long_score=float(long_scores.max()) if not long_scores.empty else None,
        max_short_score=float(short_scores.max()) if not short_scores.empty else None,
    )


def score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for direction in ["long", "short"]:
        counts = df[f"{direction}_score_band"].value_counts(dropna=False)
        for band, count in counts.items():
            records.append({"direction": direction, "score_band": band, "rows": int(count)})
    return pd.DataFrame(records)


def save_scoring_outputs(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    scored_path = directory / "nq_1m_scored.parquet"
    candidate_path = directory / "candidate_setups.csv"
    distribution_path = directory / "score_distribution.csv"
    event_path = directory / "score_events.csv"

    df.to_parquet(scored_path, index=False)
    build_candidate_table(df).to_csv(candidate_path, index=False)
    score_distribution(df).to_csv(distribution_path, index=False)

    if "score_event_any" in df.columns:
        events = df.loc[df["score_event_any"]].copy()
    else:
        events = df.iloc[0:0].copy()

    event_columns = [
        "timestamp",
        "timestamp_et",
        "session_date",
        "close",
        "long_raw_score",
        "long_score_band",
        "long_score_delta",
        "short_raw_score",
        "short_score_band",
        "short_score_delta",
        "score_edge",
        "preferred_score_direction",
        "snr_5m",
        "snr_alignment",
        "rvol_time_of_day",
        "liquidity_sweep_any",
        "bullish_mss",
        "bearish_mss",
        "bullish_fvg_retest_hold",
        "bearish_fvg_retest_hold",
    ]
    available = [column for column in event_columns if column in events.columns]
    events[available].to_csv(event_path, index=False)

    return {
        "scored_features": scored_path,
        "candidate_setups": candidate_path,
        "score_distribution": distribution_path,
        "score_events": event_path,
    }


if __name__ == "__main__":
    input_file = Path("data/processed/structure/nq_1m_structure.parquet")
    config_file = Path("config/strategy.yaml")
    output_directory = Path("data/processed/scoring")

    if not input_file.exists():
        print("\nStructure-enriched dataset not found.")
        print(f"Expected:\n{input_file}\n")
    else:
        print("\nLoading strategy configuration...")
        strategy_config = load_strategy_config(config_file)
        print("Loading structure-enriched market data...")
        data = pd.read_parquet(input_file)
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        if "timestamp_et" in data.columns:
            data["timestamp_et"] = data["timestamp"].dt.tz_convert("America/New_York")

        print(f"Loaded {len(data):,} bars.")
        print("Calculating interpretable setup scores...")
        scored = enrich_scores(data, strategy_config)
        scored = add_score_change_events(scored, strategy_config)
        summary = scoring_summary(scored)

        print("\n============================================================")
        print("SCORING SUMMARY")
        print("============================================================")
        print(f"Rows: {summary.rows:,}")
        print(f"Long candidates: {summary.long_candidates:,}")
        print(f"Short candidates: {summary.short_candidates:,}")
        print(f"Max long score: {summary.max_long_score}")
        print(f"Max short score: {summary.max_short_score}")

        saved = save_scoring_outputs(scored, output_directory)
        print("\nSaved files:")
        for name, filepath in saved.items():
            print(f"  {name}: {filepath}")
        print("\nDone.\n")
