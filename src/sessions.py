from __future__ import annotations

from dataclasses import dataclass
from datetime import time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

DEFAULT_CONFIG = Path("config/sessions.yaml")
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


class SessionError(RuntimeError):
    """Raised when session enrichment cannot be completed safely."""


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start: str
    end: str


def load_sessions_config(filepath: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Session configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise SessionError("sessions.yaml did not produce a dictionary.")
    return config


def _parse_hhmm(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour=hour, minute=minute)


def _time_mask(series: pd.Series, start: str, end: str) -> pd.Series:
    start_t = _parse_hhmm(start)
    end_t = _parse_hhmm(end)
    values = series.dt.time
    if start_t < end_t:
        return (values >= start_t) & (values < end_t)
    if start_t > end_t:
        return (values >= start_t) | (values < end_t)
    return pd.Series(True, index=series.index)


def _session_date(et: pd.Series, globex_start: str) -> pd.Series:
    cutoff = _parse_hhmm(globex_start)
    dates = et.dt.date.astype("object")
    after = et.dt.time >= cutoff
    adjusted = []
    for d, is_after in zip(dates, after):
        adjusted.append(d + timedelta(days=1) if is_after else d)
    return pd.Series(adjusted, index=et.index)


def _window_config(
    config: dict[str, Any],
    name: str,
    default_start: str,
    default_end: str,
) -> tuple[str, str]:
    section = config.get("sessions", {}).get(name, {})
    return str(section.get("start", default_start)), str(section.get("end", default_end))


def _running_extreme(
    df: pd.DataFrame,
    mask: pd.Series,
    session_date: pd.Series,
    column: str,
    kind: str,
) -> pd.Series:
    values = df[column].where(mask)
    grouped = values.groupby(session_date)
    return grouped.cummax() if kind == "max" else grouped.cummin()


def _final_by_session(
    df: pd.DataFrame,
    mask: pd.Series,
    column: str,
    agg: str,
) -> pd.Series:
    subset = df.loc[mask, ["session_date", column]]
    if subset.empty:
        return pd.Series(dtype=float)
    grouped = subset.groupby("session_date")[column]
    return grouped.max() if agg == "max" else grouped.min()


def _availability_timestamp(df: pd.DataFrame, hhmm: str) -> pd.Series:
    """Build the real ET timestamp at which a same-session value becomes known.

    session_date intentionally rolls at the Globex open. Therefore an evening bar
    at 18:00 ET may already belong to the following session_date. Comparing only
    clock times (for example, 18:00 >= 09:30) leaks next-morning information into
    the prior evening. This helper anchors the availability time to session_date.
    """

    timezone = df["timestamp_et"].dt.tz
    naive = pd.to_datetime(df["session_date"].astype(str) + " " + hhmm)
    return naive.dt.tz_localize(timezone)


def _make_available(
    df: pd.DataFrame,
    values_by_session: pd.Series,
    *,
    available_hhmm: str,
    causal: bool,
) -> pd.Series:
    mapped = df["session_date"].map(values_by_session)
    if not causal:
        return mapped
    available_at = _availability_timestamp(df, available_hhmm)
    visible = df["timestamp_et"] >= available_at
    return mapped.where(visible)


def _opening_range(
    df: pd.DataFrame,
    minutes: int,
    causal: bool,
) -> tuple[pd.Series, pd.Series]:
    start = _parse_hhmm("09:30")
    end_dt_minutes = 9 * 60 + 30 + minutes
    end = time(end_dt_minutes // 60, end_dt_minutes % 60)
    end_hhmm = f"{end.hour:02d}:{end.minute:02d}"

    t = df["timestamp_et"].dt.time
    mask = (t >= start) & (t < end)
    highs = _final_by_session(df, mask, "high", "max")
    lows = _final_by_session(df, mask, "low", "min")
    mapped_high = df["session_date"].map(highs)
    mapped_low = df["session_date"].map(lows)

    if causal:
        available_at = _availability_timestamp(df, end_hhmm)
        visible = df["timestamp_et"] >= available_at
        mapped_high = mapped_high.where(visible)
        mapped_low = mapped_low.where(visible)

    return mapped_high, mapped_low


def enrich_with_sessions(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    causal: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise SessionError(f"Missing required columns: {sorted(missing)}")

    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    if not pd.api.types.is_datetime64_any_dtype(result["timestamp"]):
        raise SessionError("'timestamp' must be datetime.")
    if getattr(result["timestamp"].dt, "tz", None) is None:
        raise SessionError("'timestamp' must be timezone-aware.")

    timezone = str(config.get("timezones", {}).get("trading", "America/New_York"))
    result["timestamp_et"] = result["timestamp"].dt.tz_convert(timezone)

    globex_start, globex_end = _window_config(config, "globex", "18:00", "17:00")
    rth_start, rth_end = _window_config(config, "rth", "09:30", "16:00")
    pm_start, pm_end = _window_config(config, "premarket", "04:00", "09:30")
    on_start, on_end = _window_config(config, "overnight", "18:00", "09:30")
    london_start, london_end = _window_config(config, "london", "02:00", "05:00")
    strategy_start, strategy_end = _window_config(
        config,
        "strategy_window",
        "09:30",
        "10:30",
    )

    result["session_date"] = _session_date(result["timestamp_et"], globex_start)
    result["is_globex"] = _time_mask(result["timestamp_et"], globex_start, globex_end)
    result["is_rth"] = _time_mask(result["timestamp_et"], rth_start, rth_end)
    result["is_premarket"] = _time_mask(result["timestamp_et"], pm_start, pm_end)
    result["is_overnight"] = _time_mask(result["timestamp_et"], on_start, on_end)
    result["is_london"] = _time_mask(result["timestamp_et"], london_start, london_end)
    result["is_strategy_window"] = _time_mask(
        result["timestamp_et"],
        strategy_start,
        strategy_end,
    )
    result["new_entry_allowed"] = result["is_strategy_window"]

    # Developing levels are causal by construction.
    result["developing_pmh"] = _running_extreme(
        result,
        result["is_premarket"],
        result["session_date"],
        "high",
        "max",
    )
    result["developing_pml"] = _running_extreme(
        result,
        result["is_premarket"],
        result["session_date"],
        "low",
        "min",
    )
    result["developing_onh"] = _running_extreme(
        result,
        result["is_overnight"],
        result["session_date"],
        "high",
        "max",
    )
    result["developing_onl"] = _running_extreme(
        result,
        result["is_overnight"],
        result["session_date"],
        "low",
        "min",
    )
    result["developing_loh"] = _running_extreme(
        result,
        result["is_london"],
        result["session_date"],
        "high",
        "max",
    )
    result["developing_lol"] = _running_extreme(
        result,
        result["is_london"],
        result["session_date"],
        "low",
        "min",
    )

    pmh = _final_by_session(result, result["is_premarket"], "high", "max")
    pml = _final_by_session(result, result["is_premarket"], "low", "min")
    onh = _final_by_session(result, result["is_overnight"], "high", "max")
    onl = _final_by_session(result, result["is_overnight"], "low", "min")
    loh = _final_by_session(result, result["is_london"], "high", "max")
    lol = _final_by_session(result, result["is_london"], "low", "min")

    result["pmh"] = _make_available(
        result,
        pmh,
        available_hhmm=pm_end,
        causal=causal,
    )
    result["pml"] = _make_available(
        result,
        pml,
        available_hhmm=pm_end,
        causal=causal,
    )
    result["onh"] = _make_available(
        result,
        onh,
        available_hhmm=on_end,
        causal=causal,
    )
    result["onl"] = _make_available(
        result,
        onl,
        available_hhmm=on_end,
        causal=causal,
    )
    result["loh"] = _make_available(
        result,
        loh,
        available_hhmm=london_end,
        causal=causal,
    )
    result["lol"] = _make_available(
        result,
        lol,
        available_hhmm=london_end,
        causal=causal,
    )

    # Previous-day levels use the completed prior RTH session only.
    # These are intentionally available as soon as the next Globex session starts.
    rth_high = _final_by_session(result, result["is_rth"], "high", "max")
    rth_low = _final_by_session(result, result["is_rth"], "low", "min")
    ordered_dates = sorted(set(result["session_date"]))
    prev_high: dict[Any, float] = {}
    prev_low: dict[Any, float] = {}
    for position, session in enumerate(ordered_dates):
        if position == 0:
            continue
        previous_session = ordered_dates[position - 1]
        if previous_session in rth_high.index:
            prev_high[session] = float(rth_high.loc[previous_session])
            prev_low[session] = float(rth_low.loc[previous_session])
    result["pdh"] = result["session_date"].map(prev_high)
    result["pdl"] = result["session_date"].map(prev_low)

    rth_open = result.loc[result["is_rth"]].groupby("session_date")["open"].first()
    mapped_open = result["session_date"].map(rth_open)
    if causal:
        available_at = _availability_timestamp(result, rth_start)
        mapped_open = mapped_open.where(result["timestamp_et"] >= available_at)
    result["rth_open"] = mapped_open

    for minutes in (5, 15, 30):
        high, low = _opening_range(result, minutes, causal)
        result[f"or{minutes}_high"] = high
        result[f"or{minutes}_low"] = low

    # Alias names used in various earlier notes.
    result["orh_5"] = result["or5_high"]
    result["orl_5"] = result["or5_low"]
    result["orh_15"] = result["or15_high"]
    result["orl_15"] = result["or15_low"]
    result["orh_30"] = result["or30_high"]
    result["orl_30"] = result["or30_low"]

    level_rows: list[dict[str, Any]] = []
    for session in ordered_dates:
        mask = result["session_date"] == session
        subset = result.loc[mask]

        def last_non_na(column: str):
            values = subset[column].dropna()
            return values.iloc[-1] if len(values) else np.nan

        level_rows.append(
            {
                "session_date": session,
                "pdh": last_non_na("pdh"),
                "pdl": last_non_na("pdl"),
                "pmh": pmh.get(session, np.nan),
                "pml": pml.get(session, np.nan),
                "onh": onh.get(session, np.nan),
                "onl": onl.get(session, np.nan),
                "loh": loh.get(session, np.nan),
                "lol": lol.get(session, np.nan),
                "rth_open": rth_open.get(session, np.nan),
                "or5_high": last_non_na("or5_high"),
                "or5_low": last_non_na("or5_low"),
                "or15_high": last_non_na("or15_high"),
                "or15_low": last_non_na("or15_low"),
                "or30_high": last_non_na("or30_high"),
                "or30_low": last_non_na("or30_low"),
            }
        )

    levels = pd.DataFrame(level_rows)
    return result, levels


def save_session_outputs(
    enriched: pd.DataFrame,
    levels: pd.DataFrame,
    output_directory: str | Path,
) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    feature_path = directory / "nq_1m_sessions.parquet"
    level_path = directory / "session_levels.csv"
    try:
        enriched.to_parquet(feature_path, index=False)
    except ImportError as exc:
        raise SessionError("Saving Parquet requires pyarrow.") from exc
    levels.to_csv(level_path, index=False)
    return {"session_features": feature_path, "session_levels": level_path}
