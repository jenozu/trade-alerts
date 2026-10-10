# Contract history inventory — 2026-10-10

Research selection is paused for data acceptance at the user's request. The
completed independent-contract 2023/2024/2025 feature builds remain preserved.
Contract isolation prevents inherited state; it does not establish sufficient
same-contract history or complete sessions. In particular, the corrected builder
splits its supplied stitched input and does not automatically load earlier bars
from the individual contract downloads. Existing downloads may therefore contain
needed history without requiring another vendor subscription.

## Ordered work

1. Inventory the exact corrected raw segments and individual contract files.
   Compare their overlap and report unused pre-segment history. Implemented by
   `scripts/audit_contract_history.py`; actual VPS inventory remains pending.
2. Classify coverage against the applicable exchange schedule and provider's
   no-trade bar behavior. Include complete session omissions, holidays, DST,
   maintenance breaks and relevant prior sessions. Observed timestamp gaps alone
   cannot classify missing data. Existing morning-session checks are useful but
   do not certify every historical source session.
3. Determine required feature context using the existing feature contracts.
   Distinguish insufficient warmup, missing downloads and available-but-unused
   history. Do not invent a universal warmup cutoff or trading eligibility rule.
4. Repair only proven affected sources/derivations into new artifacts, retaining
   old controls and provenance. Validate any alternate vendor against overlapping
   bars of the exact individual MNQ contract. No automatic feed mixing.
5. Reconcile corrected baseline evidence and affected prior research before
   resuming strategy selection. No repeated R5/R6/R7.0 or whole-year build merely
   because an inventory was requested.

## Inventory behavior

The command prints JSON to stdout only. It reads normalized `*_1m.parquet`
individual contract files and corrected `FEATURE_BUILD_SUMMARY.json` inputs.
It validates aware, ordered, minute-aligned timestamps, unique contract/time
keys, finite OHLCV and candle bounds. It checks each used raw segment's hash
against its existing `FEATURE_OUTPUT_LOCK.json`, records input hashes and checks
all inputs again after reading. Multiple download files are compared separately.
It reports exact overlapping value disagreements and timestamps present in the
download but absent inside the used segment span. No rounding or tolerance hides
a vendor/source discrepancy.

`INVENTORY_COMPLETE_COVERAGE_UNCERTIFIED` means the requested inventory ran; it
does not mean sufficient warmup, exchange completeness or research readiness.
Missing supplied directories, invalid files or raw-segment drift result in
`INVENTORY_INCOMPLETE` and exit code 1. No matching download means only that the
supplied directories lack it, not that a new download is required. Download date
ranges and gap counts are descriptive. Full feature-lock validation is separate.

## VPS step after publication

Use the existing verification checkout and its existing venv. Fetching and
extracting this one script does not update its checkout, run a pipeline, modify
data, or execute EXP-030. The outstanding EXP-030 request from the other
conversation is not changed or cancelled by this work; its results cannot close
this coverage gate.

```bash
cd /root/trade-alerts-verify-YwIqEc/repo
git fetch origin main
trade_inventory_dir=$(mktemp -d /root/trade-history-inventory-XXXXXX)
git show origin/main:scripts/audit_contract_history.py > "$trade_inventory_dir/audit_contract_history.py"
PYTHONPATH="$PWD/src" ../venv/bin/python "$trade_inventory_dir/audit_contract_history.py" \
  --build-summary /root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/features/FEATURE_BUILD_SUMMARY.json \
  --build-summary /root/trade-alerts-verify-YwIqEc/replays/isolated-2024-v_r21v9e/features/FEATURE_BUILD_SUMMARY.json \
  --build-summary /root/trade-alerts-verify-YwIqEc/replays/full-2025-isolated-features-20261005T185645Z/FEATURE_BUILD_SUMMARY.json \
  --contracts-dir /docker/trade-alerts/data/raw/barchart/contracts \
  --contracts-dir /docker/trade-alerts-2023/data/raw/barchart/contracts \
  --contracts-dir /docker/trade-alerts-2024/data/raw/barchart/contracts \
  > "$trade_inventory_dir/CONTRACT_HISTORY_INVENTORY.json" || trade_inventory_status=$?
cat "$trade_inventory_dir/CONTRACT_HISTORY_INVENTORY.json"
```

The individual contract directories are candidate locations, not confirmed
inventories. A missing-directory error is useful evidence for locating the
actual downloads; retain the partial report. This is a read-only file scan and
hash comparison, not another six-segment feature-generation job. Return its JSON
as text; do not rely on screenshots for dates/hashes. Actual source conclusions
and duration cannot be claimed until that report is reviewed.

## Local verification

New inventory regressions: 12 passed. Related inventory/build/session checks:
46 passed, 32 warnings. Full main-plus-inventory regression: **851 passed,
968 warnings in 26.03 seconds**. Warnings remain the existing NumPy timedelta,
pandas compatibility and feature-frame performance warnings. Test fixtures cover
unused history, overlapping price/volume conflicts, absent interior timestamps,
instrument mismatch, malformed candles/timestamps, missing directories, locked
raw-segment drift, preserved input bytes and CLI output. No VPS data was examined
by these synthetic tests and no historical feature build was repeated.

## Supplied VPS result — 2026-10-10

The full user-supplied report is archived at
`research-archive/EXP-INTEGRITY-HISTORY-INVENTORY/`, with verification findings
and an archive hash manifest. It returned zero errors, complete inventory,
unchanged inputs and uncertified coverage. Across the three directories, 57
files represent 19 distinct byte-identical datasets. Every used segment row
matches its download exactly and there are no unused download rows inside
used spans. This comparison cannot certify external completeness.

Seven incoming contracts have no earlier history in the inspected files:
NMM23, NMU23, NMZ23, NMM24, NMU24, NMZ24, NMU25. Six incoming contracts have
960 unused earlier Monday bars covering 01:00–16:59 ET, including the entire
configured RTH timestamp window: NMH23, NMH24, NMH25, NMM25, NMZ25, NMH26.
These bars can be considered for a separately versioned derivation; they have
not been inserted or recertified. Earlier initial-year NMZ context also exists.

The remaining inventory step is to locate original CSVs and normalized chunks,
including supplemental downloads absent from these contract files. Session
classification and feature-context sufficiency follow that source check.
No additional market-data subscription, fixed warmup cutoff or yearly rebuild
is prescribed by this result. Research selection remains paused.
