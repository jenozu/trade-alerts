# trade-alerts Phase Truth Audit

This report is read-only. It compares phases.md claims with mechanical repository evidence. It does not automatically treat file existence as proof that strategy behavior is correct.

## Repository state

- Branch: `main`
- Local HEAD: `ad3463b52db056e53bf1f9dcfbd77ed0917d5aee`
- origin/main: `ad3463b52db056e53bf1f9dcfbd77ed0917d5aee`
- HEAD matches origin/main: **True**
- Working tree clean: **True**
- Local phases.md matches origin/main: **True**
- Local phases.md SHA256: `3ab7bd2a538d7162e3c068cd7abf119fcdd15294a9b8daf92db99ccddd0a2b9e`
- Remote phases.md SHA256: `3ab7bd2a538d7162e3c068cd7abf119fcdd15294a9b8daf92db99ccddd0a2b9e`

## Test state

- Full-suite result: `418 passed, 226 warnings in 6.52s`

## Checklist progress by phase

| Scope | Checked | Open | Total | Roadmap % |
|---|---:|---:|---:|---:|
| Global rules — apply to every phase | 26 | 13 | 39 | 66.7% |
| Current status snapshot | 10 | 0 | 10 | 100.0% |
| Phase 0 — Baseline / Repository Audit | 24 | 0 | 24 | 100.0% |
| Phase 1 — ProjectX Collector | 39 | 0 | 39 | 100.0% |
| Phase 2 — Data Clock, Validation, Resampling, Sessions | 66 | 0 | 66 | 100.0% |
| Phase 3 — Objective Market Features | 162 | 1 | 163 | 99.4% |
| Phase 4 — Production Displacement + Draw on Liquidity | 6 | 34 | 40 | 15.0% |
| Phase 5 — Market State Engine | 0 | 54 | 54 | 0.0% |
| Phase 6 — Trade Planner | 0 | 66 | 66 | 0.0% |
| Phase 7 — Morning Output / Report | 0 | 40 | 40 | 0.0% |
| Phase 8 — 09:25 Premarket Refresh | 0 | 21 | 21 | 0.0% |
| Phase 9 — Live Setup State Machines | 0 | 48 | 48 | 0.0% |
| Phase 10 — VPS Orchestration, Health, Logging, Scheduling | 0 | 35 | 35 | 0.0% |
| Phase 11 — Shadow Mode | 0 | 27 | 27 | 0.0% |
| Phase 12 — Formal Backtesting / Calibration | 8 | 113 | 121 | 6.6% |

## Unchecked items that already have implementation evidence (likely stale-roadmap candidates)

- **L45 — Global rules — apply to every phase / No lookahead:** Maintain one explicit as_of contract throughout the production pipeline.
  - Evidence: `run_pipeline.py`, `src/data_clock.py`, `tests/test_pipeline_as_of.py`, `tests/test_replay_parity.py`
- **L71 — Global rules — apply to every phase / Important naming decision:** Build support/resistance confluence separately, e.g. src/confluence_zones.py or src/support_resistance.py.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L72 — Global rules — apply to every phase / Important naming decision:** Expose signal-to-noise and support/resistance as separate concepts in market state.
  - Evidence: `src/confluence_zones.py`, `src/snr.py`, `tests/test_confluence_zones.py`, `tests/test_snr.py`, `tests/test_snr_production.py`
- **L78 — Global rules — apply to every phase / Scoring:** Do not call the score a win probability until empirically calibrated.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L83 — Global rules — apply to every phase / Git / multi-conversation workflow:** Start every coding session with:
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `tests/test_sessions.py`
- **L566 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate external swings.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L567 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate important untested HTF FVGs when safely represented.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L568 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider HTF structure/bias.
  - Evidence: `src/bias.py`, `src/structure.py`, `tests/test_bias.py`, `tests/test_structure.py`
- **L570 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider protected/weak swings.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L573 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider displacement.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L576 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Preserve component scores/reasons.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L585 — Phase 4 — Production Displacement + Draw on Liquidity / Sweep vs break classification:** Require displacement for valid structural break.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L590 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** Sweep vs displacement break is reliable.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L609 — Phase 5 — Market State Engine / Core module:** Include generated_at and mandatory as_of.
  - Evidence: `run_pipeline.py`, `src/data_clock.py`, `tests/test_pipeline_as_of.py`, `tests/test_replay_parity.py`
- **L611 — Phase 5 — Market State Engine / Core module:** Include data-quality/freshness/session-coverage state.
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `tests/test_sessions.py`
- **L612 — Phase 5 — Market State Engine / Core module:** Include sessions/key levels/VWAP/timeframe summaries.
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `src/vwap.py`, `tests/test_sessions.py`, `tests/test_vwap.py`
- **L613 — Phase 5 — Market State Engine / Core module:** Include HTF/daily and intraday bias.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L614 — Phase 5 — Market State Engine / Core module:** Include swings/liquidity/dealing ranges/premium-discount.
  - Evidence: `src/dealing_range.py`, `src/liquidity.py`, `src/swings.py`, `tests/test_dealing_range.py`, `tests/test_swings.py`
- **L615 — Phase 5 — Market State Engine / Core module:** Include PD arrays.
  - Evidence: `src/pd_arrays.py`, `tests/test_pd_arrays.py`
- **L616 — Phase 5 — Market State Engine / Core module:** Include FVG/IFVG.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L617 — Phase 5 — Market State Engine / Core module:** Include structure/displacement.
  - Evidence: `src/displacement.py`, `src/structure.py`, `tests/test_displacement.py`, `tests/test_structure.py`
- **L618 — Phase 5 — Market State Engine / Core module:** Include volume/RVOL.
  - Evidence: `src/volume.py`, `tests/test_volume.py`
- **L619 — Phase 5 — Market State Engine / Core module:** Include signal-to-noise.
  - Evidence: `src/snr.py`, `tests/test_snr.py`, `tests/test_snr_production.py`
- **L620 — Phase 5 — Market State Engine / Core module:** Include support/resistance confluence zones.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L622 — Phase 5 — Market State Engine / Core module:** Include scores/components.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L636 — Phase 5 — Market State Engine / Required levels:** VWAP.
  - Evidence: `src/vwap.py`, `tests/test_vwap.py`
- **L637 — Phase 5 — Market State Engine / Required levels:** Nearest important swing high/low.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L639 — Phase 5 — Market State Engine / Required levels:** Important HTF FVG above/below.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L640 — Phase 5 — Market State Engine / Required levels:** Important 5m FVG above/below.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L641 — Phase 5 — Market State Engine / Required levels:** Important support/resistance zone.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L655 — Phase 5 — Market State Engine / Safe failure states:** NO ANALYSIS — PROJECTX DATA UNAVAILABLE.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`
- **L664 — Phase 5 — Market State Engine / Tests:** as_of test.
  - Evidence: `run_pipeline.py`, `src/data_clock.py`, `tests/test_pipeline_as_of.py`, `tests/test_replay_parity.py`
- **L708 — Phase 6 — Trade Planner / Each candidate must include:** Raw/component scores.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L709 — Phase 6 — Trade Planner / Each candidate must include:** DOL/bias alignment.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L713 — Phase 6 — Trade Planner / Reversal planner:** Important liquidity.
  - Evidence: `src/liquidity.py`
- **L716 — Phase 6 — Trade Planner / Reversal planner:** Opposite displacement.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L725 — Phase 6 — Trade Planner / Continuation planner:** Displacement break.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L729 — Phase 6 — Trade Planner / Continuation planner:** Level/FVG hold.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L735 — Phase 6 — Trade Planner / Stop logic:** Find protected/invalidation structure.
  - Evidence: `src/structure.py`, `tests/test_structure.py`
- **L738 — Phase 6 — Trade Planner / Stop logic:** Prefer ~20–25 NQ points only when structure permits.
  - Evidence: `src/structure.py`, `tests/test_structure.py`
- **L747 — Phase 6 — Trade Planner / Target logic:** TP4 from external-liquidity runner when room exists.
  - Evidence: `src/liquidity.py`
- **L788 — Phase 7 — Morning Output / Report / Deterministic outputs:** Structured morning alert JSON.
  - Evidence: `src/structure.py`, `tests/test_structure.py`
- **L797 — Phase 7 — Morning Output / Report / Required sections:** Bias — HTF/daily + intraday + confidence/reasons.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L800 — Phase 7 — Morning Output / Report / Required sections:** Key Liquidity & Structure Levels above/below price.
  - Evidence: `src/liquidity.py`, `src/structure.py`, `tests/test_structure.py`
- **L814 — Phase 7 — Morning Output / Report / Chart markup:** Important bullish/bearish FVG.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L854 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Pull fresh ProjectX bars.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`
- **L857 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Rebuild market state with 09:25 as_of.
  - Evidence: `run_pipeline.py`, `src/data_clock.py`, `tests/test_pipeline_as_of.py`, `tests/test_replay_parity.py`
- **L859 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Recalculate PMH/PML, overnight, London, sweeps, displacement, structure, FVG/IFVG, DOL, bias, scores, planner candidates.
  - Evidence: `src/bias.py`, `src/displacement.py`, `src/fvg.py`, `src/fvg_state.py`, `src/scorer.py`, `src/scorer_harmonization.py`, `src/structure.py`, `tests/test_bias.py`, `tests/test_displacement.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`, `tests/test_scorer.py`, `tests/test_structure.py`
- **L865 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Explain level/sweep/structure/DOL/bias/entry/invalidation/target changes.
  - Evidence: `src/bias.py`, `src/structure.py`, `tests/test_bias.py`, `tests/test_structure.py`
- **L871 — Phase 8 — 09:25 Premarket Refresh / Tests:** Lost confluence -> WEAKENED.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L893 — Phase 9 — Live Setup State Machines / Live loop:** Use completed bars only.
  - Evidence: `src/data_clock.py`, `src/resample.py`
- **L901 — Phase 9 — Live Setup State Machines / Reversal states:** LIQUIDITY_REACHED
  - Evidence: `src/liquidity.py`
- **L903 — Phase 9 — Live Setup State Machines / Reversal states:** DISPLACEMENT_CONFIRMED
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L914 — Phase 9 — Live Setup State Machines / Continuation states:** DISPLACEMENT_BREAK
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L925 — Phase 9 — Live Setup State Machines / Alerts:** BIAS CHANGED.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L927 — Phase 9 — Live Setup State Machines / Alerts:** LIQUIDITY SWEPT.
  - Evidence: `src/liquidity.py`
- **L928 — Phase 9 — Live Setup State Machines / Alerts:** DISPLACEMENT CONFIRMED.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L980 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Logging:** Structured logs under data/logs/.
  - Evidence: `src/structure.py`, `tests/test_structure.py`
- **L982 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Logging:** Log requests, contract, bar count, latest timestamp, validation, state-build duration, scenario scores, reports, alerts, failures.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L996 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 08:58 ET — ProjectX collection.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`
- **L1030 — Phase 11 — Shadow Mode / Minimum sample:** At least 10 trading sessions.
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `tests/test_sessions.py`
- **L1040 — Phase 11 — Shadow Mode / Save every day:** Session high/low.
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `tests/test_sessions.py`
- **L1051 — Phase 11 — Shadow Mode / Daily evaluation:** Bias correctness.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L1093 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Validate rollover boundaries.
  - Evidence: `src/rollover.py`, `tests/test_rollover.py`
- **L1094 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Do not assume TopstepX auto-roll chart behavior equals ProjectX historical API behavior.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`
- **L1095 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Keep NQ and MNQ volume histories separate.
  - Evidence: `src/volume.py`, `tests/test_volume.py`
- **L1101 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Bias accuracy.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L1111 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Performance by setup, score band, DOL, session context, direction, and volatility regime.
  - Evidence: `config/sessions.yaml`, `src/scorer.py`, `src/scorer_harmonization.py`, `src/sessions.py`, `tests/test_scorer.py`, `tests/test_sessions.py`
- **L1115 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Displacement thresholds.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L1116 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Signal-to-noise thresholds/weights.
  - Evidence: `src/snr.py`, `tests/test_snr.py`, `tests/test_snr_production.py`
- **L1117 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Support/resistance confluence weights.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L1118 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Scorer component weights.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L1121 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Swing parameters.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L1122 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** FVG significance.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L1123 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Volume/RVOL thresholds.
  - Evidence: `src/volume.py`, `tests/test_volume.py`
- **L1136 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Higher score bands should outperform lower bands over meaningful samples.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L1137 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Do not call score a probability until calibrated.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L1142 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Benchmark current FVG stage.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L1152 — Phase 12 — Formal Backtesting / Calibration / Done when:** Score bands show meaningful separation.
  - Evidence: `src/scorer.py`, `src/scorer_harmonization.py`, `tests/test_scorer.py`
- **L1162 — Phase 12 — Formal Backtesting / Calibration / Done when:** ProjectX live collection reliable.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`
- **L1164 — Phase 12 — Formal Backtesting / Calibration / Done when:** Session/as_of logic causal.
  - Evidence: `config/sessions.yaml`, `run_pipeline.py`, `src/data_clock.py`, `src/sessions.py`, `tests/test_pipeline_as_of.py`, `tests/test_replay_parity.py`, `tests/test_sessions.py`
- **L1166 — Phase 12 — Formal Backtesting / Calibration / Done when:** Required session levels reliable.
  - Evidence: `config/sessions.yaml`, `src/sessions.py`, `tests/test_sessions.py`
- **L1167 — Phase 12 — Formal Backtesting / Calibration / Done when:** VWAP reliable.
  - Evidence: `src/vwap.py`, `tests/test_vwap.py`
- **L1168 — Phase 12 — Formal Backtesting / Calibration / Done when:** HTF bias reliable.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L1169 — Phase 12 — Formal Backtesting / Calibration / Done when:** Volume/RVOL reliable.
  - Evidence: `src/volume.py`, `tests/test_volume.py`
- **L1170 — Phase 12 — Formal Backtesting / Calibration / Done when:** Swings/equal highs-lows reliable.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L1171 — Phase 12 — Formal Backtesting / Calibration / Done when:** Protected/weak swings reliable.
  - Evidence: `src/swings.py`, `tests/test_swings.py`
- **L1172 — Phase 12 — Formal Backtesting / Calibration / Done when:** Liquidity registry reliable.
  - Evidence: `src/liquidity.py`
- **L1173 — Phase 12 — Formal Backtesting / Calibration / Done when:** FVG/IFVG state reliable.
  - Evidence: `src/fvg.py`, `src/fvg_state.py`, `tests/test_fvg.py`, `tests/test_fvg_state.py`
- **L1174 — Phase 12 — Formal Backtesting / Calibration / Done when:** Displacement explainable.
  - Evidence: `src/displacement.py`, `tests/test_displacement.py`
- **L1175 — Phase 12 — Formal Backtesting / Calibration / Done when:** Structure distinguishes sweeps vs valid breaks.
  - Evidence: `src/structure.py`, `tests/test_structure.py`
- **L1177 — Phase 12 — Formal Backtesting / Calibration / Done when:** PD arrays tracked.
  - Evidence: `src/pd_arrays.py`, `tests/test_pd_arrays.py`
- **L1178 — Phase 12 — Formal Backtesting / Calibration / Done when:** Signal-to-noise available.
  - Evidence: `src/snr.py`, `tests/test_snr.py`, `tests/test_snr_production.py`
- **L1179 — Phase 12 — Formal Backtesting / Calibration / Done when:** Support/resistance confluence separately available.
  - Evidence: `src/confluence_zones.py`, `tests/test_confluence_zones.py`
- **L1215 — Phase 12 — Formal Backtesting / Calibration / Done when:** Read phases.md.
  - Evidence: `phases.md`
- **L1226 — Phase 12 — Formal Backtesting / Calibration / Done when:** Update phases.md.
  - Evidence: `phases.md`
- **L1231 — Phase 12 — Formal Backtesting / Calibration / Done when:** Rebuild bias.py from scratch without a verified defect.
  - Evidence: `src/bias.py`, `tests/test_bias.py`
- **L1233 — Phase 12 — Formal Backtesting / Calibration / Done when:** Replace snr.py with support/resistance logic.
  - Evidence: `src/confluence_zones.py`, `src/snr.py`, `tests/test_confluence_zones.py`, `tests/test_snr.py`, `tests/test_snr_production.py`
- **L1258 — Phase 12 — Formal Backtesting / Calibration / Done when:** Confirm live ProjectX pull.
  - Evidence: `scripts/collect_projectx.py`, `src/projectx_client.py`, `tests/test_projectx_client.py`

## Checked items with missing explicit references (potential roadmap errors)

- **L335 — Phase 3 — Objective Market Features / 3A — VWAP:** Use typical price (high + low + close) / 3.
  - Evidence: `MISSING:(high + low + close) / 3`

## Unchecked manual / observational requirements

- **L531 — Phase 3 — Objective Market Features / Done when:** Important levels/features match several manually inspected historical chart days.
- **L623 — Phase 5 — Market State Engine / Core module:** Include news/event-risk field, even if MVP is manual/unavailable.
- **L970 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Check credentials/auth.
- **L1008 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Verify each job manually first.
- **L1057 — Phase 11 — Shadow Mode / Human comparison:** Compare automated state to manual chart review.
- **L1237 — Phase 12 — Formal Backtesting / Calibration / Done when:** Commit credentials.

## Unchecked items with no direct mechanical evidence

- **L37 — Global rules — apply to every phase / Architecture:** Add LLM prose only after deterministic market state and trade planning are reliable.
- **L46 — Global rules — apply to every phase / No lookahead:** Preserve completed-bar semantics in both historical and live modes.
- **L47 — Global rules — apply to every phase / No lookahead:** Maintain future-mutation / append-invariance tests for every important feature.
- **L77 — Global rules — apply to every phase / Scoring:** Later expose a report-friendly 0–10 confidence display if useful.
- **L93 — Global rules — apply to every phase / Git / multi-conversation workflow:** Inspect every file before modifying it.
- **L94 — Global rules — apply to every phase / Git / multi-conversation workflow:** Do not assume remembered code from another conversation is newer than GitHub.
- **L95 — Global rules — apply to every phase / Git / multi-conversation workflow:** Update this checklist after each completed milestone.
- **L96 — Global rules — apply to every phase / Git / multi-conversation workflow:** Keep secrets and market datasets out of Git.
- **L556 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Extend existing DOL; do not replace it.
- **L557 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Rank multiple candidate targets.
- **L558 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Produce Primary DOL.
- **L559 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Produce Alternate DOL.
- **L560 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate PDH/PDL.
- **L561 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate PMH/PML.
- **L562 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate Asia H/L.
- **L563 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate London H/L.
- **L564 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate weekly H/L.
- **L565 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Candidate equal highs/lows.
- **L569 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider premium/discount.
- **L571 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider recent sweeps.
- **L572 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider PD-array state.
- **L574 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider target distance.
- **L575 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Consider obstacles/room-to-run.
- **L577 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Preserve source/price/distance/confidence.
- **L578 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Return neutral when evidence is insufficient/conflicting.
- **L579 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v2 — production requirements:** Add future-mutation invariance tests.
- **L583 — Phase 4 — Production Displacement + Draw on Liquidity / Sweep vs break classification:** Formalize reversal sequence.
- **L584 — Phase 4 — Production Displacement + Draw on Liquidity / Sweep vs break classification:** Formalize continuation sequence.
- **L586 — Phase 4 — Production Displacement + Draw on Liquidity / Sweep vs break classification:** Require full confirmation sequence before entry-valid state.
- **L591 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** DOL emits primary + alternate targets.
- **L592 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** DOL is explainable and causal.
- **L593 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** Replay/live behavior is consistent.
- **L594 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** Full suite is green.
- **L595 — Phase 4 — Production Displacement + Draw on Liquidity / Done when:** Push checkpoint and update this file.
- **L607 — Phase 5 — Market State Engine / Core module:** Create src/market_state.py.
- **L608 — Phase 5 — Market State Engine / Core module:** Define schema/version.
- **L610 — Phase 5 — Market State Engine / Core module:** Include symbol/contract/latest price metadata.
- **L621 — Phase 5 — Market State Engine / Core module:** Include Primary/Alternate DOL.
- **L624 — Phase 5 — Market State Engine / Core module:** Include trade-candidate section.
- **L628 — Phase 5 — Market State Engine / Required levels:** PDH/PDL.
- **L629 — Phase 5 — Market State Engine / Required levels:** Previous close.
- **L630 — Phase 5 — Market State Engine / Required levels:** Prior-day half-back.
- **L631 — Phase 5 — Market State Engine / Required levels:** PMH/PML.
- **L632 — Phase 5 — Market State Engine / Required levels:** Asia High/Low.
- **L633 — Phase 5 — Market State Engine / Required levels:** London High/Low.
- **L634 — Phase 5 — Market State Engine / Required levels:** Overnight High/Low.
- **L635 — Phase 5 — Market State Engine / Required levels:** Week High/Low.
- **L638 — Phase 5 — Market State Engine / Required levels:** Nearest equal highs/lows.
- **L642 — Phase 5 — Market State Engine / Required levels:** Cash open / OR5 / OR15 when available.
- **L646 — Phase 5 — Market State Engine / Snapshot storage:** Create data/state/.
- **L647 — Phase 5 — Market State Engine / Snapshot storage:** Save timestamped snapshots, e.g. YYYY-MM-DD_0900_market_state.json.
- **L648 — Phase 5 — Market State Engine / Snapshot storage:** Save separate 09:25 snapshot.
- **L649 — Phase 5 — Market State Engine / Snapshot storage:** Maintain latest.json only as convenience copy/pointer.
- **L650 — Phase 5 — Market State Engine / Snapshot storage:** Never overwrite the only historical state.
- **L651 — Phase 5 — Market State Engine / Snapshot storage:** Include schema version and source snapshot references.
- **L656 — Phase 5 — Market State Engine / Safe failure states:** NO ANALYSIS — STALE MARKET DATA.
- **L657 — Phase 5 — Market State Engine / Safe failure states:** ANALYSIS DEGRADED — REQUIRED HISTORY INCOMPLETE.
- **L658 — Phase 5 — Market State Engine / Safe failure states:** Never silently substitute an old state for a fresh one.
- **L662 — Phase 5 — Market State Engine / Tests:** tests/test_market_state.py.
- **L663 — Phase 5 — Market State Engine / Tests:** Schema test.
- **L665 — Phase 5 — Market State Engine / Tests:** Storage test.
- **L666 — Phase 5 — Market State Engine / Tests:** Fatal/degraded data-quality tests.
- **L667 — Phase 5 — Market State Engine / Tests:** Historical prefix invariant with future bars appended.
- **L671 — Phase 5 — Market State Engine / Done when:** One JSON contains every deterministic fact required for morning analysis.
- **L672 — Phase 5 — Market State Engine / Done when:** State is versioned and snapshot-safe.
- **L673 — Phase 5 — Market State Engine / Done when:** No-lookahead is proven.
- **L674 — Phase 5 — Market State Engine / Done when:** Full suite is green.
- **L675 — Phase 5 — Market State Engine / Done when:** Push checkpoint and update this file.
- **L687 — Phase 6 — Trade Planner / Core:** Create src/trade_planner.py.
- **L688 — Phase 6 — Trade Planner / Core:** Consume market state, not arbitrary raw bars.
- **L689 — Phase 6 — Trade Planner / Core:** Produce preferred.
- **L690 — Phase 6 — Trade Planner / Core:** Produce alternate.
- **L691 — Phase 6 — Trade Planner / Core:** Support NO TRADE.
- **L695 — Phase 6 — Trade Planner / Each candidate must include:** Direction.
- **L696 — Phase 6 — Trade Planner / Each candidate must include:** Setup family/subtype.
- **L697 — Phase 6 — Trade Planner / Each candidate must include:** Trigger level/zone.
- **L698 — Phase 6 — Trade Planner / Each candidate must include:** Entry zone.
- **L699 — Phase 6 — Trade Planner / Each candidate must include:** Structural invalidation.
- **L700 — Phase 6 — Trade Planner / Each candidate must include:** SL and risk distance.
- **L701 — Phase 6 — Trade Planner / Each candidate must include:** TP1/TP2/TP3/TP4.
- **L702 — Phase 6 — Trade Planner / Each candidate must include:** Reason/source for every target.
- **L703 — Phase 6 — Trade Planner / Each candidate must include:** Confirmation criteria.
- **L704 — Phase 6 — Trade Planner / Each candidate must include:** Invalidation criteria.
- **L705 — Phase 6 — Trade Planner / Each candidate must include:** Nearby obstacles.
- **L706 — Phase 6 — Trade Planner / Each candidate must include:** Distance to first obstacle/primary target.
- **L707 — Phase 6 — Trade Planner / Each candidate must include:** Reward/risk.
- **L714 — Phase 6 — Trade Planner / Reversal planner:** Sweep.
- **L715 — Phase 6 — Trade Planner / Reversal planner:** Failure to accept beyond level.
- **L717 — Phase 6 — Trade Planner / Reversal planner:** MSS/CHOCH.
- **L718 — Phase 6 — Trade Planner / Reversal planner:** Retest.
- **L719 — Phase 6 — Trade Planner / Reversal planner:** Entry confirmation.
- **L720 — Phase 6 — Trade Planner / Reversal planner:** 09:00 scenario remains a hypothesis unless triggers already exist.
- **L724 — Phase 6 — Trade Planner / Continuation planner:** Important level.
- **L726 — Phase 6 — Trade Planner / Continuation planner:** Body close beyond level.
- **L727 — Phase 6 — Trade Planner / Continuation planner:** Acceptance/follow-through.
- **L728 — Phase 6 — Trade Planner / Continuation planner:** Pullback.
- **L730 — Phase 6 — Trade Planner / Continuation planner:** Micro BOS.
- **L731 — Phase 6 — Trade Planner / Continuation planner:** Entry confirmation.
- **L736 — Phase 6 — Trade Planner / Stop logic:** Add configurable buffer.
- **L737 — Phase 6 — Trade Planner / Stop logic:** Calculate actual risk.
- **L739 — Phase 6 — Trade Planner / Stop logic:** Never force a stop inside structural invalidation.
- **L740 — Phase 6 — Trade Planner / Stop logic:** Reject setup when valid stop is materially too large.
- **L744 — Phase 6 — Trade Planner / Target logic:** TP1 from nearest internal objective / ~1R where possible.
- **L745 — Phase 6 — Trade Planner / Target logic:** TP2 from next meaningful objective.
- **L746 — Phase 6 — Trade Planner / Target logic:** TP3 from Primary DOL / major objective.
- **L748 — Phase 6 — Trade Planner / Target logic:** Record why each target was selected.
- **L752 — Phase 6 — Trade Planner / Room-to-run:** Detect immediate opposing HTF obstacle.
- **L753 — Phase 6 — Trade Planner / Room-to-run:** Detect insufficient room to TP1/primary target.
- **L754 — Phase 6 — Trade Planner / Room-to-run:** Reject/downgrade poor asymmetric setups.
- **L755 — Phase 6 — Trade Planner / Room-to-run:** Record rejection reason.
- **L759 — Phase 6 — Trade Planner / Tests:** tests/test_trade_planner.py.
- **L760 — Phase 6 — Trade Planner / Tests:** Structural stop test.
- **L761 — Phase 6 — Trade Planner / Tests:** Oversized-risk rejection.
- **L762 — Phase 6 — Trade Planner / Tests:** Target-priority test.
- **L763 — Phase 6 — Trade Planner / Tests:** Room-to-run test.
- **L764 — Phase 6 — Trade Planner / Tests:** Preferred/alternate test.
- **L765 — Phase 6 — Trade Planner / Tests:** No-trade test.
- **L766 — Phase 6 — Trade Planner / Tests:** No-lookahead test.
- **L770 — Phase 6 — Trade Planner / Done when:** Preferred/alternate are deterministic.
- **L771 — Phase 6 — Trade Planner / Done when:** Stops are structural.
- **L772 — Phase 6 — Trade Planner / Done when:** Targets are market-derived.
- **L773 — Phase 6 — Trade Planner / Done when:** Poor setups are rejected.
- **L774 — Phase 6 — Trade Planner / Done when:** Replay-safe.
- **L775 — Phase 6 — Trade Planner / Done when:** Full suite green.
- **L776 — Phase 6 — Trade Planner / Done when:** Push checkpoint and update this file.
- **L789 — Phase 7 — Morning Output / Report / Deterministic outputs:** Deterministic Markdown report.
- **L790 — Phase 7 — Morning Output / Report / Deterministic outputs:** Save under data/reports/.
- **L791 — Phase 7 — Morning Output / Report / Deterministic outputs:** Timestamp every report.
- **L792 — Phase 7 — Morning Output / Report / Deterministic outputs:** Link report to source market-state snapshot.
- **L796 — Phase 7 — Morning Output / Report / Required sections:** Current Market Context.
- **L798 — Phase 7 — Morning Output / Report / Required sections:** Primary DOL.
- **L799 — Phase 7 — Morning Output / Report / Required sections:** Alternate DOL where useful.
- **L801 — Phase 7 — Morning Output / Report / Required sections:** Chart Markup.
- **L802 — Phase 7 — Morning Output / Report / Required sections:** Scenario A — Preferred.
- **L803 — Phase 7 — Morning Output / Report / Required sections:** Scenario B — Alternate.
- **L804 — Phase 7 — Morning Output / Report / Required sections:** Trigger Zones.
- **L805 — Phase 7 — Morning Output / Report / Required sections:** Best Play Right Now.
- **L809 — Phase 7 — Morning Output / Report / Chart markup:** PDH/PDL.
- **L810 — Phase 7 — Morning Output / Report / Chart markup:** PMH/PML.
- **L811 — Phase 7 — Morning Output / Report / Chart markup:** Asia H/L.
- **L812 — Phase 7 — Morning Output / Report / Chart markup:** London H/L.
- **L813 — Phase 7 — Morning Output / Report / Chart markup:** Primary DOL.
- **L815 — Phase 7 — Morning Output / Report / Chart markup:** Preferred long/short trigger.
- **L816 — Phase 7 — Morning Output / Report / Chart markup:** No-trade zone.
- **L817 — Phase 7 — Morning Output / Report / Chart markup:** Entry/SL/TP1–TP4.
- **L821 — Phase 7 — Morning Output / Report / Behavior:** 09:00 report is explicitly a hypothesis/plan.
- **L822 — Phase 7 — Morning Output / Report / Behavior:** Do not mark a setup confirmed unless deterministic state confirms it.
- **L823 — Phase 7 — Morning Output / Report / Behavior:** Use NO TRADE when appropriate.
- **L824 — Phase 7 — Morning Output / Report / Behavior:** Use NO ANALYSIS on fatal data problems.
- **L825 — Phase 7 — Morning Output / Report / Behavior:** Never invent/recalculate deterministic levels in prose.
- **L829 — Phase 7 — Morning Output / Report / Optional LLM layer:** Create src/report_generator.py only after deterministic output is reliable.
- **L830 — Phase 7 — Morning Output / Report / Optional LLM layer:** Version-control prompt files.
- **L831 — Phase 7 — Morning Output / Report / Optional LLM layer:** Send market state rather than raw 10k bars.
- **L832 — Phase 7 — Morning Output / Report / Optional LLM layer:** Explicitly forbid invented/altered levels.
- **L833 — Phase 7 — Morning Output / Report / Optional LLM layer:** Preserve deterministic JSON if LLM generation fails.
- **L837 — Phase 7 — Morning Output / Report / Done when:** Deterministic report matches the required format.
- **L838 — Phase 7 — Morning Output / Report / Done when:** Chart markup is complete.
- **L839 — Phase 7 — Morning Output / Report / Done when:** Preferred/alternate scenarios are clear.
- **L840 — Phase 7 — Morning Output / Report / Done when:** LLM is optional rather than required for calculations.
- **L841 — Phase 7 — Morning Output / Report / Done when:** Full suite green.
- **L842 — Phase 7 — Morning Output / Report / Done when:** Push checkpoint and update this file.
- **L855 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Validate freshness.
- **L856 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Save new raw snapshot.
- **L858 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Save separate 09:25 state.
- **L860 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Compare 09:00 vs 09:25.
- **L861 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Classify UNCHANGED.
- **L862 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Classify STRENGTHENED.
- **L863 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Classify WEAKENED.
- **L864 — Phase 8 — 09:25 Premarket Refresh / Checklist:** Classify FLIPPED.
- **L869 — Phase 8 — 09:25 Premarket Refresh / Tests:** Identical snapshots -> UNCHANGED.
- **L870 — Phase 8 — 09:25 Premarket Refresh / Tests:** Added supportive evidence -> STRENGTHENED.
- **L872 — Phase 8 — 09:25 Premarket Refresh / Tests:** Directional reversal -> FLIPPED.
- **L873 — Phase 8 — 09:25 Premarket Refresh / Tests:** No 09:30+ information in 09:25 state.
- **L877 — Phase 8 — 09:25 Premarket Refresh / Done when:** Both snapshots are preserved independently.
- **L878 — Phase 8 — 09:25 Premarket Refresh / Done when:** Comparison is deterministic and traceable.
- **L879 — Phase 8 — 09:25 Premarket Refresh / Done when:** Full suite green.
- **L880 — Phase 8 — 09:25 Premarket Refresh / Done when:** Push checkpoint and update this file.
- **L892 — Phase 9 — Live Setup State Machines / Live loop:** Poll roughly once per minute.
- **L894 — Phase 9 — Live Setup State Machines / Live loop:** Validate each update and detect stale feed.
- **L895 — Phase 9 — Live Setup State Machines / Live loop:** Preserve state between iterations/restarts where needed.
- **L896 — Phase 9 — Live Setup State Machines / Live loop:** End standard monitoring at 10:30 ET.
- **L900 — Phase 9 — Live Setup State Machines / Reversal states:** ARMED
- **L902 — Phase 9 — Live Setup State Machines / Reversal states:** SWEEP_CONFIRMED
- **L904 — Phase 9 — Live Setup State Machines / Reversal states:** MSS_CONFIRMED
- **L905 — Phase 9 — Live Setup State Machines / Reversal states:** WAIT_RETEST
- **L906 — Phase 9 — Live Setup State Machines / Reversal states:** RETEST_HOLDS
- **L907 — Phase 9 — Live Setup State Machines / Reversal states:** ENTRY_VALID
- **L908 — Phase 9 — Live Setup State Machines / Reversal states:** INVALIDATED
- **L912 — Phase 9 — Live Setup State Machines / Continuation states:** ARMED
- **L913 — Phase 9 — Live Setup State Machines / Continuation states:** LEVEL_REACHED
- **L915 — Phase 9 — Live Setup State Machines / Continuation states:** ACCEPTANCE
- **L916 — Phase 9 — Live Setup State Machines / Continuation states:** WAIT_RETEST
- **L917 — Phase 9 — Live Setup State Machines / Continuation states:** RETEST_HOLDS
- **L918 — Phase 9 — Live Setup State Machines / Continuation states:** MICRO_BOS
- **L919 — Phase 9 — Live Setup State Machines / Continuation states:** ENTRY_VALID
- **L920 — Phase 9 — Live Setup State Machines / Continuation states:** INVALIDATED
- **L924 — Phase 9 — Live Setup State Machines / Alerts:** PREMARKET PLAN READY.
- **L926 — Phase 9 — Live Setup State Machines / Alerts:** TRIGGER ZONE REACHED.
- **L929 — Phase 9 — Live Setup State Machines / Alerts:** MSS/CHOCH CONFIRMED.
- **L930 — Phase 9 — Live Setup State Machines / Alerts:** RETEST IN PROGRESS.
- **L931 — Phase 9 — Live Setup State Machines / Alerts:** ENTRY VALID.
- **L932 — Phase 9 — Live Setup State Machines / Alerts:** SETUP INVALIDATED.
- **L933 — Phase 9 — Live Setup State Machines / Alerts:** TP1/TP2/TP3/TP4 HIT.
- **L937 — Phase 9 — Live Setup State Machines / Deduplication:** Persist scenario ID.
- **L938 — Phase 9 — Live Setup State Machines / Deduplication:** Persist last state/alert time.
- **L939 — Phase 9 — Live Setup State Machines / Deduplication:** Alert only on meaningful state change.
- **L940 — Phase 9 — Live Setup State Machines / Deduplication:** Do not repeat the same alert every minute.
- **L944 — Phase 9 — Live Setup State Machines / Replay tests:** Reversal sequence replay.
- **L945 — Phase 9 — Live Setup State Machines / Replay tests:** Continuation sequence replay.
- **L946 — Phase 9 — Live Setup State Machines / Replay tests:** Invalidation replay.
- **L947 — Phase 9 — Live Setup State Machines / Replay tests:** No-lookahead transition test.
- **L948 — Phase 9 — Live Setup State Machines / Replay tests:** No duplicate-alert test.
- **L949 — Phase 9 — Live Setup State Machines / Replay tests:** Restart/recovery test.
- **L953 — Phase 9 — Live Setup State Machines / Done when:** Both setup families work deterministically.
- **L954 — Phase 9 — Live Setup State Machines / Done when:** Alerts occur only on meaningful transitions.
- **L955 — Phase 9 — Live Setup State Machines / Done when:** Replay/live logic is shared.
- **L956 — Phase 9 — Live Setup State Machines / Done when:** Full suite green.
- **L957 — Phase 9 — Live Setup State Machines / Done when:** Push checkpoint and update this file.
- **L969 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Create scripts/healthcheck.py.
- **L971 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Check current contract.
- **L972 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Check data directory write access.
- **L973 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Check latest-bar freshness.
- **L974 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Check required modules/config files.
- **L975 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Run lightweight test subset if appropriate.
- **L976 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Health check:** Exit non-zero on critical failure.
- **L981 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Logging:** Log auth success/failure without secrets.
- **L983 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Logging:** Never log passwords/API keys.
- **L987 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Orchestrator:** Create one orchestrator if practical.
- **L988 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Orchestrator:** Premarket mode.
- **L989 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Orchestrator:** Refresh mode.
- **L990 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Orchestrator:** Live-monitor mode.
- **L991 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Orchestrator:** Minimize duplicated code.
- **L995 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 08:55 ET — health check.
- **L997 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 09:00 ET — state + morning plan.
- **L998 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 09:25 ET — refresh + thesis comparison.
- **L999 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 09:29 ET — live monitor armed.
- **L1000 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 09:30–10:30 ET — monitoring.
- **L1001 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Schedule:** 10:30 ET — close monitor + save recap.
- **L1005 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Check timedatectl.
- **L1006 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Choose systemd timers vs cron.
- **L1007 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Use ET-aware scheduling and automatic EST/EDT handling.
- **L1009 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Verify jobs survive VPS reboot.
- **L1010 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / VPS scheduling:** Verify logs prove execution.
- **L1014 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Done when:** Full weekday workflow runs automatically.
- **L1015 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Done when:** Logs provide audit trail.
- **L1016 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Done when:** Failure handling is safe.
- **L1017 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Done when:** Services survive restart.
- **L1018 — Phase 10 — VPS Orchestration, Health, Logging, Scheduling / Done when:** Push checkpoint and update this file.
- **L1031 — Phase 11 — Shadow Mode / Minimum sample:** Prefer 20+ before aggressive tuning.
- **L1035 — Phase 11 — Shadow Mode / Save every day:** 09:00 state + plan.
- **L1036 — Phase 11 — Shadow Mode / Save every day:** 09:25 state + update.
- **L1037 — Phase 11 — Shadow Mode / Save every day:** Every live state transition.
- **L1038 — Phase 11 — Shadow Mode / Save every day:** Entry-valid and invalidation events.
- **L1039 — Phase 11 — Shadow Mode / Save every day:** TP1–TP4 outcomes.
- **L1041 — Phase 11 — Shadow Mode / Save every day:** MFE/MAE.
- **L1042 — Phase 11 — Shadow Mode / Save every day:** Final scenario outcome.
- **L1046 — Phase 11 — Shadow Mode / Daily evaluation:** Preferred direction/setup.
- **L1047 — Phase 11 — Shadow Mode / Daily evaluation:** Alternate setup.
- **L1048 — Phase 11 — Shadow Mode / Daily evaluation:** Setup confirmed / entry triggered.
- **L1049 — Phase 11 — Shadow Mode / Daily evaluation:** SL / TP results.
- **L1050 — Phase 11 — Shadow Mode / Daily evaluation:** MFE/MAE.
- **L1052 — Phase 11 — Shadow Mode / Daily evaluation:** DOL result.
- **L1053 — Phase 11 — Shadow Mode / Daily evaluation:** Notes.
- **L1058 — Phase 11 — Shadow Mode / Human comparison:** Compare levels to TradingView/Topstep charts.
- **L1059 — Phase 11 — Shadow Mode / Human comparison:** Separate implementation bugs from losing trades.
- **L1060 — Phase 11 — Shadow Mode / Human comparison:** Do not change strategy after every losing day.
- **L1064 — Phase 11 — Shadow Mode / Done when:** Minimum shadow sample collected.
- **L1065 — Phase 11 — Shadow Mode / Done when:** No critical calculation errors remain.
- **L1066 — Phase 11 — Shadow Mode / Done when:** Production timing is reliable.
- **L1067 — Phase 11 — Shadow Mode / Done when:** Records are complete enough for calibration.
- **L1068 — Phase 11 — Shadow Mode / Done when:** Update this file with observed issues.
- **L1088 — Phase 12 — Formal Backtesting / Calibration / Existing infrastructure:** Continue using these tools during earlier phases for replay/regression.
- **L1092 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Use explicit quarterly contracts where required.
- **L1096 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Preserve source/contract metadata.
- **L1097 — Phase 12 — Formal Backtesting / Calibration / Historical data discipline:** Preserve exact datasets/snapshots used for results.
- **L1102 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Preferred-scenario accuracy.
- **L1103 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Trigger precision.
- **L1104 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Win rate.
- **L1105 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Average/median R.
- **L1106 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Expectancy / profit factor.
- **L1107 — Phase 12 — Formal Backtesting / Calibration / Metrics:** TP1–TP4 hit rates.
- **L1108 — Phase 12 — Formal Backtesting / Calibration / Metrics:** Stop/no-trade rates.
- **L1109 — Phase 12 — Formal Backtesting / Calibration / Metrics:** MFE/MAE.
- **L1110 — Phase 12 — Formal Backtesting / Calibration / Metrics:** False sweep/breakout rates.
- **L1119 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Confidence bands.
- **L1120 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** DOL thresholds/weights.
- **L1124 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Stop buffers.
- **L1125 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Room-to-run filters.
- **L1126 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Exit model.
- **L1127 — Phase 12 — Formal Backtesting / Calibration / Parameters to calibrate:** Target priorities.
- **L1131 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Do not optimize solely for maximum historical profit.
- **L1132 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Prefer stable parameters across regimes.
- **L1133 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Use walk-forward/out-of-sample evaluation.
- **L1134 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Keep tuning/evaluation periods distinct.
- **L1135 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Compare historical results to shadow-mode observations.
- **L1138 — Phase 12 — Formal Backtesting / Calibration / Calibration rules:** Preserve old configs/results for reproducibility.
- **L1143 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Create exact-output regression fixture.
- **L1144 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Optimize implementation.
- **L1145 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Prove output equivalence.
- **L1146 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Re-run full suite.
- **L1147 — Phase 12 — Formal Backtesting / Calibration / FVG performance optimization:** Benchmark improved runtime.
- **L1151 — Phase 12 — Formal Backtesting / Calibration / Done when:** Model evaluated over sufficient historical + shadow data.
- **L1153 — Phase 12 — Formal Backtesting / Calibration / Done when:** Parameters are stable out of sample.
- **L1154 — Phase 12 — Formal Backtesting / Calibration / Done when:** Production config is versioned.
- **L1155 — Phase 12 — Formal Backtesting / Calibration / Done when:** Baseline metrics are stored.
- **L1156 — Phase 12 — Formal Backtesting / Calibration / Done when:** Push checkpoint and update this file.
- **L1163 — Phase 12 — Formal Backtesting / Calibration / Done when:** Data freshness enforced.
- **L1165 — Phase 12 — Formal Backtesting / Calibration / Done when:** Required multi-timeframe data reliable.
- **L1176 — Phase 12 — Formal Backtesting / Calibration / Done when:** Premium/discount reliable.
- **L1180 — Phase 12 — Formal Backtesting / Calibration / Done when:** Primary + Alternate DOL available.
- **L1181 — Phase 12 — Formal Backtesting / Calibration / Done when:** Market-state snapshots stable.
- **L1182 — Phase 12 — Formal Backtesting / Calibration / Done when:** Trade planner produces preferred/alternate scenarios.
- **L1183 — Phase 12 — Formal Backtesting / Calibration / Done when:** Stops use structural invalidation.
- **L1184 — Phase 12 — Formal Backtesting / Calibration / Done when:** TP1–TP4 map to real objectives.
- **L1185 — Phase 12 — Formal Backtesting / Calibration / Done when:** 09:00 report complete.
- **L1186 — Phase 12 — Formal Backtesting / Calibration / Done when:** 09:25 comparison works.
- **L1187 — Phase 12 — Formal Backtesting / Calibration / Done when:** Reversal/continuation live state machines work.
- **L1188 — Phase 12 — Formal Backtesting / Calibration / Done when:** Alerts deduplicated.
- **L1189 — Phase 12 — Formal Backtesting / Calibration / Done when:** VPS scheduling reliable.
- **L1190 — Phase 12 — Formal Backtesting / Calibration / Done when:** Failure handling safe.
- **L1191 — Phase 12 — Formal Backtesting / Calibration / Done when:** Shadow mode completed.
- **L1192 — Phase 12 — Formal Backtesting / Calibration / Done when:** Calibration completed.
- **L1193 — Phase 12 — Formal Backtesting / Calibration / Done when:** No component submits brokerage orders.
- **L1216 — Phase 12 — Formal Backtesting / Calibration / Done when:** Inspect GitHub main.
- **L1217 — Phase 12 — Formal Backtesting / Calibration / Done when:** Run the current test suite.
- **L1218 — Phase 12 — Formal Backtesting / Calibration / Done when:** Identify the first unchecked item in the active phase.
- **L1219 — Phase 12 — Formal Backtesting / Calibration / Done when:** Inspect existing implementation before creating/replacing anything.
- **L1220 — Phase 12 — Formal Backtesting / Calibration / Done when:** Preserve tested modules.
- **L1221 — Phase 12 — Formal Backtesting / Calibration / Done when:** Make only the changes required for the current milestone.
- **L1222 — Phase 12 — Formal Backtesting / Calibration / Done when:** Add/update tests.
- **L1223 — Phase 12 — Formal Backtesting / Calibration / Done when:** Run targeted tests.
- **L1224 — Phase 12 — Formal Backtesting / Calibration / Done when:** Run full tests.
- **L1225 — Phase 12 — Formal Backtesting / Calibration / Done when:** Commit/push the tested checkpoint.
- **L1227 — Phase 12 — Formal Backtesting / Calibration / Done when:** Stop and report before starting the next major phase.
- **L1232 — Phase 12 — Formal Backtesting / Calibration / Done when:** Rebuild dol.py from scratch without a verified defect.
- **L1234 — Phase 12 — Formal Backtesting / Calibration / Done when:** Duplicate strategy logic for live mode.
- **L1235 — Phase 12 — Formal Backtesting / Calibration / Done when:** Let an LLM invent numeric price levels.
- **L1236 — Phase 12 — Formal Backtesting / Calibration / Done when:** Use future bars in historical replay.
- **L1238 — Phase 12 — Formal Backtesting / Calibration / Done when:** Auto-place trades.
- **L1239 — Phase 12 — Formal Backtesting / Calibration / Done when:** Aggressively tune parameters before sufficient data exists.
- **L1257 — Phase 12 — Formal Backtesting / Calibration / Done when:** Record the full test count.
- **L1259 — Phase 12 — Formal Backtesting / Calibration / Done when:** Confirm current contract.
- **L1260 — Phase 12 — Formal Backtesting / Calibration / Done when:** Confirm fresh latest bar.
- **L1261 — Phase 12 — Formal Backtesting / Calibration / Done when:** Confirm timestamped raw Parquet.
- **L1262 — Phase 12 — Formal Backtesting / Calibration / Done when:** Confirm metadata snapshot.
- **L1263 — Phase 12 — Formal Backtesting / Calibration / Done when:** Mark Phase 1 complete.
- **L1264 — Phase 12 — Formal Backtesting / Calibration / Done when:** Begin Phase 2.

## Checked items that still require semantic review

- **L36 — Global rules — apply to every phase / Architecture:** Python owns objective numeric calculations.
- **L38 — Global rules — apply to every phase / Architecture:** System is analysis/alerts only.
- **L39 — Global rules — apply to every phase / Architecture:** No automated order placement.
- **L40 — Global rules — apply to every phase / Architecture:** No automated brokerage position management.
- **L44 — Global rules — apply to every phase / No lookahead:** Existing research features were built with causal/no-lookahead behavior in mind.
- **L82 — Global rules — apply to every phase / Git / multi-conversation workflow:** GitHub main is implementation truth.
- **L103 — Current status snapshot:** DOL v1 exists and is integrated.
- **L110 — Current status snapshot:** Reproduce the current full-suite count on the VPS after the latest pull — 200 passed, 25 warnings at 9e7262a851e9c7264c3e0a66277b9ad13df8eef9.
- **L123 — Phase 0 — Baseline / Repository Audit / Checklist:** Existing trade-alerts repository identified.
- **L124 — Phase 0 — Baseline / Repository Audit / Checklist:** Existing feature/research modules inspected during prior development.
- **L125 — Phase 0 — Baseline / Repository Audit / Checklist:** Historical pipeline exists.
- **L129 — Phase 0 — Baseline / Repository Audit / Checklist:** DOL exists.
- **L131 — Phase 0 — Baseline / Repository Audit / Checklist:** Run git pull --ff-only on VPS.
- **L132 — Phase 0 — Baseline / Repository Audit / Checklist:** Confirm working tree is clean.
- **L133 — Phase 0 — Baseline / Repository Audit / Checklist:** Run pytest -q.
- **L134 — Phase 0 — Baseline / Repository Audit / Checklist:** Record current passing test count.
- **L135 — Phase 0 — Baseline / Repository Audit / Checklist:** Record warnings separately from failures.
- **L136 — Phase 0 — Baseline / Repository Audit / Checklist:** Confirm Python/venv versions.
- **L137 — Phase 0 — Baseline / Repository Audit / Checklist:** Confirm data directories are writable.
- **L138 — Phase 0 — Baseline / Repository Audit / Checklist:** Confirm .env is ignored by Git.
- **L147 — Phase 0 — Baseline / Repository Audit / Done when:** Latest main is pulled.
- **L148 — Phase 0 — Baseline / Repository Audit / Done when:** Full suite is green.
- **L149 — Phase 0 — Baseline / Repository Audit / Done when:** Working tree is clean.
- **L150 — Phase 0 — Baseline / Repository Audit / Done when:** Configs are backed up.
- **L151 — Phase 0 — Baseline / Repository Audit / Done when:** Test count and commit are recorded.
- **L169 — Phase 1 — ProjectX Collector / Client:** Preserve legacy TOPSTEP_USERNAME / TOPSTEP_API_KEY.
- **L170 — Phase 1 — ProjectX Collector / Client:** Authenticate.
- **L171 — Phase 1 — ProjectX Collector / Client:** Search/resolve contracts.
- **L172 — Phase 1 — ProjectX Collector / Client:** Retrieve bars.
- **L173 — Phase 1 — ProjectX Collector / Client:** Normalize timezone-aware OHLCV.
- **L174 — Phase 1 — ProjectX Collector / Client:** Normalize timestamps to UTC storage.
- **L175 — Phase 1 — ProjectX Collector / Client:** Detect malformed data.
- **L176 — Phase 1 — ProjectX Collector / Client:** Detect zero-bar responses.
- **L177 — Phase 1 — ProjectX Collector / Client:** Detect stale data.
- **L178 — Phase 1 — ProjectX Collector / Client:** Retry transient HTTP failures.
- **L179 — Phase 1 — ProjectX Collector / Client:** Respect request limits/chunking.
- **L180 — Phase 1 — ProjectX Collector / Client:** Use market-data endpoints only.
- **L185 — Phase 1 — ProjectX Collector / Collector script:** Save timestamped raw Parquet snapshots.
- **L186 — Phase 1 — ProjectX Collector / Collector script:** Save metadata snapshots.
- **L187 — Phase 1 — ProjectX Collector / Collector script:** Fail loudly on auth/data failure.
- **L189 — Phase 1 — ProjectX Collector / Collector script:** Verify correct active contract is selected — MNQU6 / CON.F.US.MNQ.U26.
- **L190 — Phase 1 — ProjectX Collector / Collector script:** Verify intended NQ/MNQ symbol — MNQ.
- **L192 — Phase 1 — ProjectX Collector / Collector script:** Verify saved Parquet loads successfully.
- **L193 — Phase 1 — ProjectX Collector / Collector script:** Verify metadata records contract/source/range accurately.
- **L194 — Phase 1 — ProjectX Collector / Collector script:** Verify no secret values appear in logs/output.
- **L195 — Phase 1 — ProjectX Collector / Collector script:** Verify stale/empty/error responses fail safely through collector validation/tests.
- **L200 — Phase 1 — ProjectX Collector / Compatibility:** Route historical CLI through reusable client.
- **L201 — Phase 1 — ProjectX Collector / Compatibility:** Preserve explicit historical contract workflows.
- **L207 — Phase 1 — ProjectX Collector / Tests:** Full suite reported at 180 passing after Phase 1 code.
- **L217 — Phase 1 — ProjectX Collector / Done when:** Code implemented.
- **L218 — Phase 1 — ProjectX Collector / Done when:** Tests implemented.
- **L219 — Phase 1 — ProjectX Collector / Done when:** Code pushed.
- **L221 — Phase 1 — ProjectX Collector / Done when:** Fresh snapshot + metadata verified.
- **L222 — Phase 1 — ProjectX Collector / Done when:** Phase 1 fully complete — verified 2026-09-02.
- **L234 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Canonical data contract:** timestamp is timezone-aware UTC storage.
- **L236 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Canonical data contract:** Source/symbol/contract metadata can be preserved.
- **L242 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Required-column checks exist.
- **L243 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Timestamp checks exist.
- **L244 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** OHLC consistency checks exist.
- **L245 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Duplicate/gap/outlier diagnostics exist.
- **L246 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Add/verify live freshness rules.
- **L247 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Distinguish warnings vs fatal errors for production analysis.
- **L248 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Validation:** Add degraded-analysis status for incomplete but usable history.
- **L255 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 1m
- **L256 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 5m
- **L257 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 15m
- **L258 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 30m
- **L259 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 1h
- **L260 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 4h
- **L261 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** Daily research resampling exists
- **L265 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 2m
- **L266 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** 3m
- **L267 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** Completed-bar visibility on every timeframe.
- **L268 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** available_at semantics on every timeframe.
- **L270 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** Daily does not accidentally use midnight UTC if futures trading date is intended.
- **L271 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** Deterministic boundaries through DST.
- **L272 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Resampling:** Replay reproduces the same multi-timeframe bars as live mode.
- **L277 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** ET conversion exists.
- **L278 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Prior-day/premarket/overnight/London logic exists in some form.
- **L280 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Verify final London definition.
- **L282 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Calculate Asia High/Low.
- **L283 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Verify London High/Low.
- **L284 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Verify overnight High/Low.
- **L285 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Verify PMH/PML.
- **L287 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Ensure finalized levels only appear when available.
- **L289 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Sessions:** Verify ET DST transitions.
- **L293 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** Previous close.
- **L294 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** Prior-day midpoint / half-back.
- **L295 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** Current week High/Low.
- **L296 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** Cash open after 09:30.
- **L297 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** OR5 High/Low.
- **L298 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Additional required levels:** OR15 High/Low.
- **L302 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 08:00 ET snapshot.
- **L303 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 09:00 ET snapshot.
- **L304 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 09:25 ET snapshot.
- **L305 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 09:29 ET snapshot.
- **L306 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 09:35 ET snapshot.
- **L307 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** 10:00 ET snapshot.
- **L309 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** No incomplete HTF bar visible.
- **L311 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Replay/no-lookahead checkpoints:** OR levels do not appear early.
- **L315 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** 2m/3m are supported.
- **L317 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** Asia/London/overnight/premarket levels are reliable.
- **L318 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** Prior/weekly/opening-range levels are reliable.
- **L320 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** Replay/no-lookahead tests are green.
- **L321 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** Full suite is green.
- **L322 — Phase 2 — Data Clock, Validation, Resampling, Sessions / Done when:** Push checkpoint and update this file.
- **L341 — Phase 3 — Objective Market Features / 3A — VWAP:** Recent cross if useful.
- **L342 — Phase 3 — Objective Market Features / 3A — VWAP:** Slope if useful.
- **L343 — Phase 3 — Objective Market Features / 3A — VWAP:** Unit tests.
- **L344 — Phase 3 — Objective Market Features / 3A — VWAP:** No-lookahead tests.
- **L349 — Phase 3 — Objective Market Features / 3B — Volume / RVOL:** Rolling RVOL exists.
- **L350 — Phase 3 — Objective Market Features / 3B — Volume / RVOL:** Time-of-day RVOL exists.
- **L351 — Phase 3 — Objective Market Features / 3B — Volume / RVOL:** Current implementation is causal.
- **L353 — Phase 3 — Objective Market Features / 3B — Volume / RVOL:** Expose rolling average/median.
- **L357 — Phase 3 — Objective Market Features / 3B — Volume / RVOL:** Verify DST/time-of-day behavior.
- **L363 — Phase 3 — Objective Market Features / 3C — HTF Bias:** Completed HTF bars are respected.
- **L366 — Phase 3 — Objective Market Features / 3C — HTF Bias:** Reconcile production HTF hierarchy with actual config.
- **L367 — Phase 3 — Objective Market Features / 3C — HTF Bias:** Decide exact 1H/30m/15m vs 4H/Daily roles.
- **L376 — Phase 3 — Objective Market Features / 3D — Swings:** Confirmation delay is causal.
- **L377 — Phase 3 — Objective Market Features / 3D — Swings:** Add timeframe metadata where needed.
- **L378 — Phase 3 — Objective Market Features / 3D — Swings:** Equal-high clustering.
- **L379 — Phase 3 — Objective Market Features / 3D — Swings:** Equal-low clustering.
- **L381 — Phase 3 — Objective Market Features / 3D — Swings:** Swept state.
- **L385 — Phase 3 — Objective Market Features / 3D — Swings:** Record reason for protected/weak status.
- **L386 — Phase 3 — Objective Market Features / 3D — Swings:** Add no-lookahead regressions.
- **L391 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Buy-side/sell-side sweep detection exists.
- **L393 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** PDH/PDL support exists.
- **L394 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** PMH/PML support exists.
- **L396 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Add Asia H/L.
- **L397 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Add weekly H/L.
- **L398 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Add equal highs/lows.
- **L400 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Add importance/components.
- **L401 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track untouched.
- **L402 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track approached.
- **L403 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track swept.
- **L404 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track broken.
- **L405 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track reclaimed.
- **L406 — Phase 3 — Objective Market Features / 3E — Liquidity Registry:** Track invalidated.
- **L413 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Correct three-candle definition exists.
- **L415 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Lifecycle/retest logic exists.
- **L416 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Tests exist.
- **L418 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Track timeframe in production state.
- **L419 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** ATR-relative size.
- **L420 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Mitigation percentage/full fill.
- **L421 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Invalidation.
- **L426 — Phase 3 — Objective Market Features / 3F — FVG / IFVG:** Add exact-output regression fixture.
- **L432 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Structural range high/low.
- **L433 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Equilibrium/midpoint.
- **L434 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Percentile within range.
- **L435 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Premium/discount/equilibrium classification.
- **L436 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Multiple relevant ranges/timeframes.
- **L437 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Avoid using premium/discount as a blind directional rule.
- **L438 — Phase 3 — Objective Market Features / 3G — Dealing Range / Premium-Discount:** Unit + no-lookahead tests.
- **L444 — Phase 3 — Objective Market Features / 3H — Displacement:** Body / ATR.
- **L445 — Phase 3 — Objective Market Features / 3H — Displacement:** Range / ATR.
- **L446 — Phase 3 — Objective Market Features / 3H — Displacement:** Close location.
- **L447 — Phase 3 — Objective Market Features / 3H — Displacement:** Consecutive directional candles.
- **L451 — Phase 3 — Objective Market Features / 3H — Displacement:** Follow-through.
- **L452 — Phase 3 — Objective Market Features / 3H — Displacement:** Preserve every raw component.
- **L454 — Phase 3 — Objective Market Features / 3H — Displacement:** Configurable thresholds.
- **L455 — Phase 3 — Objective Market Features / 3H — Displacement:** Provisional weak/moderate/strong categories.
- **L456 — Phase 3 — Objective Market Features / 3H — Displacement:** Unit + causal tests.
- **L461 — Phase 3 — Objective Market Features / 3I — Structure:** BOS/MSS/CHOCH-related logic exists.
- **L462 — Phase 3 — Objective Market Features / 3I — Structure:** Explicit wick-sweep vs body-close break distinction.
- **L464 — Phase 3 — Objective Market Features / 3I — Structure:** Continuation-break state.
- **L465 — Phase 3 — Objective Market Features / 3I — Structure:** Failed-break state.
- **L466 — Phase 3 — Objective Market Features / 3I — Structure:** Reclaim state.
- **L468 — Phase 3 — Objective Market Features / 3I — Structure:** Expose broken level/timeframe/timestamp/confirmation.
- **L470 — Phase 3 — Objective Market Features / 3I — Structure:** Replay/no-lookahead tests.
- **L477 — Phase 3 — Objective Market Features / 3J — PD Arrays:** Timestamp every state change.
- **L478 — Phase 3 — Objective Market Features / 3J — PD Arrays:** Feed PD-array context into DOL.
- **L480 — Phase 3 — Objective Market Features / 3J — PD Arrays:** Add supply/demand only when deterministically defined.
- **L481 — Phase 3 — Objective Market Features / 3J — PD Arrays:** Keep automated OB secondary until reliable.
- **L482 — Phase 3 — Objective Market Features / 3J — PD Arrays:** Tests.
- **L490 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Equal highs/lows.
- **L493 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Premium/discount midpoint.
- **L495 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Reaction count/recency.
- **L497 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Mitigation state.
- **L498 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** HTF alignment.
- **L499 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Preserve components separately.
- **L501 — Phase 3 — Objective Market Features / 3K — Support / Resistance Confluence Zones:** Unit + no-lookahead tests.
- **L507 — Phase 3 — Objective Market Features / 3L — Signal-to-Noise:** Completed-bar availability is protected.
- **L508 — Phase 3 — Objective Market Features / 3L — Signal-to-Noise:** Future-mutation tests exist.
- **L509 — Phase 3 — Objective Market Features / 3L — Signal-to-Noise:** Decide exact production role in morning confidence.
- **L518 — Phase 3 — Objective Market Features / 3M — Scorer Harmonization:** DOL contribution is supported.
- **L523 — Phase 3 — Objective Market Features / 3M — Scorer Harmonization:** Preserve explainable individual contributions.
- **L524 — Phase 3 — Objective Market Features / 3M — Scorer Harmonization:** Preserve conflict penalties.
- **L525 — Phase 3 — Objective Market Features / 3M — Scorer Harmonization:** Verify theoretical maximum remains 100 unless intentionally redesigned.
- **L526 — Phase 3 — Objective Market Features / 3M — Scorer Harmonization:** Delay calibration until the feature set is complete.
- **L530 — Phase 3 — Objective Market Features / Done when:** Every objective feature needed by market state exists.
- **L532 — Phase 3 — Objective Market Features / Done when:** No-lookahead tests are green.
- **L533 — Phase 3 — Objective Market Features / Done when:** Full suite is green.
- **L534 — Phase 3 — Objective Market Features / Done when:** Feature outputs are ready for stable serialization.
- **L535 — Phase 3 — Objective Market Features / Done when:** Push checkpoint and update this file.
- **L549 — Phase 4 — Production Displacement + Draw on Liquidity / DOL v1 — existing:** DOL is causal.
- **L1085 — Phase 12 — Formal Backtesting / Calibration / Existing infrastructure:** Barchart historical support exists.
- **L1087 — Phase 12 — Formal Backtesting / Calibration / Existing infrastructure:** Exit-model analysis tooling exists.

## Source module → direct-test inventory

| Module | Matching direct tests |
|---|---|
| `src/backtest.py` | `tests/test_backtest.py` |
| `src/bias.py` | `tests/test_bias.py` |
| `src/confluence_zones.py` | `tests/test_confluence_zones.py` |
| `src/data_clock.py` | `tests/test_data_clock.py` |
| `src/data_loader.py` | `tests/test_data_loader.py` |
| `src/dealing_range.py` | `tests/test_dealing_range.py` |
| `src/displacement.py` | `tests/test_displacement.py` |
| `src/dol.py` | `tests/test_dol.py` |
| `src/fvg.py` | `tests/test_fvg.py`, `tests/test_fvg_state.py`, `tests/test_fvg_timezone.py` |
| `src/fvg_state.py` | `tests/test_fvg_state.py` |
| `src/liquidity.py` | `tests/test_liquidity_registry.py` |
| `src/liquidity_registry.py` | `tests/test_liquidity_registry.py` |
| `src/pd_arrays.py` | `tests/test_pd_arrays.py` |
| `src/projectx_client.py` | `tests/test_projectx_client.py` |
| `src/resample.py` | `tests/test_resample_daily_session.py`, `tests/test_resample_short_timeframes.py`, `tests/test_resample_timeframe_visibility.py` |
| `src/rollover.py` | `tests/test_rollover.py`, `tests/test_rollover_pipeline.py` |
| `src/scorer.py` | `tests/test_scorer.py` |
| `src/scorer_harmonization.py` | **NONE FOUND BY NAME** |
| `src/sessions.py` | `tests/test_sessions.py`, `tests/test_sessions_contract.py` |
| `src/snr.py` | `tests/test_snr.py`, `tests/test_snr_production.py` |
| `src/structure.py` | `tests/test_structure.py`, `tests/test_structure_state.py` |
| `src/structure_state.py` | `tests/test_structure_state.py` |
| `src/swing_lifecycle.py` | `tests/test_swing_lifecycle.py` |
| `src/swings.py` | `tests/test_swings.py` |
| `src/validate_data.py` | `tests/test_validate_data.py` |
| `src/volume.py` | `tests/test_volume.py` |
| `src/vwap.py` | `tests/test_vwap.py` |

## Duplicate checklist text with conflicting status

- full suite is green
- previous close
- push checkpoint and update this file
- vwap

## Recent implementation commits

```text
ad3463b Record Phase 3 certification checkpoint
c656bfe Certify Phase 3 automated feature gates
39358da Complete Phase 3M scorer harmonization
9615413 Complete Phase 3L production SNR role
a46e38f Complete Phase 3K confluence zones
a4eced5 Complete Phase 3J PD array lifecycle
b3aad89 Complete Phase 3 structure and swing lifecycle
1a9663e Complete Phase 3F production FVG state
dcfbc86 Complete Phase 3E liquidity registry
75a50a8 Complete Phase 3A VWAP and 3B volume features
a0ca57d Complete Phase 3H displacement model
a1ab673 Add Phase 3 swing lifecycle features
d5f3545 Complete Phase 3G dealing range features
ec22d1c Complete Phase 3C hierarchical HTF bias
80f6e86 Complete Phase 2 data clock and session safety
```

## Interpretation rules

- `UNCHECKED_WITH_EVIDENCE` does **not** automatically mean complete; it means phases.md may be stale and the behavior should be reviewed.
- `CHECKED_WITH_EVIDENCE` proves only that expected artifacts exist; tests and semantics still matter.
- Manual/live/chart requirements should remain open until the specified real-world verification actually occurred.
- A green full suite is necessary but does not prove every roadmap requirement is implemented correctly.
