from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from data_clock import filter_as_of, normalize_as_of

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


_WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

DEFAULT_WEEK_START_DAY = "sunday"
DEFAULT_WEEK_START_TIME = "18:00"
DEFAULT_WEEK_END_DAY = "friday"
DEFAULT_WEEK_END_TIME = "17:00"

# Sessions the morning engine requires to be present in the data before it can
# compute its levels. This is the fallback used when config/sessions.yaml does
# not declare ``validation.required_sessions``; the config is authoritative and
# may extend or narrow this list.
DEFAULT_REQUIRED_SESSIONS: tuple[str, ...] = (
    "overnight",
    "london",
    "asia",
    "premarket",
)


def _week_config(config: dict[str, Any]) -> dict[str, str]:
    week = config.get("week", {}) or {}
    return {
        "start_day": str(week.get("start_day", DEFAULT_WEEK_START_DAY)).strip().lower(),
        "start_time": str(week.get("start_time", DEFAULT_WEEK_START_TIME)).strip(),
        "end_day": str(week.get("end_day", DEFAULT_WEEK_END_DAY)).strip().lower(),
        "end_time": str(week.get("end_time", DEFAULT_WEEK_END_TIME)).strip(),
    }


def _futures_week_start(et: pd.Series, week_config: dict[str, str]) -> pd.Series:
    """Return each row's most recent futures-week start instant (tz-aware ET).

    The futures week starts at the configured day/time (default Sunday 18:00
    ET). The configured end (default Friday 17:00 ET) documents when the
    market closes; no bars exist between that close and the next week start.
    """
    start_dow = _WEEKDAY_INDEX[week_config["start_day"]]
    start_hour, start_minute = (
        int(part) for part in week_config["start_time"].split(":", 1)
    )
    start_time_of_day = time(start_hour, start_minute)
    timezone = et.dt.tz
    dates = et.dt.date.astype("object")
    weekdays = et.dt.dayofweek
    times_of_day = et.dt.time
    anchor_datetimes = []
    for day, weekday, time_of_day in zip(dates, weekdays, times_of_day):
        anchor_date = day - timedelta(days=(weekday - start_dow) % 7)
        # Rows earlier than the anchor instant on the anchor day belong to the
        # previous futures week (relevant only on the anchor weekday).
        if weekday == start_dow and time_of_day < start_time_of_day:
            anchor_date = anchor_date - timedelta(days=7)
        anchor_datetimes.append(
            datetime.combine(anchor_date, start_time_of_day)
        )
    return pd.Series(anchor_datetimes, index=et.index).dt.tz_localize(timezone)


def _futures_week_end(
    week_start: pd.Series,
    week_config: dict[str, str],
) -> pd.Series:
    """Return each row's futures-week end instant (tz-aware ET).

    The configured end day/time (default Friday 17:00 ET) is applied to the
    calendar week of each row's futures-week start (default Sunday 18:00 ET).
    The futures week is half-open [start, end): a bar opening exactly at the
    end instant belongs to no futures week.
    """
    start_dow = _WEEKDAY_INDEX[week_config["start_day"]]
    end_dow = _WEEKDAY_INDEX[week_config["end_day"]]
    end_hour, end_minute = (
        int(part) for part in week_config["end_time"].split(":", 1)
    )
    end_time_of_day = time(end_hour, end_minute)
    offset_days = (end_dow - start_dow) % 7
    timezone = week_start.dt.tz
    dates = week_start.dt.date.astype("object")
    end_datetimes = [
        datetime.combine(day + timedelta(days=offset_days), end_time_of_day)
        for day in dates
    ]
    return pd.Series(end_datetimes, index=week_start.index).dt.tz_localize(timezone)


def _availability_hhmm(config: dict[str, Any], key: str, default: str) -> str:
    """Read a level availability time from config, falling back to ``default``."""
    availability = config.get("level_availability", {}) or {}
    return str(availability.get(key, default))


# The sessions enrichment operates on the master one-minute feed
# (config/sessions.yaml ``timeframes.master``). A row opening at T is
# knowable only from its own completion, T + 1 minute (the as_of contract:
# ``available_at == timestamp + bar_duration``). Finalized-level availability
# is therefore evaluated against each row's completion instant, never against
# its bar-open timestamp: a window that finalizes at 05:00 ET is first visible
# on the 04:59 bar (which completes exactly at 05:00), so a completed-prefix
# analysis at ``as_of == 05:00 ET`` sees the finalized level with no
# one-minute delay and no exposure of incomplete bars.
_MASTER_BAR_DURATION = timedelta(minutes=1)


def _row_known_at(timestamp_et: pd.Series) -> pd.Series:
    """The instant at which each 1m row may influence analysis (its close)."""
    return timestamp_et + _MASTER_BAR_DURATION


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


def _availability_timestamp(
    df: pd.DataFrame,
    hhmm: str,
    *,
    globex_start: str | None = None,
) -> pd.Series:
    """Build the real ET timestamp at which a same-session value becomes known.

    session_date intentionally rolls at the Globex open. Therefore an evening bar
    at 18:00 ET may already belong to the following session_date. Comparing only
    clock times (for example, 18:00 >= 09:30) leaks next-morning information into
    the prior evening. This helper anchors the availability time to session_date.

    Availability times at or after the Globex open (for example
    previous_day_levels.available_from: 18:00) land on the *next* session's
    opening evening, one calendar day after the current session's own open. When
    ``globex_start`` is supplied, such anchors are rolled back one calendar day
    so the value becomes visible from the current session's opening evening.
    """
    timezone = df["timestamp_et"].dt.tz
    naive = pd.to_datetime(df["session_date"].astype(str) + " " + hhmm)
    candidate = naive.dt.tz_localize(timezone)
    if globex_start is None:
        return candidate
    roll = pd.to_datetime(
        df["session_date"].astype(str) + " " + globex_start
    ).dt.tz_localize(timezone)
    return candidate.where(
        candidate < roll, candidate - pd.Timedelta(1, unit="D")
    )


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
    visible = _row_known_at(df["timestamp_et"]) >= available_at
    return mapped.where(visible)


def _opening_range(
    df: pd.DataFrame,
    start_hhmm: str,
    minutes: int,
    availability_hhmm: str | None,
    causal: bool,
) -> tuple[pd.Series, pd.Series]:
    start = _parse_hhmm(start_hhmm)
    end_total_minutes = start.hour * 60 + start.minute + minutes
    end = time(end_total_minutes // 60, end_total_minutes % 60)
    end_hhmm = f"{end.hour:02d}:{end.minute:02d}"

    t = df["timestamp_et"].dt.time
    mask = (t >= start) & (t < end)
    highs = _final_by_session(df, mask, "high", "max")
    lows = _final_by_session(df, mask, "low", "min")
    mapped_high = df["session_date"].map(highs)
    mapped_low = df["session_date"].map(lows)

    if causal:
        available_at = _availability_timestamp(df, availability_hhmm or end_hhmm)
        visible = _row_known_at(df["timestamp_et"]) >= available_at
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
    asia_start, asia_end = _window_config(config, "asia", "20:00", "00:00")
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
    result["is_asia"] = _time_mask(result["timestamp_et"], asia_start, asia_end)
    result["is_strategy_window"] = _time_mask(
        result["timestamp_et"],
        strategy_start,
        strategy_end,
    )
    result["new_entry_allowed"] = result["is_strategy_window"]

    # Current futures week high/low develop causally from the week start
    # (default Sunday 18:00 ET) through the configured week end (default
    # Friday 17:00 ET). Each futures week has its own running extrema; values
    # never carry across the week boundary, and bars in the weekend gap after
    # the Friday close (which no futures week contains) never update them.
    week_config = _week_config(config)
    week_start = _futures_week_start(result["timestamp_et"], week_config)
    week_end = _futures_week_end(week_start, week_config)
    in_futures_week = (result["timestamp_et"] >= week_start) & (
        result["timestamp_et"] < week_end
    )
    result["week_high"] = _running_extreme(
        result, in_futures_week, week_start, "high", "max"
    ).where(in_futures_week)
    result["week_low"] = _running_extreme(
        result, in_futures_week, week_start, "low", "min"
    ).where(in_futures_week)

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
    result["developing_ash"] = _running_extreme(
        result,
        result["is_asia"],
        result["session_date"],
        "high",
        "max",
    )
    result["developing_asl"] = _running_extreme(
        result,
        result["is_asia"],
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
    ash = _final_by_session(result, result["is_asia"], "high", "max")
    asl = _final_by_session(result, result["is_asia"], "low", "min")

    pm_availability_hhmm = _availability_hhmm(config, "pmh_pml", pm_end)
    on_availability_hhmm = _availability_hhmm(config, "onh_onl", on_end)
    london_availability_hhmm = _availability_hhmm(config, "loh_lol", london_end)
    asia_availability_hhmm = _availability_hhmm(config, "ash_asl", asia_end)

    result["pmh"] = _make_available(
        result,
        pmh,
        available_hhmm=pm_availability_hhmm,
        causal=causal,
    )
    result["pml"] = _make_available(
        result,
        pml,
        available_hhmm=pm_availability_hhmm,
        causal=causal,
    )
    result["onh"] = _make_available(
        result,
        onh,
        available_hhmm=on_availability_hhmm,
        causal=causal,
    )
    result["onl"] = _make_available(
        result,
        onl,
        available_hhmm=on_availability_hhmm,
        causal=causal,
    )
    result["loh"] = _make_available(
        result,
        loh,
        available_hhmm=london_availability_hhmm,
        causal=causal,
    )
    result["lol"] = _make_available(
        result,
        lol,
        available_hhmm=london_availability_hhmm,
        causal=causal,
    )
    result["ash"] = _make_available(
        result,
        ash,
        available_hhmm=asia_availability_hhmm,
        causal=causal,
    )
    result["asl"] = _make_available(
        result,
        asl,
        available_hhmm=asia_availability_hhmm,
        causal=causal,
    )

    # Previous-day levels use the completed prior RTH session only. Config
    # previous_day_levels.available_from (default: the Globex open, 18:00 ET)
    # declares when they become usable; availability times at or after the
    # Globex open are anchored to the session's own opening evening, so the
    # shipped default makes PD levels visible from the first bar of the
    # session that opens at that 18:00 ET.
    prev_levels_config = config.get("previous_day_levels", {}) or {}
    prev_levels_available_hhmm = str(
        prev_levels_config.get("available_from", globex_start)
    )
    rth_high = _final_by_session(result, result["is_rth"], "high", "max")
    rth_low = _final_by_session(result, result["is_rth"], "low", "min")
    rth_close = (
        result.loc[result["is_rth"]].groupby("session_date")["close"].last()
    )
    ordered_dates = sorted(set(result["session_date"]))
    prev_high: dict[Any, float] = {}
    prev_low: dict[Any, float] = {}
    prev_close: dict[Any, float] = {}
    for position, session in enumerate(ordered_dates):
        if position == 0:
            continue
        previous_session = ordered_dates[position - 1]
        if previous_session in rth_high.index:
            prev_high[session] = float(rth_high.loc[previous_session])
            prev_low[session] = float(rth_low.loc[previous_session])
            prev_close[session] = float(rth_close.loc[previous_session])
    result["pdh"] = result["session_date"].map(prev_high)
    result["pdl"] = result["session_date"].map(prev_low)
    result["pdc"] = result["session_date"].map(prev_close)
    if causal:
        pd_levels_available_at = _availability_timestamp(
            result,
            prev_levels_available_hhmm,
            globex_start=globex_start,
        )
        pd_levels_visible = _row_known_at(result["timestamp_et"]) >= pd_levels_available_at
        result["pdh"] = result["pdh"].where(pd_levels_visible)
        result["pdl"] = result["pdl"].where(pd_levels_visible)
        result["pdc"] = result["pdc"].where(pd_levels_visible)
    # Half-back is the prior RTH range midpoint: (PDH + PDL) / 2. It inherits
    # the PD-level availability mask through the masked PDH/PDL columns.
    result["half_back"] = (result["pdh"] + result["pdl"]) / 2.0

    rth_open = result.loc[result["is_rth"]].groupby("session_date")["open"].first()
    mapped_open = result["session_date"].map(rth_open)
    if causal:
        # Cash open is known only after the 09:30 bar completes at 09:31 ET
        # (config level_availability.rth_open).
        rth_open_availability_hhmm = _availability_hhmm(config, "rth_open", "09:31")
        available_at = _availability_timestamp(result, rth_open_availability_hhmm)
        mapped_open = mapped_open.where(
            _row_known_at(result["timestamp_et"]) >= available_at
        )
    result["rth_open"] = mapped_open

    opening_ranges = config.get("opening_ranges", {}) or {}
    opening_range_start = str(opening_ranges.get("start", "09:30"))
    opening_range_minutes = [
        int(value) for value in opening_ranges.get("durations_minutes", [5, 15, 30])
    ]
    opening_range_availability = opening_ranges.get("availability", {}) or {}
    for minutes in opening_range_minutes:
        configured_availability = opening_range_availability.get(f"or{minutes}")
        availability_hhmm = (
            str(configured_availability)
            if configured_availability is not None
            else None
        )
        high, low = _opening_range(
            result,
            start_hhmm=opening_range_start,
            minutes=minutes,
            availability_hhmm=availability_hhmm,
            causal=causal,
        )
        result[f"or{minutes}_high"] = high
        result[f"or{minutes}_low"] = low

    # Alias names used in various earlier notes (only for ranges that exist).
    for alias_name, source_column in (
        ("orh_5", "or5_high"),
        ("orl_5", "or5_low"),
        ("orh_15", "or15_high"),
        ("orl_15", "or15_low"),
        ("orh_30", "or30_high"),
        ("orl_30", "or30_low"),
    ):
        if source_column in result.columns:
            result[alias_name] = result[source_column]

    level_rows: list[dict[str, Any]] = []
    for session in ordered_dates:
        mask = result["session_date"] == session
        subset = result.loc[mask]

        def last_non_na(column: str):
            values = subset[column].dropna()
            return values.iloc[-1] if len(values) else np.nan

        row: dict[str, Any] = {
            "session_date": session,
            "pdh": last_non_na("pdh"),
            "pdl": last_non_na("pdl"),
            "pdc": last_non_na("pdc"),
            "half_back": last_non_na("half_back"),
            # Every finalized artifact field is derived from the enriched
            # availability-masked columns (last non-NaN of the session's
            # rows), never from the raw groupby series: a causal prefix that
            # ends before a level's availability instant must not publish the
            # unfinalized raw value in the artifact table.
            "pmh": last_non_na("pmh"),
            "pml": last_non_na("pml"),
            "onh": last_non_na("onh"),
            "onl": last_non_na("onl"),
            "loh": last_non_na("loh"),
            "lol": last_non_na("lol"),
            "ash": last_non_na("ash"),
            "asl": last_non_na("asl"),
            "rth_open": last_non_na("rth_open"),
        }
        for minutes in opening_range_minutes:
            row[f"or{minutes}_high"] = last_non_na(f"or{minutes}_high")
            row[f"or{minutes}_low"] = last_non_na(f"or{minutes}_low")
        level_rows.append(row)

    levels = pd.DataFrame(level_rows)
    return result, levels


@dataclass(frozen=True)
class SessionCoverage:
    """Coverage of one required session within the analyzed session date.

    ``covered`` is True only when every completed 1m slot the window should
    have produced by ``as_of`` is present: for an ongoing due window that is
    every expected minute through ``as_of`` (never beyond), and for a
    finalized window (as_of at/after the window end) it is the window's full
    wall-clock/DST-aware constituent minutes. A window that is not yet due
    (its start instant is after ``as_of``) is never ``covered`` -- it is
    reported missing presence-wise but must never drive a no-analysis
    outcome, because its bars were not expected to exist yet.

    ``due`` records whether the window had already started by ``as_of``.
    ``expected_count`` is the number of completed minutes the window should
    contain by ``as_of`` under the same rule.
    """

    session: str
    required: bool
    covered: bool
    bar_count: int
    first_et: pd.Timestamp | None
    last_et: pd.Timestamp | None
    due: bool
    expected_count: int = 0


@dataclass(frozen=True)
class SessionCoverageReport:
    """Result of checking required-session coverage for the morning engine.

    ``missing`` lists the required sessions that are not fully covered at
    ``as_of``: either their window had started but expected completed minutes
    are absent, or their window has not started yet. ``all_covered`` is True
    exactly when ``missing`` is empty.

    ``missing_due`` narrows ``missing`` to the sessions whose window had
    started by ``as_of`` (``due``): those are the missing expected minutes
    that make morning analysis unsafe. A window that is not yet due is
    distinguished from a missing expected bar, so early snapshots are never
    hard-failed for sessions that have not begun.
    """

    as_of: pd.Timestamp | None
    sessions: tuple[SessionCoverage, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(
            coverage.session
            for coverage in self.sessions
            if coverage.required and not coverage.covered
        )

    @property
    def all_covered(self) -> bool:
        return not self.missing

    @property
    def missing_due(self) -> tuple[str, ...]:
        return tuple(
            coverage.session
            for coverage in self.sessions
            if coverage.required and coverage.due and not coverage.covered
        )

    @property
    def all_due_covered(self) -> bool:
        return not self.missing_due

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat() if self.as_of is not None else None,
            "all_covered": self.all_covered,
            "all_due_covered": self.all_due_covered,
            "missing": list(self.missing),
            "missing_due": list(self.missing_due),
            "sessions": [
                {
                    "session": coverage.session,
                    "required": coverage.required,
                    "covered": coverage.covered,
                    "due": coverage.due,
                    "bar_count": coverage.bar_count,
                    "first_et": str(coverage.first_et) if coverage.first_et is not None else None,
                    "last_et": str(coverage.last_et) if coverage.last_et is not None else None,
                }
                for coverage in self.sessions
            ],
        }


def required_sessions(config: dict[str, Any]) -> list[str]:
    """Return the sessions the morning engine requires, from config.

    Reads ``validation.required_sessions`` and falls back to
    :data:`DEFAULT_REQUIRED_SESSIONS` when the config does not declare it. The
    config is authoritative: an unknown session name is a hard error so a typo
    cannot silently narrow the coverage check.
    """
    validation = config.get("validation", {}) or {}
    raw = validation.get("required_sessions")
    if raw is None:
        names = list(DEFAULT_REQUIRED_SESSIONS)
    elif isinstance(raw, str):
        names = [raw]
    else:
        names = [str(name) for name in raw if str(name).strip()]

    defined = config.get("sessions", {}) or {}
    unknown = [name for name in names if name not in defined]
    if unknown:
        raise SessionError(
            "validation.required_sessions names undefined sessions: "
            f"{sorted(unknown)}"
        )
    return names


def required_session_coverage(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    as_of: Any = None,
) -> SessionCoverageReport:
    """Check that the morning engine's required sessions are covered.

    Config-driven, ``as_of``-aware coverage check (Phase 2 validation V4) using
    the half-open ET session windows defined in config/sessions.yaml.

    - Only completed bars available at ``as_of`` are considered; when ``as_of``
      is omitted the caller must pass an already completed prefix (the data's
      last bar completion is then used as its effective as-of).
    - Coverage is evaluated for the most recent Globex session date present in
      that prefix (the session the morning engine is analyzing). A session is
      ``covered`` only when every completed 1m slot expected within its
      half-open ``[start, end)`` ET window is present: expected minutes run up
      to ``min(as_of, window end)``, so an ongoing due window requires full
      minute coverage only through ``as_of`` while a finalized window requires
      its full exact wall-clock/DST-aware constituent minutes. This is a
      completeness check, not a numeric quality threshold.
    - A required session is ``due`` when its window had already started by the
      effective as-of (its start instant, anchored to the analyzed session
      date, is not in the future). ``missing_due`` (required + due + not
      covered) is the set that must drive a no-analysis outcome; missing
      windows that are not yet due are distinguished and never hard-fail.
    """
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise SessionError(f"Missing required columns: {sorted(missing_columns)}")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise SessionError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise SessionError("'timestamp' must be timezone-aware.")

    normalized_as_of = normalize_as_of(as_of) if as_of is not None else None
    data = df.sort_values("timestamp").copy()
    if normalized_as_of is not None:
        data = filter_as_of(data, as_of=normalized_as_of)

    timezone = str(config.get("timezones", {}).get("trading", "America/New_York"))
    et = data["timestamp"].dt.tz_convert(timezone)

    globex_start, _globex_end = _window_config(config, "globex", "18:00", "17:00")
    globex_cutoff = _parse_hhmm(globex_start)
    session_dates = _session_date(et, globex_start)

    names = required_sessions(config)

    if data.empty:
        # No bar exists to anchor the analyzed session date: presence is all
        # four are missing, and nothing is due (no as-of reference).
        coverages = tuple(
            SessionCoverage(name, True, False, 0, None, None, False)
            for name in names
        )
        return SessionCoverageReport(normalized_as_of, coverages)

    if normalized_as_of is not None:
        effective_as_of = normalized_as_of
    else:
        # The caller passed an already completed prefix; its last bar is
        # knowable one minute after it opens.
        effective_as_of = pd.Timestamp(data["timestamp"].max()) + _MASTER_BAR_DURATION

    latest_session = max(session_dates.tolist())
    latest_mask = session_dates == latest_session
    latest_et = et.loc[latest_mask]
    as_of_et = effective_as_of.tz_convert(timezone)

    coverages: list[SessionCoverage] = []
    for name in names:
        start, end = _window_config(config, name, "", "")
        if start == "" or end == "":
            raise SessionError(f"Required session {name!r} has no start/end in config.")
        start_t = _parse_hhmm(start)
        end_t = _parse_hhmm(end)
        # Anchor the window to the analyzed session date, rolling at the Globex
        # clock: a window that opens at/after the roll time (18:00 ET, e.g.
        # overnight and Asia) begins on the prior calendar day of session
        # ``latest_session``; a window whose end time is at/before its start
        # (e.g. Asia ending 00:00 and overnight ending 09:30) wraps past
        # midnight and ends on the following calendar day.
        if start_t >= globex_cutoff:
            start_calendar = latest_session - timedelta(days=1)
        else:
            start_calendar = latest_session
        end_calendar = (
            start_calendar + timedelta(days=1) if end_t <= start_t else start_calendar
        )
        start_instant = pd.Timestamp(
            datetime.combine(start_calendar, start_t)
        ).tz_localize(timezone, nonexistent="shift_forward")
        end_instant = pd.Timestamp(
            datetime.combine(end_calendar, end_t)
        ).tz_localize(timezone, nonexistent="shift_forward")
        due = start_instant <= effective_as_of

        window_mask = _time_mask(latest_et, start, end)
        present = latest_et.loc[window_mask]
        count = int(present.size)
        first_et = present.iloc[0] if count else None
        last_et = present.iloc[-1] if count else None

        # Expected completed minutes: the whole-minute open instants G in
        # [start_instant, end_instant) whose bar has completed by as_of
        # (G + 1m <= as_of). date_range over the DST-aware zone skips the
        # nonexistent spring-forward minutes and emits both fall-back fold
        # legs, so the grid is exactly the window's real wall-clock minutes.
        # A window not yet started at as_of yields an empty expectation and
        # stays ``covered=False``/``due=False`` (never a hard failure).
        full_grid = pd.date_range(
            start_instant,
            end_instant - _MASTER_BAR_DURATION,
            freq="1min",
        )
        completed_expected = full_grid[
            full_grid + _MASTER_BAR_DURATION <= as_of_et
        ]
        expected_index = pd.Index(completed_expected)
        present_minutes = pd.Index(present).unique()
        missing_expected = expected_index.difference(present_minutes)
        covered = due and len(missing_expected) == 0
        coverages.append(
            SessionCoverage(
                name,
                True,
                covered,
                count,
                first_et,
                last_et,
                due,
                expected_count=len(completed_expected),
            )
        )

    return SessionCoverageReport(normalized_as_of, tuple(coverages))


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
