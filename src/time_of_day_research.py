"""EXP-020 — Time-of-day diagnostics using ledger signal_time."""

from __future__ import annotations

import pandas as pd

from directional_research import _metrics, validate_ledger
from setup_family_research import derive_setup_family


class TimeOfDayResearchError(RuntimeError):
    pass


def segment(df, col):
    s = df[col].where(df[col].notna(), "<missing>").astype(str)

    return {
        value: _metrics(df.loc[s == value])
        for value in s.drop_duplicates().tolist()
    }


def five_minute_bucket(ts):
    if pd.isna(ts):
        return "unknown"

    minute = ts.hour * 60 + ts.minute

    if minute < 570:
        return "pre-09:30"
    if minute <= 574:
        return "09:30-09:34"
    if minute <= 579:
        return "09:35-09:39"
    if minute <= 584:
        return "09:40-09:44"
    if minute <= 589:
        return "09:45-09:49"
    if minute <= 594:
        return "09:50-09:54"
    if minute <= 599:
        return "09:55-09:59"
    if minute <= 604:
        return "10:00-10:04"
    if minute <= 609:
        return "10:05-10:09"
    if minute <= 614:
        return "10:10-10:14"
    if minute <= 619:
        return "10:15-10:19"
    if minute <= 624:
        return "10:20-10:24"
    if minute <= 629:
        return "10:25-10:29"

    return "10:30+"


def broad_bucket(ts):
    if pd.isna(ts):
        return "unknown"

    minute = ts.hour * 60 + ts.minute

    if minute < 570:
        return "pre-09:30"
    if minute <= 574:
        return "09:30-09:34"
    if minute <= 584:
        return "09:35-09:44"
    if minute <= 599:
        return "09:45-09:59"
    if minute <= 614:
        return "10:00-10:14"
    if minute <= 629:
        return "10:15-10:29"

    return "10:30+"


def enrich(ledger):
    validate_ledger(ledger)

    out = ledger.copy()

    signal_utc = pd.to_datetime(
        out["signal_time"],
        utc=True,
        errors="coerce",
    )

    signal_et = signal_utc.dt.tz_convert(
        "America/New_York"
    )

    out["signal_time_et"] = signal_et
    out["signal_clock_et"] = signal_et.dt.strftime("%H:%M")
    out["signal_hour_et"] = signal_et.dt.hour
    out["signal_minute_et"] = signal_et.dt.minute

    out["time_bucket_5m"] = signal_et.map(
        five_minute_bucket
    )

    out["time_bucket_broad"] = signal_et.map(
        broad_bucket
    )

    out["direction"] = (
        out["direction"]
        .astype(str)
        .str.lower()
    )

    out["setup_family"] = derive_setup_family(out)

    if "raw_score" in out.columns:
        score = pd.to_numeric(
            out["raw_score"],
            errors="coerce",
        )

        out["score_band_exp020"] = pd.cut(
            score,
            bins=[
                -float("inf"),
                79.999,
                89.999,
                float("inf"),
            ],
            labels=[
                "70-79_or_lower",
                "80-89",
                "90+",
            ],
        ).astype(str)

    else:
        out["score_band_exp020"] = "unknown"

    return out


def analyze(frames):
    if set(frames) != {2023, 2024, 2025}:
        raise TimeOfDayResearchError(
            "EXP-020 requires 2023/2024/2025"
        )

    joined = []

    for year, frame in sorted(frames.items()):
        x = frame.copy()
        x["year"] = year
        joined.append(x)

    df = pd.concat(joined, ignore_index=True)

    result = {
        "experiment_id": "EXP-020_time-of-day",

        "coverage": {
            "total": int(len(df)),
            "valid_signal_time": int(
                df["signal_time_et"].notna().sum()
            ),
        },

        "five_minute": segment(
            df,
            "time_bucket_5m",
        ),

        "broad_time": segment(
            df,
            "time_bucket_broad",
        ),

        "exact_clock": segment(
            df,
            "signal_clock_et",
        ),

        "by_year": {},
        "by_direction": {},
        "by_family": {},
        "by_score_band": {},
    }

    for year in sorted(df["year"].unique()):
        g = df[df["year"] == year]

        result["by_year"][str(year)] = {
            "five_minute": segment(
                g,
                "time_bucket_5m",
            ),
            "broad_time": segment(
                g,
                "time_bucket_broad",
            ),
        }

    for direction in ("long", "short"):
        g = df[df["direction"] == direction]

        result["by_direction"][direction] = {
            "five_minute": segment(
                g,
                "time_bucket_5m",
            ),
            "broad_time": segment(
                g,
                "time_bucket_broad",
            ),
        }

    for family in ("reversal", "continuation"):
        g = df[df["setup_family"] == family]

        result["by_family"][family] = {
            "five_minute": segment(
                g,
                "time_bucket_5m",
            ),
            "broad_time": segment(
                g,
                "time_bucket_broad",
            ),
        }

    for band in df["score_band_exp020"].dropna().unique():
        g = df[
            df["score_band_exp020"] == band
        ]

        result["by_score_band"][str(band)] = {
            "broad_time": segment(
                g,
                "time_bucket_broad",
            ),
        }

    return result, df


def metrics_frame(result):
    rows = []

    def add(section, values):
        for value, metrics in values.items():
            if (
                isinstance(metrics, dict)
                and "trades" in metrics
            ):
                rows.append({
                    "section": section,
                    "value": value,
                    **metrics,
                })

    add("five_minute", result["five_minute"])
    add("broad_time", result["broad_time"])
    add("exact_clock", result["exact_clock"])

    for year, sections in result["by_year"].items():
        for section, values in sections.items():
            add(
                f"year_{year}_{section}",
                values,
            )

    for direction, sections in result["by_direction"].items():
        for section, values in sections.items():
            add(
                f"direction_{direction}_{section}",
                values,
            )

    for family, sections in result["by_family"].items():
        for section, values in sections.items():
            add(
                f"family_{family}_{section}",
                values,
            )

    for band, sections in result["by_score_band"].items():
        for section, values in sections.items():
            add(
                f"score_{band}_{section}",
                values,
            )

    return pd.DataFrame(rows)


def markdown_report(result):
    def num(v, digits=2):
        if v is None:
            return "—"

        try:
            return f"{float(v):.{digits}f}"
        except Exception:
            return "—"

    def pct(v):
        if v is None:
            return "—"

        return f"{100 * float(v):.1f}%"

    def table(values):
        lines = [
            "| Time | Trades | Win | Exp pts | Exp R | PF | Net pts | TP1 | TP2 | TP3 | TP4 | Stop | Avg MFE | Avg MAE |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]

        for label, m in values.items():
            lines.append(
                f"| {label} | "
                f"{m.get('trades',0)} | "
                f"{pct(m.get('win_rate'))} | "
                f"{num(m.get('expectancy_points'))} | "
                f"{num(m.get('expectancy_r'),3)} | "
                f"{num(m.get('profit_factor'))} | "
                f"{num(m.get('net_points'))} | "
                f"{pct(m.get('tp1_hit_rate'))} | "
                f"{pct(m.get('tp2_hit_rate'))} | "
                f"{pct(m.get('tp3_hit_rate'))} | "
                f"{pct(m.get('tp4_hit_rate'))} | "
                f"{pct(m.get('stop_rate'))} | "
                f"{num(m.get('avg_mfe'))} | "
                f"{num(m.get('avg_mae'))} |"
            )

        return "\n".join(lines)

    lines = [
        "# EXP-020 — Time of Day",
        "",
        "Diagnostic only.",
        "",
        "## Timestamp semantics",
        "",
        "- `signal_time` is parsed as UTC and converted to `America/New_York` before time bucketing.",
        "- `session_date` is not used for intraday timing.",
        "",
        "## Coverage",
        "",
        f"- Valid signal times: "
        f"{result['coverage']['valid_signal_time']} / "
        f"{result['coverage']['total']}",
        "",
        "## Five-minute buckets",
        "",
        table(result["five_minute"]),
        "",
        "## Broad buckets",
        "",
        table(result["broad_time"]),
        "",
        "## Year stability",
        "",
    ]

    for year, sections in result["by_year"].items():
        lines += [
            f"### {year}",
            "",
            table(sections["broad_time"]),
            "",
        ]

    lines += [
        "## Direction",
        "",
    ]

    for direction, sections in result["by_direction"].items():
        lines += [
            f"### {direction}",
            "",
            table(sections["broad_time"]),
            "",
        ]

    lines += [
        "## Setup family",
        "",
    ]

    for family, sections in result["by_family"].items():
        lines += [
            f"### {family}",
            "",
            table(sections["broad_time"]),
            "",
        ]

    lines += [
        "## Score-band interaction",
        "",
    ]

    for band, sections in result["by_score_band"].items():
        lines += [
            f"### {band}",
            "",
            table(sections["broad_time"]),
            "",
        ]

    lines += [
        "## Limitations",
        "",
        "- Existing baseline trades only.",
        "- Time-of-day effects may overlap opening volatility, setup family, direction, score band, and year.",
        "- Small five-minute cells are exploratory.",
        "- EXP-020 does not change the production trading window.",
        "",
        "## Decision",
        "",
        "**Diagnostic only — no strategy change.**",
    ]

    return "\n".join(lines)
