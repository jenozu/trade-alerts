# 2023 corrected diagnostic evidence

## Scope and evidence boundary

This records user-supplied VPS terminal evidence reviewed October 8–9, 2026.
The underlying large market-data files remain on the VPS. Local screenshot
review is not a second direct examination of those Parquet files. Original
raw data, scored controls and research archives were preserved.

Task root: `/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw`.
Feature, chronology and execution outputs use separate sibling directories.
The producing review checkout was `14e0349823c1ae7df6d71f40eb634424399d27b2`;
sequence contract was `fvg_chronology_v2`, execution contract
`market_after_retest_confirmation_v2`. No year or threshold search was performed.

Feature coverage: 440,032 source bars, 352,178 UTC-2023 bars, six isolated contract
segments. Both feature locks were independently verified; segment checks and
original-source preservation passed. Chronology derivation completed unchanged;
execution completed with both execution locks verified.

## Recorded decisions

All seven signals are reversals. Entry times are one minute after the signal.
Prices shown include the audit's adverse entry slippage. Dates/times below are UTC.

| Signal | Contract | Direction | Entry price | Oversized structural risk | First obstacle source | Distance points |
| --- | --- | --- | ---: | --- | --- | ---: |
| 2023-02-28 14:42 | NMH23 | long | 12086.25 | 47.00 > 25 | nearest_equal_high | 0.25 |
| 2023-06-23 14:02 | NMU23 | short | 15018.50 | No oversized-risk rejection | nearest_equal_low | 0.25 |
| 2023-10-02 13:48 | NMZ23 | short | 14933.25 | 29.75 > 25 | confluence_zone | 3.0833333333 |
| 2023-10-11 14:24 | NMZ23 | long | 15328.75 | No oversized-risk rejection | nearest_equal_high | 1.75 |
| 2023-10-19 13:32 | NMZ23 | long | 15107.50 | 30.25 > 25 | nearest_equal_high | 1.00 |
| 2023-11-30 15:05 | NMZ23 | short | 15943.25 | 47.75 > 25 | week_low | 24.50 |
| 2023-12-21 15:15 | NMH24 | long | 16888.75 | 47.25 > 25 | nearest_equal_high | 0.75 |

Every signal failed the minimum 25-point room-to-first-obstacle check. February
28, June 23, October 2, October 11, October 19 and December 21 also failed TP1
asymmetry (respectively 0.01, 0.01, 0.26, 0.08, 0.03 and 0.02 < 1).
November 30 additionally failed primary-DOL room (24.50 < 25) and had no TP1
market objective before that DOL. December 21 also failed primary-DOL asymmetry
(0.85 < 1). These are the current planner's recorded reasons, not independent
certification of level significance.

The read-only obstacle diagnostic reproduced all seven nearest distances.
None of these first objectives was marked an HTF obstacle. Five were categorized
as internal liquidity; October 2 was a confluence zone, November 30 external
weekly liquidity. Internal liquidity is therefore being used as a hard room
constraint, rather than merely reported as an intermediate draw.

## Settings and conclusions

The saved audit summary shows completed-bar decisions, next-open entry,
stop-first same-bar resolution, one position, a 60-minute maximum hold,
0.25-point entry and exit slippage, point value 2, quantity 1 and disabled
commission. This preserves frozen diagnostic settings; it does not certify
actual fees or a ten-contract live configuration. Fixed-distance TP settings
listed in the effective settings do not demonstrate that v2 executed fixed
targets: no trade executed and v2 uses its shared planner target contract.

Result: seven eligible signals, zero accepted plans/trades, zero executed-plan
parity comparisons. Do not claim a win rate, profitability or positive historical
execution proof from this result. Do not relax constraints merely to create trades.

The newly published main document `docs/context_bias_confirmation_principles.md`
distinguishes liquidity targets/draws from potential reaction/reversal zones.
It explicitly remains a design principle, not proof of current implementation.
It does not settle which internal pools should block entries or become TP1.
An exact policy must be defined before an alternative execution contract is
implemented. The old contracts and these diagnostics must remain reproducible.

No tests/builds need repeating for this documentation update. The latest code
suite remains 786 passed with 872 warnings. R7 strategy-selection remains paused
pending the remaining fidelity, costs and baseline gates.

## Authoritative execution evidence archived — 2026-10-09

The supplied terminal export has been decoded and preserved under
`research-archive/EXP-INTEGRITY-2023-DIAGNOSTIC/`. Both lock identity digests
verify, all three exported outputs match their recorded SHA-256 hashes and sizes,
68 producer code-file hashes match the integrity checkout, and segment counts
and all seven rejection decisions reconcile with the summary. The archive
manifest verifies all seven copied files. VPS-only source paths have not been
reopened locally; this verification does not claim historical accepted-path
parity, realistic fees or research readiness. No completed pipeline was rerun.

2024 and 2025 authoritative execution exports were subsequently verified and
archived under matching EXP-INTEGRITY-2024-DIAGNOSTIC and
EXP-INTEGRITY-2025-DIAGNOSTIC directories.
