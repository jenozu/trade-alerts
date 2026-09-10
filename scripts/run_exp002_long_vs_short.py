"""Run EXP-002 from archived trade ledgers without rerunning the pipeline."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT/"src"))
from directional_research import analyze_long_vs_short, flatten_tables, markdown_report

def parse_ledger(value:str):
    try:
        y,p=value.split("=",1); return int(y),Path(p)
    except ValueError as exc: raise argparse.ArgumentTypeError("Ledger must be YEAR=/path/to/trades.csv") from exc

def main():
    ap=argparse.ArgumentParser(description="EXP-002 ledger-only long-vs-short diagnostic")
    ap.add_argument("--ledger",action="append",required=True,type=parse_ledger,metavar="YEAR=PATH")
    ap.add_argument("--output-dir",default=str(PROJECT_ROOT/"data"/"reports"/"EXP-002_long-vs-short"))
    a=ap.parse_args(); ledgers=dict(a.ledger)
    if set(ledgers)!={2023,2024,2025}: ap.error("EXP-002 control set must contain exactly 2023, 2024, and 2025 ledgers.")
    missing=[str(p) for p in ledgers.values() if not p.exists()]
    if missing: ap.error("Ledger not found: "+", ".join(missing))
    result=analyze_long_vs_short({y:pd.read_csv(p) for y,p in ledgers.items()})
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    (out/"exp002_long_vs_short_results.json").write_text(json.dumps(result,indent=2,allow_nan=True),encoding="utf-8")
    (out/"EXP-002_long-vs-short.md").write_text(markdown_report(result,{y:str(p) for y,p in ledgers.items()}),encoding="utf-8")
    for name,table in flatten_tables(result).items(): table.to_csv(out/f"{name}.csv",index=False)
    print(f"EXP-002 complete: {out/'EXP-002_long-vs-short.md'}")
if __name__=="__main__": main()
