# NQ / MNQ Trading System — Phase Checklist

**Repository:** `jenozu/trade-alerts`  
**Branch:** `main`  
**Purpose:** Canonical implementation checklist for coordinating work across ChatGPT conversations, coding agents, and LLMs.  
**Last organized:** 2026-09-02

> Before doing any work, inspect the current repository and this checklist. Do not recreate working modules simply because an older roadmap lists them as future work.

## How to use this file

- `[x]` = completed and verified
- `[ ]` = not completed yet

A phase is only complete when its code exists, targeted tests pass, the full suite is green, required live/replay verification is complete, the work is committed/pushed, and this file is updated.

At the end of every coding session:

```text
1. Run targeted tests.
2. Run the full test suite.
3. Record the passing test count.
4. Commit/push the tested checkpoint.
5. Update phases.md.
6. Stop before starting the next major phase unless explicitly requested.
```

---

# Global rules — apply to every phase

## Architecture

- [x] Use one shared deterministic strategy engine for historical replay, premarket analysis, live alerts, and post-session evaluation.
- [x] Keep ProjectX/data ingestion separate from strategy calculations.
- [x] Python owns objective numeric calculations.
- [ ] Add LLM prose only after deterministic market state and trade planning are reliable.
- [x] System is analysis/alerts only.
- [x] No automated order placement.
- [x] No automated brokerage position management.

## No lookahead

- [x] Existing research features were built with causal/no-lookahead behavior in mind.
- [ ] Maintain one explicit `as_of` contract throughout the production pipeline.
- [ ] Preserve completed-bar semantics in both historical and live modes.
- [ ] Maintain future-mutation / append-invariance tests for every important feature.

## Existing modules that must be preserved

- [x] `src/data_loader.py`
- [x] `src/validate_data.py`
- [x] `src/resample.py`
- [x] `src/sessions.py`
- [x] `src/volume.py`
- [x] `src/snr.py` — **signal-to-noise**, not support/resistance
- [x] `src/swings.py`
- [x] `src/liquidity.py`
- [x] `src/fvg.py`
- [x] `src/structure.py`
- [x] `src/bias.py`
- [x] `src/dol.py`
- [x] `src/scorer.py`
- [x] `src/backtest.py`
- [x] `src/rollover.py`
- [x] `src/projectx_client.py`

## Important naming decision

- [x] Keep `src/snr.py` as signal-to-noise / market quality.
- [ ] Build support/resistance confluence separately, e.g. `src/confluence_zones.py` or `src/support_resistance.py`.
- [ ] Expose signal-to-noise and support/resistance as separate concepts in market state.

## Scoring

- [x] Preserve the interpretable internal 0–100 raw score.
- [ ] Later expose a report-friendly 0–10 confidence display if useful.
- [ ] Do not call the score a win probability until empirically calibrated.

## Git / multi-conversation workflow

- [x] GitHub `main` is implementation truth.
- [ ] Start every coding session with:

```bash
cd /docker/trade-alerts
source .venv/bin/activate
git pull --ff-only
git status
pytest -q
```

- [ ] Inspect every file before modifying it.
- [ ] Do not assume remembered code from another conversation is newer than GitHub.
- [ ] Update this checklist after each completed milestone.
- [ ] Keep secrets and market datasets out of Git.

---

# Current status snapshot

- [x] HTF bias exists and is integrated.
- [x] DOL v1 exists and is integrated.
- [x] Historical backtesting infrastructure exists.
- [x] Rollover/stitching infrastructure exists.
- [x] ProjectX reusable client exists.
- [x] ProjectX-specific test result reported: **21 passed**.
- [x] Full-suite result reported after ProjectX Phase 1: **180 passed**.
- [x] ProjectX collector checkpoint pushed: `950633e` — `checkpoint: projectx collector`.
- [x] Reproduce the current full-suite count on the VPS after the latest pull — **200 passed, 25 warnings** at `9e7262a851e9c7264c3e0a66277b9ad13df8eef9`.
- [x] Confirm the ProjectX collector succeeds on the VPS with `PROJECTX_LIVE=false`.

---

# Phase 0 — Baseline / Repository Audit

## Goal

Freeze a trustworthy baseline before continuing production work.

## Checklist

- [x] Existing `trade-alerts` repository identified.
- [x] Existing feature/research modules inspected during prior development.
- [x] Historical pipeline exists.
- [x] Backtest engine exists.
- [x] Rollover/stitching support exists.
- [x] HTF bias exists.
- [x] DOL exists.
- [x] ProjectX reusable client exists.
- [x] Run `git pull --ff-only` on VPS.
- [x] Confirm working tree is clean.
- [x] Run `pytest -q`.
- [x] Record current passing test count.
- [x] Record warnings separately from failures.
- [x] Confirm Python/venv versions.
- [x] Confirm data directories are writable.
- [x] Confirm `.env` is ignored by Git.
- [x] Confirm no credentials are committed.
- [x] Back up current `config/strategy.yaml` before major strategy changes.
- [x] Back up current `config/sessions.yaml` before session changes.

> **Phase 0 backup evidence:** Both configs are committed in `trade-brain/90-Sources/Config-Baselines/2026-09-03/` with a verified `SHA256SUMS` manifest and documented baseline convention. Source commit: `940bd823456a6c7f0ddf12ec72a16d24d7fdee01`; trade-brain commit: `3746f39e1e00f614a58db78196bc889de1c7b800`.

## Done when

- [x] Latest `main` is pulled.
- [x] Full suite is green.
- [x] Working tree is clean.
- [x] Configs are backed up.
- [x] Test count and commit are recorded.

**Latest verified full-suite count:** `200 passed, 25 warnings`
**Latest verified commit:** `9e7262a851e9c7264c3e0a66277b9ad13df8eef9`

---

# Phase 1 — ProjectX Collector

## Goal

Create one reusable, read-only ProjectX market-data layer that serves the morning system and existing historical utilities.

## Client

- [x] Create `src/projectx_client.py`.
- [x] Reuse the proven ProjectX/TopstepX auth flow.
- [x] Support `PROJECTX_USERNAME` / `PROJECTX_API_KEY`.
- [x] Preserve legacy `TOPSTEP_USERNAME` / `TOPSTEP_API_KEY`.
- [x] Authenticate.
- [x] Search/resolve contracts.
- [x] Retrieve bars.
- [x] Normalize timezone-aware OHLCV.
- [x] Normalize timestamps to UTC storage.
- [x] Detect malformed data.
- [x] Detect zero-bar responses.
- [x] Detect stale data.
- [x] Retry transient HTTP failures.
- [x] Respect request limits/chunking.
- [x] Use market-data endpoints only.

## Collector script

- [x] Create `scripts/collect_projectx.py`.
- [x] Save timestamped raw Parquet snapshots.
- [x] Save metadata snapshots.
- [x] Fail loudly on auth/data failure.
- [x] Verify script succeeds from VPS using the current ProjectX account environment (`PROJECTX_LIVE=false`).
- [x] Verify correct active contract is selected — **MNQU6 / CON.F.US.MNQ.U26**.
- [x] Verify intended NQ/MNQ symbol — **MNQ**.
- [x] Verify latest completed bar is fresh.
- [x] Verify saved Parquet loads successfully.
- [x] Verify metadata records contract/source/range accurately.
- [x] Verify no secret values appear in logs/output.
- [x] Verify stale/empty/error responses fail safely through collector validation/tests.

## Compatibility

- [x] Preserve `fetch_projectx_history.py`.
- [x] Route historical CLI through reusable client.
- [x] Preserve explicit historical contract workflows.

## Tests

- [x] Create `tests/test_projectx_client.py`.
- [x] ProjectX tests reported at 21 passing.
- [x] Full suite reported at 180 passing after Phase 1 code.

## Live verification command

```bash
python scripts/collect_projectx.py --days 3
```

## Done when

- [x] Code implemented.
- [x] Tests implemented.
- [x] Code pushed.
- [x] Live VPS/current-data pull verified.
- [x] Fresh snapshot + metadata verified.
- [x] **Phase 1 fully complete — verified 2026-09-02.**

---

# Phase 2 — Data Clock, Validation, Resampling, Sessions

## Goal

Make the data pipeline production-safe so 09:00, 09:25, post-open live analysis, and historical replay use exactly the information available at that time.

## Canonical data contract

- [x] `timestamp` is timezone-aware UTC storage.
- [x] `open`, `high`, `low`, `close`, `volume` exist.
- [x] Source/symbol/contract metadata can be preserved.
- [x] Define one explicit production `as_of` contract.
- [x] Ensure downstream production modules honor `as_of`.

## Validation

- [x] Required-column checks exist.
- [x] Timestamp checks exist.
- [x] OHLC consistency checks exist.
- [x] Duplicate/gap/outlier diagnostics exist.
- [x] Add/verify live freshness rules.
- [x] Distinguish warnings vs fatal errors for production analysis.
- [x] Add degraded-analysis status for incomplete but usable history.
- [x] Validate session coverage required by the morning engine.

## Resampling

Existing:

- [x] 1m
- [x] 5m
- [x] 15m
- [x] 30m
- [x] 1h
- [x] 4h
- [x] Daily research resampling exists

Add/verify:

- [x] 2m
- [x] 3m
- [x] Completed-bar visibility on every timeframe.
- [x] `available_at` semantics on every timeframe.
- [x] Session-aware Daily construction.
- [x] Daily does not accidentally use midnight UTC if futures trading date is intended.
- [x] Deterministic boundaries through DST.
- [x] Replay reproduces the same multi-timeframe bars as live mode.

## Sessions

- [x] Session engine exists.
- [x] ET conversion exists.
- [x] Prior-day/premarket/overnight/London logic exists in some form.
- [x] Treat `config/sessions.yaml` as authoritative.
- [x] Verify final London definition.
- [x] Add/verify explicit Asia session.
- [x] Calculate Asia High/Low.
- [x] Verify London High/Low.
- [x] Verify overnight High/Low.
- [x] Verify PMH/PML.
- [x] Ensure developing session levels never use future bars.
- [x] Ensure finalized levels only appear when available.
- [x] Verify session identities across midnight.
- [x] Verify ET DST transitions.

## Additional required levels

- [x] Previous close.
- [x] Prior-day midpoint / half-back.
- [x] Current week High/Low.
- [x] Cash open after 09:30.
- [x] OR5 High/Low.
- [x] OR15 High/Low.

## Replay/no-lookahead checkpoints

- [x] 08:00 ET snapshot.
- [x] 09:00 ET snapshot.
- [x] 09:25 ET snapshot.
- [x] 09:29 ET snapshot.
- [x] 09:35 ET snapshot.
- [x] 10:00 ET snapshot.
- [x] No future session extrema visible.
- [x] No incomplete HTF bar visible.
- [x] PMH/PML only developed through `as_of`.
- [x] OR levels do not appear early.

## Done when

- [x] 2m/3m are supported.
- [x] Daily/session resampling is correct.
- [x] Asia/London/overnight/premarket levels are reliable.
- [x] Prior/weekly/opening-range levels are reliable.
- [x] `as_of` behavior is deterministic.
- [x] Replay/no-lookahead tests are green.
- [x] Full suite is green.
- [x] Push checkpoint and update this file.

---

# Phase 3 — Objective Market Features

## Goal

Complete the deterministic facts required by market state before building narrative/reporting layers.

## 3A — VWAP

- [x] Create/verify `src/vwap.py`.
- [x] Use typical price `(high + low + close) / 3`.
- [x] Weight by volume.
- [x] Configure reset/session behavior.
- [x] Current VWAP.
- [x] Distance from VWAP.
- [x] Above/below VWAP.
- [x] Recent cross if useful.
- [x] Slope if useful.
- [x] Unit tests.
- [x] No-lookahead tests.

## 3B — Volume / RVOL

- [x] `src/volume.py` exists.
- [x] Rolling RVOL exists.
- [x] Time-of-day RVOL exists.
- [x] Current implementation is causal.
- [x] Expose 1m/5m current volume cleanly.
- [x] Expose rolling average/median.
- [x] Add volume percentile if useful.
- [x] Add breakout/rejection/pullback volume context.
- [x] Never mix NQ and MNQ volume baselines.
- [x] Verify DST/time-of-day behavior.

## 3C — HTF Bias

- [x] `src/bias.py` exists.
- [x] Bias is causal.
- [x] Completed HTF bars are respected.
- [x] Bias is integrated into scoring.
- [x] Bias tests exist.
- [x] Reconcile production HTF hierarchy with actual config.
- [x] Decide exact 1H/30m/15m vs 4H/Daily roles.
- [x] Fix session-aware Daily dependency if Daily remains an input.
- [x] Expose bias reasons/components.
- [x] Separate HTF/daily vs intraday bias for reporting.

## 3D — Swings

- [x] `src/swings.py` exists.
- [x] Internal/external swings exist.
- [x] Confirmation delay is causal.
- [x] Add timeframe metadata where needed.
- [x] Equal-high clustering.
- [x] Equal-low clustering.
- [x] Swing strength.
- [x] Swept state.
- [x] Broken-with-displacement state.
- [x] Protected/strong swing classification.
- [x] Weak-liquidity classification.
- [x] Record reason for protected/weak status.
- [x] Add no-lookahead regressions.

## 3E — Liquidity Registry

- [x] `src/liquidity.py` exists.
- [x] Buy-side/sell-side sweep detection exists.
- [x] Unswept liquidity distance exists.
- [x] PDH/PDL support exists.
- [x] PMH/PML support exists.
- [x] Overnight/London/swing support exists.
- [x] Add Asia H/L.
- [x] Add weekly H/L.
- [x] Add equal highs/lows.
- [x] Add explicit liquidity-pool registry/object model.
- [x] Add importance/components.
- [x] Track `untouched`.
- [x] Track `approached`.
- [x] Track `swept`.
- [x] Track `broken`.
- [x] Track `reclaimed`.
- [x] Track `invalidated`.
- [x] Associate pool with timeframe/session metadata.
- [x] Prevent same-price identity collisions across sessions.

## 3F — FVG / IFVG

- [x] `src/fvg.py` exists.
- [x] Correct three-candle definition exists.
- [x] Bullish/bearish FVG detection exists.
- [x] Lifecycle/retest logic exists.
- [x] Tests exist.
- [x] Expose clean active multi-timeframe FVG objects.
- [x] Track timeframe in production state.
- [x] ATR-relative size.
- [x] Mitigation percentage/full fill.
- [x] Invalidation.
- [x] Verify IFVG conversion state.
- [x] Associate important gaps with sweep/displacement/structure.
- [x] Nearest HTF FVG above/below.
- [x] Nearest 5m FVG above/below.
- [x] Add exact-output regression fixture.
- [x] Optimize FVG performance without behavior drift.

## 3G — Dealing Range / Premium-Discount

- [x] Create `src/dealing_range.py`.
- [x] Structural range high/low.
- [x] Equilibrium/midpoint.
- [x] Percentile within range.
- [x] Premium/discount/equilibrium classification.
- [x] Multiple relevant ranges/timeframes.
- [x] Avoid using premium/discount as a blind directional rule.
- [x] Unit + no-lookahead tests.

## 3H — Displacement

- [x] Existing structure code contains initial displacement logic.
- [x] Build dedicated explainable displacement component model.
- [x] Body / ATR.
- [x] Range / ATR.
- [x] Close location.
- [x] Consecutive directional candles.
- [x] Distance beyond broken structure.
- [x] RVOL/volume.
- [x] FVG generation.
- [x] Follow-through.
- [x] Preserve every raw component.
- [x] Combined score.
- [x] Configurable thresholds.
- [x] Provisional weak/moderate/strong categories.
- [x] Unit + causal tests.

## 3I — Structure

- [x] `src/structure.py` exists.
- [x] BOS/MSS/CHOCH-related logic exists.
- [x] Explicit wick-sweep vs body-close break distinction.
- [x] Explicit body-close vs displacement-break distinction.
- [x] Continuation-break state.
- [x] Failed-break state.
- [x] Reclaim state.
- [x] Integrate dedicated displacement score.
- [x] Expose broken level/timeframe/timestamp/confirmation.
- [x] Expose volume/displacement context.
- [x] Replay/no-lookahead tests.

## 3J — PD Arrays

- [ ] Create `src/pd_arrays.py`.
- [ ] Track bullish/bearish FVG respect/disrespect.
- [ ] Track IFVG respect/disrespect.
- [ ] Timestamp every state change.
- [ ] Feed PD-array context into DOL.
- [ ] Feed PD-array context into bias/scoring where appropriate.
- [ ] Add supply/demand only when deterministically defined.
- [ ] Keep automated OB secondary until reliable.
- [ ] Tests.

## 3K — Support / Resistance Confluence Zones

- [ ] Create separate module such as `src/confluence_zones.py`.
- [ ] Do **not** replace `src/snr.py`.
- [ ] HTF swing component.
- [ ] Prior-day/session-level components.
- [ ] Equal highs/lows.
- [ ] FVG boundaries.
- [ ] VWAP.
- [ ] Premium/discount midpoint.
- [ ] Volume reaction.
- [ ] Reaction count/recency.
- [ ] Displacement away from zone.
- [ ] Mitigation state.
- [ ] HTF alignment.
- [ ] Preserve components separately.
- [ ] Transparent combined zone score.
- [ ] Unit + no-lookahead tests.

## 3L — Signal-to-Noise

- [x] `src/snr.py` exists.
- [x] 1m/5m/15m signal-to-noise exists.
- [x] Completed-bar availability is protected.
- [x] Future-mutation tests exist.
- [ ] Decide exact production role in morning confidence.
- [ ] Expose raw SNR components to market state.
- [ ] Do not use SNR as a standalone direction predictor.

## 3M — Scorer Harmonization

- [x] `src/scorer.py` exists.
- [x] 0–100 deterministic score exists.
- [x] HTF bias contribution is active.
- [x] DOL contribution is supported.
- [ ] Integrate production VWAP.
- [ ] Integrate dealing range.
- [ ] Integrate support/resistance confluence.
- [ ] Integrate richer displacement.
- [ ] Preserve explainable individual contributions.
- [ ] Preserve conflict penalties.
- [ ] Verify theoretical maximum remains 100 unless intentionally redesigned.
- [ ] Delay calibration until the feature set is complete.

## Done when

- [ ] Every objective feature needed by market state exists.
- [ ] Important levels/features match several manually inspected historical chart days.
- [ ] No-lookahead tests are green.
- [ ] Full suite is green.
- [ ] Feature outputs are ready for stable serialization.
- [ ] Push checkpoint and update this file.

---

# Phase 4 — Production Displacement + Draw on Liquidity

## Goal

Reliably distinguish reversal vs continuation context and rank the market's most meaningful destinations.

## DOL v1 — existing

- [x] `src/dol.py` exists.
- [x] `tests/test_dol.py` exists.
- [x] DOL is causal.
- [x] DOL is integrated into `run_pipeline.py`.
- [x] `tests/test_pipeline_dol.py` exists.
- [x] Scorer can award DOL points.

## DOL v2 — production requirements

- [ ] Extend existing DOL; do not replace it.
- [ ] Rank multiple candidate targets.
- [ ] Produce **Primary DOL**.
- [ ] Produce **Alternate DOL**.
- [ ] Candidate PDH/PDL.
- [ ] Candidate PMH/PML.
- [ ] Candidate Asia H/L.
- [ ] Candidate London H/L.
- [ ] Candidate weekly H/L.
- [ ] Candidate equal highs/lows.
- [ ] Candidate external swings.
- [ ] Candidate important untested HTF FVGs when safely represented.
- [ ] Consider HTF structure/bias.
- [ ] Consider premium/discount.
- [ ] Consider protected/weak swings.
- [ ] Consider recent sweeps.
- [ ] Consider PD-array state.
- [ ] Consider displacement.
- [ ] Consider target distance.
- [ ] Consider obstacles/room-to-run.
- [ ] Preserve component scores/reasons.
- [ ] Preserve source/price/distance/confidence.
- [ ] Return neutral when evidence is insufficient/conflicting.
- [ ] Add future-mutation invariance tests.

## Sweep vs break classification

- [ ] Formalize reversal sequence.
- [ ] Formalize continuation sequence.
- [ ] Require displacement for valid structural break.
- [ ] Require full confirmation sequence before entry-valid state.

## Done when

- [ ] Sweep vs displacement break is reliable.
- [ ] DOL emits primary + alternate targets.
- [ ] DOL is explainable and causal.
- [ ] Replay/live behavior is consistent.
- [ ] Full suite is green.
- [ ] Push checkpoint and update this file.

---

# Phase 5 — Market State Engine

## Goal

Build one stable, timestamped deterministic snapshot containing every fact needed by the trade planner and report.

## Core module

- [ ] Create `src/market_state.py`.
- [ ] Define schema/version.
- [ ] Include `generated_at` and mandatory `as_of`.
- [ ] Include symbol/contract/latest price metadata.
- [ ] Include data-quality/freshness/session-coverage state.
- [ ] Include sessions/key levels/VWAP/timeframe summaries.
- [ ] Include HTF/daily and intraday bias.
- [ ] Include swings/liquidity/dealing ranges/premium-discount.
- [ ] Include PD arrays.
- [ ] Include FVG/IFVG.
- [ ] Include structure/displacement.
- [ ] Include volume/RVOL.
- [ ] Include signal-to-noise.
- [ ] Include support/resistance confluence zones.
- [ ] Include Primary/Alternate DOL.
- [ ] Include scores/components.
- [ ] Include news/event-risk field, even if MVP is manual/unavailable.
- [ ] Include trade-candidate section.

## Required levels

- [ ] PDH/PDL.
- [ ] Previous close.
- [ ] Prior-day half-back.
- [ ] PMH/PML.
- [ ] Asia High/Low.
- [ ] London High/Low.
- [ ] Overnight High/Low.
- [ ] Week High/Low.
- [ ] VWAP.
- [ ] Nearest important swing high/low.
- [ ] Nearest equal highs/lows.
- [ ] Important HTF FVG above/below.
- [ ] Important 5m FVG above/below.
- [ ] Important support/resistance zone.
- [ ] Cash open / OR5 / OR15 when available.

## Snapshot storage

- [ ] Create `data/state/`.
- [ ] Save timestamped snapshots, e.g. `YYYY-MM-DD_0900_market_state.json`.
- [ ] Save separate 09:25 snapshot.
- [ ] Maintain `latest.json` only as convenience copy/pointer.
- [ ] Never overwrite the only historical state.
- [ ] Include schema version and source snapshot references.

## Safe failure states

- [ ] `NO ANALYSIS — PROJECTX DATA UNAVAILABLE`.
- [ ] `NO ANALYSIS — STALE MARKET DATA`.
- [ ] `ANALYSIS DEGRADED — REQUIRED HISTORY INCOMPLETE`.
- [ ] Never silently substitute an old state for a fresh one.

## Tests

- [ ] `tests/test_market_state.py`.
- [ ] Schema test.
- [ ] `as_of` test.
- [ ] Storage test.
- [ ] Fatal/degraded data-quality tests.
- [ ] Historical prefix invariant with future bars appended.

## Done when

- [ ] One JSON contains every deterministic fact required for morning analysis.
- [ ] State is versioned and snapshot-safe.
- [ ] No-lookahead is proven.
- [ ] Full suite is green.
- [ ] Push checkpoint and update this file.

---

# Phase 6 — Trade Planner

## Goal

Convert deterministic market state into at most one preferred and one alternate trade hypothesis.

## Core

- [ ] Create `src/trade_planner.py`.
- [ ] Consume market state, not arbitrary raw bars.
- [ ] Produce `preferred`.
- [ ] Produce `alternate`.
- [ ] Support `NO TRADE`.

## Each candidate must include

- [ ] Direction.
- [ ] Setup family/subtype.
- [ ] Trigger level/zone.
- [ ] Entry zone.
- [ ] Structural invalidation.
- [ ] SL and risk distance.
- [ ] TP1/TP2/TP3/TP4.
- [ ] Reason/source for every target.
- [ ] Confirmation criteria.
- [ ] Invalidation criteria.
- [ ] Nearby obstacles.
- [ ] Distance to first obstacle/primary target.
- [ ] Reward/risk.
- [ ] Raw/component scores.
- [ ] DOL/bias alignment.

## Reversal planner

- [ ] Important liquidity.
- [ ] Sweep.
- [ ] Failure to accept beyond level.
- [ ] Opposite displacement.
- [ ] MSS/CHOCH.
- [ ] Retest.
- [ ] Entry confirmation.
- [ ] 09:00 scenario remains a hypothesis unless triggers already exist.

## Continuation planner

- [ ] Important level.
- [ ] Displacement break.
- [ ] Body close beyond level.
- [ ] Acceptance/follow-through.
- [ ] Pullback.
- [ ] Level/FVG hold.
- [ ] Micro BOS.
- [ ] Entry confirmation.

## Stop logic

- [ ] Find protected/invalidation structure.
- [ ] Add configurable buffer.
- [ ] Calculate actual risk.
- [ ] Prefer ~20–25 NQ points only when structure permits.
- [ ] Never force a stop inside structural invalidation.
- [ ] Reject setup when valid stop is materially too large.

## Target logic

- [ ] TP1 from nearest internal objective / ~1R where possible.
- [ ] TP2 from next meaningful objective.
- [ ] TP3 from Primary DOL / major objective.
- [ ] TP4 from external-liquidity runner when room exists.
- [ ] Record why each target was selected.

## Room-to-run

- [ ] Detect immediate opposing HTF obstacle.
- [ ] Detect insufficient room to TP1/primary target.
- [ ] Reject/downgrade poor asymmetric setups.
- [ ] Record rejection reason.

## Tests

- [ ] `tests/test_trade_planner.py`.
- [ ] Structural stop test.
- [ ] Oversized-risk rejection.
- [ ] Target-priority test.
- [ ] Room-to-run test.
- [ ] Preferred/alternate test.
- [ ] No-trade test.
- [ ] No-lookahead test.

## Done when

- [ ] Preferred/alternate are deterministic.
- [ ] Stops are structural.
- [ ] Targets are market-derived.
- [ ] Poor setups are rejected.
- [ ] Replay-safe.
- [ ] Full suite green.
- [ ] Push checkpoint and update this file.

---

# Phase 7 — Morning Output / Report

## Goal

Produce the complete 09:00 ET plan deterministically first, then optionally add LLM narrative.

## Deterministic outputs

- [ ] Structured morning alert JSON.
- [ ] Deterministic Markdown report.
- [ ] Save under `data/reports/`.
- [ ] Timestamp every report.
- [ ] Link report to source market-state snapshot.

## Required sections

- [ ] Current Market Context.
- [ ] Bias — HTF/daily + intraday + confidence/reasons.
- [ ] Primary DOL.
- [ ] Alternate DOL where useful.
- [ ] Key Liquidity & Structure Levels above/below price.
- [ ] Chart Markup.
- [ ] Scenario A — Preferred.
- [ ] Scenario B — Alternate.
- [ ] Trigger Zones.
- [ ] Best Play Right Now.

## Chart markup

- [ ] PDH/PDL.
- [ ] PMH/PML.
- [ ] Asia H/L.
- [ ] London H/L.
- [ ] Primary DOL.
- [ ] Important bullish/bearish FVG.
- [ ] Preferred long/short trigger.
- [ ] No-trade zone.
- [ ] Entry/SL/TP1–TP4.

## Behavior

- [ ] 09:00 report is explicitly a hypothesis/plan.
- [ ] Do not mark a setup confirmed unless deterministic state confirms it.
- [ ] Use `NO TRADE` when appropriate.
- [ ] Use `NO ANALYSIS` on fatal data problems.
- [ ] Never invent/recalculate deterministic levels in prose.

## Optional LLM layer

- [ ] Create `src/report_generator.py` only after deterministic output is reliable.
- [ ] Version-control prompt files.
- [ ] Send market state rather than raw 10k bars.
- [ ] Explicitly forbid invented/altered levels.
- [ ] Preserve deterministic JSON if LLM generation fails.

## Done when

- [ ] Deterministic report matches the required format.
- [ ] Chart markup is complete.
- [ ] Preferred/alternate scenarios are clear.
- [ ] LLM is optional rather than required for calculations.
- [ ] Full suite green.
- [ ] Push checkpoint and update this file.

---

# Phase 8 — 09:25 Premarket Refresh

## Goal

Update the 09:00 thesis using only information available by approximately 09:25 ET.

## Checklist

- [ ] Pull fresh ProjectX bars.
- [ ] Validate freshness.
- [ ] Save new raw snapshot.
- [ ] Rebuild market state with 09:25 `as_of`.
- [ ] Save separate 09:25 state.
- [ ] Recalculate PMH/PML, overnight, London, sweeps, displacement, structure, FVG/IFVG, DOL, bias, scores, planner candidates.
- [ ] Compare 09:00 vs 09:25.
- [ ] Classify `UNCHANGED`.
- [ ] Classify `STRENGTHENED`.
- [ ] Classify `WEAKENED`.
- [ ] Classify `FLIPPED`.
- [ ] Explain level/sweep/structure/DOL/bias/entry/invalidation/target changes.

## Tests

- [ ] Identical snapshots -> UNCHANGED.
- [ ] Added supportive evidence -> STRENGTHENED.
- [ ] Lost confluence -> WEAKENED.
- [ ] Directional reversal -> FLIPPED.
- [ ] No 09:30+ information in 09:25 state.

## Done when

- [ ] Both snapshots are preserved independently.
- [ ] Comparison is deterministic and traceable.
- [ ] Full suite green.
- [ ] Push checkpoint and update this file.

---

# Phase 9 — Live Setup State Machines

## Goal

Monitor 09:30–10:30 ET using deterministic setup-state machines instead of repeated vague AI analysis.

## Live loop

- [ ] Poll roughly once per minute.
- [ ] Use completed bars only.
- [ ] Validate each update and detect stale feed.
- [ ] Preserve state between iterations/restarts where needed.
- [ ] End standard monitoring at 10:30 ET.

## Reversal states

- [ ] `ARMED`
- [ ] `LIQUIDITY_REACHED`
- [ ] `SWEEP_CONFIRMED`
- [ ] `DISPLACEMENT_CONFIRMED`
- [ ] `MSS_CONFIRMED`
- [ ] `WAIT_RETEST`
- [ ] `RETEST_HOLDS`
- [ ] `ENTRY_VALID`
- [ ] `INVALIDATED`

## Continuation states

- [ ] `ARMED`
- [ ] `LEVEL_REACHED`
- [ ] `DISPLACEMENT_BREAK`
- [ ] `ACCEPTANCE`
- [ ] `WAIT_RETEST`
- [ ] `RETEST_HOLDS`
- [ ] `MICRO_BOS`
- [ ] `ENTRY_VALID`
- [ ] `INVALIDATED`

## Alerts

- [ ] PREMARKET PLAN READY.
- [ ] BIAS CHANGED.
- [ ] TRIGGER ZONE REACHED.
- [ ] LIQUIDITY SWEPT.
- [ ] DISPLACEMENT CONFIRMED.
- [ ] MSS/CHOCH CONFIRMED.
- [ ] RETEST IN PROGRESS.
- [ ] ENTRY VALID.
- [ ] SETUP INVALIDATED.
- [ ] TP1/TP2/TP3/TP4 HIT.

## Deduplication

- [ ] Persist scenario ID.
- [ ] Persist last state/alert time.
- [ ] Alert only on meaningful state change.
- [ ] Do not repeat the same alert every minute.

## Replay tests

- [ ] Reversal sequence replay.
- [ ] Continuation sequence replay.
- [ ] Invalidation replay.
- [ ] No-lookahead transition test.
- [ ] No duplicate-alert test.
- [ ] Restart/recovery test.

## Done when

- [ ] Both setup families work deterministically.
- [ ] Alerts occur only on meaningful transitions.
- [ ] Replay/live logic is shared.
- [ ] Full suite green.
- [ ] Push checkpoint and update this file.

---

# Phase 10 — VPS Orchestration, Health, Logging, Scheduling

## Goal

Run the complete morning workflow reliably without manual intervention.

## Health check

- [ ] Create `scripts/healthcheck.py`.
- [ ] Check credentials/auth.
- [ ] Check current contract.
- [ ] Check data directory write access.
- [ ] Check latest-bar freshness.
- [ ] Check required modules/config files.
- [ ] Run lightweight test subset if appropriate.
- [ ] Exit non-zero on critical failure.

## Logging

- [ ] Structured logs under `data/logs/`.
- [ ] Log auth success/failure without secrets.
- [ ] Log requests, contract, bar count, latest timestamp, validation, state-build duration, scenario scores, reports, alerts, failures.
- [ ] Never log passwords/API keys.

## Orchestrator

- [ ] Create one orchestrator if practical.
- [ ] Premarket mode.
- [ ] Refresh mode.
- [ ] Live-monitor mode.
- [ ] Minimize duplicated code.

## Schedule

- [ ] 08:55 ET — health check.
- [ ] 08:58 ET — ProjectX collection.
- [ ] 09:00 ET — state + morning plan.
- [ ] 09:25 ET — refresh + thesis comparison.
- [ ] 09:29 ET — live monitor armed.
- [ ] 09:30–10:30 ET — monitoring.
- [ ] 10:30 ET — close monitor + save recap.

## VPS scheduling

- [ ] Check `timedatectl`.
- [ ] Choose systemd timers vs cron.
- [ ] Use ET-aware scheduling and automatic EST/EDT handling.
- [ ] Verify each job manually first.
- [ ] Verify jobs survive VPS reboot.
- [ ] Verify logs prove execution.

## Done when

- [ ] Full weekday workflow runs automatically.
- [ ] Logs provide audit trail.
- [ ] Failure handling is safe.
- [ ] Services survive restart.
- [ ] Push checkpoint and update this file.

---

# Phase 11 — Shadow Mode

## Goal

Run the finished system without relying on it for live entries long enough to validate reliability and collect calibration data.

## Minimum sample

- [ ] At least 10 trading sessions.
- [ ] Prefer 20+ before aggressive tuning.

## Save every day

- [ ] 09:00 state + plan.
- [ ] 09:25 state + update.
- [ ] Every live state transition.
- [ ] Entry-valid and invalidation events.
- [ ] TP1–TP4 outcomes.
- [ ] Session high/low.
- [ ] MFE/MAE.
- [ ] Final scenario outcome.

## Daily evaluation

- [ ] Preferred direction/setup.
- [ ] Alternate setup.
- [ ] Setup confirmed / entry triggered.
- [ ] SL / TP results.
- [ ] MFE/MAE.
- [ ] Bias correctness.
- [ ] DOL result.
- [ ] Notes.

## Human comparison

- [ ] Compare automated state to manual chart review.
- [ ] Compare levels to TradingView/Topstep charts.
- [ ] Separate implementation bugs from losing trades.
- [ ] Do not change strategy after every losing day.

## Done when

- [ ] Minimum shadow sample collected.
- [ ] No critical calculation errors remain.
- [ ] Production timing is reliable.
- [ ] Records are complete enough for calibration.
- [ ] Update this file with observed issues.

---

# Phase 12 — Formal Backtesting / Calibration

## Goal

Use the existing historical backtester plus shadow-mode results to calibrate thresholds without overfitting.

## Existing infrastructure

- [x] `src/backtest.py` exists.
- [x] `run_pipeline.py` exists.
- [x] `src/rollover.py` exists.
- [x] `run_rollover_pipeline.py` exists.
- [x] `stitch_projectx_history.py` exists.
- [x] Barchart historical support exists.
- [x] ProjectX historical support exists.
- [x] Exit-model analysis tooling exists.
- [ ] Continue using these tools during earlier phases for replay/regression.

## Historical data discipline

- [ ] Use explicit quarterly contracts where required.
- [ ] Validate rollover boundaries.
- [ ] Do not assume TopstepX auto-roll chart behavior equals ProjectX historical API behavior.
- [ ] Keep NQ and MNQ volume histories separate.
- [ ] Preserve source/contract metadata.
- [ ] Preserve exact datasets/snapshots used for results.

## Metrics

- [ ] Bias accuracy.
- [ ] Preferred-scenario accuracy.
- [ ] Trigger precision.
- [ ] Win rate.
- [ ] Average/median R.
- [ ] Expectancy / profit factor.
- [ ] TP1–TP4 hit rates.
- [ ] Stop/no-trade rates.
- [ ] MFE/MAE.
- [ ] False sweep/breakout rates.
- [ ] Performance by setup, score band, DOL, session context, direction, and volatility regime.

## Parameters to calibrate

- [ ] Displacement thresholds.
- [ ] Signal-to-noise thresholds/weights.
- [ ] Support/resistance confluence weights.
- [ ] Scorer component weights.
- [ ] Confidence bands.
- [ ] DOL thresholds/weights.
- [ ] Swing parameters.
- [ ] FVG significance.
- [ ] Volume/RVOL thresholds.
- [ ] Stop buffers.
- [ ] Room-to-run filters.
- [ ] Exit model.
- [ ] Target priorities.

## Calibration rules

- [ ] Do not optimize solely for maximum historical profit.
- [ ] Prefer stable parameters across regimes.
- [ ] Use walk-forward/out-of-sample evaluation.
- [ ] Keep tuning/evaluation periods distinct.
- [ ] Compare historical results to shadow-mode observations.
- [ ] Higher score bands should outperform lower bands over meaningful samples.
- [ ] Do not call score a probability until calibrated.
- [ ] Preserve old configs/results for reproducibility.

## FVG performance optimization

- [ ] Benchmark current FVG stage.
- [ ] Create exact-output regression fixture.
- [ ] Optimize implementation.
- [ ] Prove output equivalence.
- [ ] Re-run full suite.
- [ ] Benchmark improved runtime.

## Done when

- [ ] Model evaluated over sufficient historical + shadow data.
- [ ] Score bands show meaningful separation.
- [ ] Parameters are stable out of sample.
- [ ] Production config is versioned.
- [ ] Baseline metrics are stored.
- [ ] Push checkpoint and update this file.

---

# Production readiness checklist

- [ ] ProjectX live collection reliable.
- [ ] Data freshness enforced.
- [ ] Session/`as_of` logic causal.
- [ ] Required multi-timeframe data reliable.
- [ ] Required session levels reliable.
- [ ] VWAP reliable.
- [ ] HTF bias reliable.
- [ ] Volume/RVOL reliable.
- [ ] Swings/equal highs-lows reliable.
- [ ] Protected/weak swings reliable.
- [ ] Liquidity registry reliable.
- [ ] FVG/IFVG state reliable.
- [ ] Displacement explainable.
- [ ] Structure distinguishes sweeps vs valid breaks.
- [ ] Premium/discount reliable.
- [ ] PD arrays tracked.
- [ ] Signal-to-noise available.
- [ ] Support/resistance confluence separately available.
- [ ] Primary + Alternate DOL available.
- [ ] Market-state snapshots stable.
- [ ] Trade planner produces preferred/alternate scenarios.
- [ ] Stops use structural invalidation.
- [ ] TP1–TP4 map to real objectives.
- [ ] 09:00 report complete.
- [ ] 09:25 comparison works.
- [ ] Reversal/continuation live state machines work.
- [ ] Alerts deduplicated.
- [ ] VPS scheduling reliable.
- [ ] Failure handling safe.
- [ ] Shadow mode completed.
- [ ] Calibration completed.
- [ ] No component submits brokerage orders.

---

# Daily production target

```text
08:55 ET  Health check
08:58 ET  ProjectX collection
09:00 ET  Deterministic market state + premarket plan + chart markup
09:25 ET  Fresh collection + state refresh + thesis classification
09:29 ET  Live state machines armed
09:30–10:30 ET  Deterministic setup monitoring + state-change alerts
10:30 ET  Monitoring ends + session evaluation saved
```

---

# Instructions to any future LLM / coding agent

Before doing anything:

- [ ] Read `phases.md`.
- [ ] Inspect GitHub `main`.
- [ ] Run the current test suite.
- [ ] Identify the first unchecked item in the active phase.
- [ ] Inspect existing implementation before creating/replacing anything.
- [ ] Preserve tested modules.
- [ ] Make only the changes required for the current milestone.
- [ ] Add/update tests.
- [ ] Run targeted tests.
- [ ] Run full tests.
- [ ] Commit/push the tested checkpoint.
- [ ] Update `phases.md`.
- [ ] Stop and report before starting the next major phase.

Never:

- [ ] Rebuild `bias.py` from scratch without a verified defect.
- [ ] Rebuild `dol.py` from scratch without a verified defect.
- [ ] Replace `snr.py` with support/resistance logic.
- [ ] Duplicate strategy logic for live mode.
- [ ] Let an LLM invent numeric price levels.
- [ ] Use future bars in historical replay.
- [ ] Commit credentials.
- [ ] Auto-place trades.
- [ ] Aggressively tune parameters before sufficient data exists.

---

# Current next action

```bash
cd /docker/trade-alerts
source .venv/bin/activate
git pull --ff-only
git status
pytest -q

python scripts/collect_projectx.py --days 3
```

Then:

- [ ] Record the full test count.
- [ ] Confirm live ProjectX pull.
- [ ] Confirm current contract.
- [ ] Confirm fresh latest bar.
- [ ] Confirm timestamped raw Parquet.
- [ ] Confirm metadata snapshot.
- [ ] Mark Phase 1 complete.
- [ ] Begin Phase 2.
