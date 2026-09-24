"""Validate and archive an existing R4.5 full-universe VPS run.

Never launches or repeats backtests. Refuses to archive partial results or a
baseline that does not reproduce the three frozen historical trade ledgers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd

MODELS = (
    "baseline",
    "candidate_conservative",
    "candidate_evidence_tilt",
    "candidate_redundancy_reduced",
)
YEARS = (2023, 2024, 2025)
BASELINE_COUNTS = {2023: 344, 2024: 388, 2025: 486}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/reports/R4-05_full-universe-candidates"
DEFAULT_ARCHIVE = ROOT / "research-archive/R4-05"
DEFAULT_LEDGERS = {
    2023: Path("/docker/trade-alerts-2023/data/results/backtest/trades.csv"),
    2024: Path("/docker/trade-alerts-2024/data/results/backtest/trades.csv"),
    2025: Path("/docker/trade-alerts/data/results/research_runs/2025_pipeline_final/backtest/trades.csv"),
}
FEATURES = {
    2023: Path("/docker/trade-alerts-2023/data/processed/scoring/nq_1m_scored.parquet"),
    2024: Path("/docker/trade-alerts-2024/data/processed/scoring/nq_1m_scored.parquet"),
    2025: Path("/docker/trade-alerts/data/cache/2025_warmup_92d/features_scored.parquet"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_trades(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"Required trade ledger missing: {path}")
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    return frame


def trade_fingerprint(frame: pd.DataFrame) -> Counter:
    needed = {"signal_time", "direction", "net_result_points"}
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError(f"Trade ledger missing fingerprint columns: {sorted(missing)}")
    ts = pd.to_datetime(frame["signal_time"], utc=True, errors="coerce")
    pts = pd.to_numeric(frame["net_result_points"], errors="coerce")
    direction = frame["direction"].astype(str).str.lower().str.strip()
    if ts.isna().any() or pts.isna().any():
        raise ValueError("Trade ledger has missing/invalid signal times or results")
    return Counter(zip(ts.astype(str), direction, pts.round(2)))


def audit(output: Path, ledgers: dict[int, Path]) -> dict:
    summary_path = output / "model_summary.csv"
    result_path = output / "r45_results.json"
    if not summary_path.is_file() or not result_path.is_file():
        raise ValueError("R4.5 summary/results missing: full run is not complete")

    summary = pd.read_csv(summary_path)
    if "model" not in summary or set(summary["model"]) != set(MODELS) or len(summary) != 4:
        raise ValueError("R4.5 summary must contain exactly the four candidate models")
    raw_results = json.loads(result_path.read_text(encoding="utf-8"))
    if set(raw_results.get("years", {})) != {str(y) for y in YEARS}:
        raise ValueError("R4.5 results JSON is missing a research year")
    if set(raw_results.get("aggregate", {})) != set(MODELS):
        raise ValueError("R4.5 results JSON is missing a candidate aggregate")

    report = {"years": {}, "baseline_reproduced": True}
    for year in YEARS:
        control = read_trades(ledgers[year])
        if len(control) != BASELINE_COUNTS[year]:
            raise ValueError(f"Frozen {year} baseline count changed: {len(control)}")
        report["years"][str(year)] = {}
        for model in MODELS:
            folder = output / str(year) / model
            trades = read_trades(folder / "trades.csv")
            metric_file = folder / "metrics.json"
            if not metric_file.is_file():
                raise ValueError(f"Missing {year}/{model} metrics.json")
            metric = json.loads(metric_file.read_text(encoding="utf-8"))
            if int(metric.get("trades", -1)) != len(trades):
                raise ValueError(f"Trade-count mismatch: {year}/{model}")
            if len(trades):
                net = pd.to_numeric(trades["net_result_points"], errors="coerce")
                if net.isna().any():
                    raise ValueError(f"Invalid net points: {year}/{model}")
                if "net_points" in metric and abs(float(net.sum()) - float(metric["net_points"])) > 0.02:
                    raise ValueError(f"Net-points mismatch: {year}/{model}")
            report["years"][str(year)][model] = {
                "trades": len(trades),
                "net_points": round(float(pd.to_numeric(trades["net_result_points"]).sum()), 2) if len(trades) else 0.0,
            }
            if model == "baseline":
                old, new = trade_fingerprint(control), trade_fingerprint(trades)
                if old != new:
                    missing = list((old - new).elements())[:3]
                    added = list((new - old).elements())[:3]
                    raise ValueError(
                        f"{year} baseline replay differs from frozen ledger: "
                        f"frozen={len(control)}, replay={len(trades)}; "
                        f"missing examples={missing}; extra examples={added}. "
                        "Do NOT rank candidates until config/code/data parity is investigated."
                    )
    for model in MODELS:
        combined = read_trades(output / f"{model}_all_years_trades.csv")
        total = sum(report["years"][str(year)][model]["trades"] for year in YEARS)
        aggregate = raw_results["aggregate"][model]
        summary_row = summary.loc[summary["model"] == model].iloc[0]
        if len(combined) != total or int(aggregate.get("trades", -1)) != total or int(summary_row.trades) != total:
            raise ValueError(f"Aggregate count mismatch: {model}")
        combined_net = round(float(pd.to_numeric(combined["net_result_points"]).sum()), 2) if len(combined) else 0.0
        yearly_net = sum(report["years"][str(year)][model]["net_points"] for year in YEARS)
        if abs(combined_net - yearly_net) > 0.02:
            raise ValueError(f"Aggregate net-points mismatch: {model}")
        report.setdefault("aggregate", {})[model] = {"trades": total, "net_points": combined_net}
    return report


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    p.add_argument("--log", type=Path, default=Path("/tmp/r45.log"))
    p.add_argument("--commit", action="store_true", help="Archive, commit, and push only after audit passes")
    args = p.parse_args(argv)

    if not args.log.is_file() or "R4.5 complete" not in args.log.read_text(errors="replace"):
        print("R4.5 has no confirmed full-run completion marker. Existing run was NOT restarted.")
        return 2
    try:
        result = audit(args.output, DEFAULT_LEDGERS)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"R4.5 NOT ARCHIVED: {exc}")
        return 3
    print("R4.5: all 12 model-year outputs verified; frozen baselines reproduced exactly.")
    print(json.dumps(result, indent=2))
    if not args.commit:
        return 0
    if git("branch", "--show-current") != "main":
        print("Refusing to commit: current branch is not main")
        return 4
    runner = ROOT / "scripts/run_r45_full_universe_candidates.py"
    if not runner.is_file():
        print("Refusing to archive: R4.5 runner is missing on this VPS")
        return 4
    if git("diff", "--cached", "--name-only"):
        print("Refusing to commit: existing unrelated staged changes detected")
        return 4
    if args.archive.exists():
        prior = {
            str(f.relative_to(args.archive)): sha256(f)
            for f in args.archive.rglob("*")
            if f.is_file() and f.name != "VERIFICATION_MANIFEST.json"
        }
        current = {
            str(f.relative_to(args.output)): sha256(f)
            for f in args.output.rglob("*") if f.is_file()
        }
        if prior != current:
            print("Existing local archive differs from verified run. Refusing overwrite.")
            return 4
        print("Existing local archive matches verified results; reusing it.")
    else:
        shutil.copytree(args.output, args.archive)
    manifest = {
        "research": "R4.5 full-universe candidate backtest",
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
        "verification": result,
        "source_features": {
            str(year): {"path": str(path), "bytes": path.stat().st_size}
            for year, path in FEATURES.items()
        },
        "source_ledger_sha256": {str(year): sha256(DEFAULT_LEDGERS[year]) for year in YEARS},
        "strategy_config_sha256": sha256(ROOT / "config/strategy.yaml"),
        "runner_sha256": sha256(runner),
        "artifact_sha256": {
            str(f.relative_to(args.archive)): sha256(f)
            for f in sorted(args.archive.rglob("*")) if f.is_file()
        },
        "feature_hash_note": "Full feature parquet hashes not calculated to avoid rereading large VPS archives; paths and sizes recorded.",
    }
    (args.archive / "VERIFICATION_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    git("add", "--", str(runner.relative_to(ROOT)), str(args.archive.relative_to(ROOT)))
    if git("diff", "--cached", "--name-only"):
        print(git("commit", "-m", "Archive verified R4.5 full-universe candidate backtests"))
    print(git("push", "origin", "main"))
    print("R4.5 ARCHIVED AND PUSHED:", git("rev-parse", "HEAD"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
