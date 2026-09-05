from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timezone
from pathlib import Path

import pandas as pd

CHICAGO_TZ = "America/Chicago"
SESSION_OPEN_LOCAL = time(17, 0)


class RolloverAnalysisError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze adjacent Barchart MNQ contracts and recommend deterministic rollover boundaries from daily volume crossover.")
    p.add_argument("--contracts-dir", type=Path, default=Path("data/raw/barchart/contracts"))
    p.add_argument("--output", type=Path, default=Path("data/raw/barchart/rollover_analysis.json"))
    p.add_argument("--confirmation-days", type=int, default=2)
    return p.parse_args()


def contract_sort_key(name: str) -> tuple[int, int]:
    name = name.upper().replace("_1M.PARQUET", "")
    if len(name) < 5:
        raise RolloverAnalysisError(f"Unrecognized contract name: {name}")
    month_code = name[-3]
    year = int(name[-2:])
    month_order = {"H": 3, "M": 6, "U": 9, "Z": 12}
    if month_code not in month_order:
        raise RolloverAnalysisError(f"Unsupported MNQ month code in {name}")
    return (2000 + year, month_order[month_code])


def trading_date(ts: pd.Series) -> pd.Series:
    local = ts.dt.tz_convert(CHICAGO_TZ)
    dates = pd.Series(local.dt.date, index=ts.index, dtype="object")
    return dates.where(local.dt.time < SESSION_OPEN_LOCAL, dates + pd.to_timedelta(1, unit="D"))


def load_contract(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    needed = {"timestamp", "volume", "contract"}
    missing = needed - set(df.columns)
    if missing:
        raise RolloverAnalysisError(f"{path.name}: missing {sorted(missing)}")
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="raise")
    df["volume"] = pd.to_numeric(df["volume"], errors="raise")
    if (df["volume"] < 0).any():
        raise RolloverAnalysisError(f"{path.name}: negative volume")
    df["trading_date"] = trading_date(df["timestamp"])
    return df


def daily_volume(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("trading_date", as_index=False)["volume"].sum()
    return out.rename(columns={"volume": "daily_volume"})


def analyze_pair(old: pd.DataFrame, new: pd.DataFrame, old_name: str, new_name: str, confirmation_days: int) -> dict:
    if confirmation_days < 1:
        raise RolloverAnalysisError("confirmation-days must be >= 1")
    a = daily_volume(old).rename(columns={"daily_volume": "old_volume"})
    b = daily_volume(new).rename(columns={"daily_volume": "new_volume"})
    x = a.merge(b, on="trading_date", how="inner").sort_values("trading_date").reset_index(drop=True)
    if x.empty:
        raise RolloverAnalysisError(f"{old_name}->{new_name}: no overlapping trading dates")
    x["new_gt_old"] = x["new_volume"] > x["old_volume"]

    chosen_idx = None
    flags = x["new_gt_old"].tolist()
    for i in range(0, len(flags) - confirmation_days + 1):
        if all(flags[i:i + confirmation_days]):
            chosen_idx = i
            break

    method = "confirmed_volume_crossover"
    if chosen_idx is None:
        candidates = x.index[x["new_gt_old"]].tolist()
        if not candidates:
            raise RolloverAnalysisError(f"{old_name}->{new_name}: new contract never exceeds old contract volume in overlap")
        chosen_idx = candidates[0]
        method = "first_volume_crossover_unconfirmed"

    chosen_date = pd.Timestamp(x.loc[chosen_idx, "trading_date"])
    session_open_local = pd.Timestamp.combine(chosen_date.date() - pd.Timedelta(days=1), SESSION_OPEN_LOCAL).tz_localize(CHICAGO_TZ)
    rollover_utc = session_open_local.tz_convert("UTC")

    rows = []
    for _, r in x.iterrows():
        rows.append({
            "trading_date": str(r["trading_date"]),
            "old_volume": float(r["old_volume"]),
            "new_volume": float(r["new_volume"]),
            "new_gt_old": bool(r["new_gt_old"]),
        })

    return {
        "from_contract": old_name,
        "to_contract": new_name,
        "method": method,
        "confirmation_days_required": confirmation_days,
        "selected_trading_date": str(chosen_date.date()),
        "rollover_timestamp_utc": rollover_utc.isoformat(),
        "overlap_trading_days": len(x),
        "daily_volume_comparison": rows,
    }


def main() -> None:
    args = parse_args()
    files = sorted(args.contracts_dir.glob("NM*_1m.parquet"), key=lambda p: contract_sort_key(p.name))
    if len(files) < 2:
        raise RolloverAnalysisError(f"Need at least two contract Parquets in {args.contracts_dir}")

    contracts = [p.stem.replace("_1m", "") for p in files]
    frames = [load_contract(p) for p in files]
    analyses = []
    failures = []

    print("\n" + "=" * 80)
    print("BARCHART MNQ ROLLOVER ANALYSIS")
    print("=" * 80)
    print(f"Contracts: {len(files)}")
    print(f"Confirmation days: {args.confirmation_days}")

    for i in range(len(files) - 1):
        old_name, new_name = contracts[i], contracts[i + 1]
        print(f"\n[{i+1}/{len(files)-1}] {old_name} -> {new_name}")
        try:
            result = analyze_pair(frames[i], frames[i + 1], old_name, new_name, args.confirmation_days)
            analyses.append(result)
            print(f"  selected trading date: {result['selected_trading_date']}")
            print(f"  rollover UTC: {result['rollover_timestamp_utc']}")
            print(f"  method: {result['method']}")
            print(f"  overlap days: {result['overlap_trading_days']}")
        except Exception as exc:
            failures.append({"from_contract": old_name, "to_contract": new_name, "error": repr(exc)})
            print(f"  ERROR: {exc!r}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "BARCHART",
        "symbol": "MNQ",
        "rule": "roll at CME session open preceding first trading date where new-contract daily volume exceeds old-contract daily volume for N consecutive overlapping trading dates; fallback is flagged unconfirmed first crossover",
        "confirmation_days": args.confirmation_days,
        "contracts_in_order": contracts,
        "rollovers_expected": len(files) - 1,
        "rollovers_succeeded": len(analyses),
        "rollovers_failed": len(failures),
        "rollovers": analyses,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("ROLLOVER ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Succeeded: {len(analyses)} / {len(files)-1}")
    print(f"Failed:    {len(failures)}")
    print(f"Audit:     {args.output}")
    if failures:
        print("\nROLLOVER ANALYSIS INCOMPLETE — DO NOT STITCH YET")
        raise SystemExit(1)
    print("\nROLLOVER ANALYSIS PASSED")
    print("Review any unconfirmed crossover methods before stitching.")


if __name__ == "__main__":
    main()
