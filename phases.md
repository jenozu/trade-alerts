# NQ / MNQ Trading System — Phase Checklist

**Repository:** `jenozu/trade-alerts`  
**Branch:** `main`  
**Purpose:** Canonical implementation checklist for coordinating work across ChatGPT conversations, coding agents, and LLMs.  
**Last organized:** 2026-09-04

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

- [x] Create `src/pd_arrays.py`.
- [x] Track bullish/bearish FVG respect/disrespect.
- [x] Track IFVG respect/disrespect.
- [x] Timestamp every state change.
- [x] Feed PD-array context into DOL.
- [x] Feed PD-array context into bias/scoring where appropriate.
- [x] Add supply/demand only when deterministically defined.
- [x] Keep automated OB secondary until reliable.
- [x] Tests.

## 3K — Support / Resistance Confluence Zones

- [x] Create separate module such as `src/confluence_zones.py`.
- [x] Do **not** replace `src/snr.py`.
- [x] HTF swing component.
- [x] Prior-day/session-level components.
- [x] Equal highs/lows.
- [x] FVG boundaries.
- [x] VWAP.
- [x] Premium/discount midpoint.
- [x] Volume reaction.
- [x] Reaction count/recency.
- [x] Displacement away from zone.
- [x] Mitigation state.
- [x] HTF alignment.
- [x] Preserve components separately.
- [x] Transparent combined zone score.
- [x] Unit + no-lookahead tests.

## 3L — Signal-to-Noise

- [x] `src/snr.py` exists.
- [x] 1m/5m/15m signal-to-noise exists.
- [x] Completed-bar availability is protected.
- [x] Future-mutation tests exist.
- [x] Decide exact production role in morning confidence.
- [x] Expose raw SNR components to market state.
- [x] Do not use SNR as a standalone direction predictor.

## 3M — Scorer Harmonization

- [x] `src/scorer.py` exists.
- [x] 0–100 deterministic score exists.
- [x] HTF bias contribution is active.
- [x] DOL contribution is supported.
- [x] Integrate production VWAP.
- [x] Integrate dealing range.
- [x] Integrate support/resistance confluence.
- [x] Integrate richer displacement.
- [x] Preserve explainable individual contributions.
- [x] Preserve conflict penalties.
- [x] Verify theoretical maximum remains 100 unless intentionally redesigned.
- [x] Delay calibration until the feature set is complete.

## Done when

- [x] Every objective feature needed by market state exists.
- [x] Important levels/features match several manually inspected historical chart days.

> **Manual historical-chart validation:** PASS — 2026-03-31 (volatile), 2026-04-14 (trend), and 2026-05-15 (chop) manually inspected against historical charts. See `docs/PHASE3_MANUAL_CHART_VALIDATION.md`.
- [x] No-lookahead tests are green.
- [x] Full suite is green.
- [x] Feature outputs are ready for stable serialization.
- [x] Push checkpoint and update this file.

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

- [x] Extend existing DOL; do not replace it.
- [x] Rank multiple candidate targets.
- [x] Produce **Primary DOL**.
- [x] Produce **Alternate DOL**.
- [x] Candidate PDH/PDL.
- [x] Candidate PMH/PML.
- [x] Candidate Asia H/L.
- [x] Candidate London H/L.
- [x] Candidate weekly H/L.
- [x] Candidate equal highs/lows.
- [x] Candidate external swings.
- [x] Candidate important untested HTF FVGs when safely represented.
- [x] Consider HTF structure/bias.
- [x] Consider premium/discount.
- [x] Consider protected/weak swings.
- [x] Consider recent sweeps.
- [x] Consider PD-array state.
- [x] Consider displacement.
- [x] Consider target distance.
- [x] Consider obstacles/room-to-run.
- [x] Preserve component scores/reasons.
- [x] Preserve source/price/distance/confidence.
- [x] Return neutral when evidence is insufficient/conflicting.
- [x] Add future-mutation invariance tests.

## Sweep vs break classification

- [x] Formalize reversal sequence.
- [x] Formalize continuation sequence.
- [x] Require displacement for valid structural break.
- [x] Require full confirmation sequence before entry-valid state.

## Done when

- [x] Sweep vs displacement break is reliable.
- [x] DOL emits primary + alternate targets.
- [x] DOL is explainable and causal.
- [x] Replay/live behavior is consistent.
- [x] Full suite is green.
- [x] Push checkpoint and update this file.

> **Replay/live parity evidence:** `tests/test_replay_parity.py::test_phase4_replay_matches_live_completed_prefix_at_as_of` runs the shared production structure/sequence and DOL logic on both an explicit-`as_of` completed prefix and a causally processed full replay. It verifies identical Phase 4 outputs, hides an explicitly incomplete bar, and proves hostile future sweep/reversal bars cannot rewrite the visible result. Verified with the full suite at **430 passed, 263 warnings** on 2026-09-04.

---

# Phase 5 — Market State Engine

## Goal

Build one stable, timestamped deterministic snapshot containing every fact needed by the trade planner and report.

## Core module

- [x] Create `src/market_state.py`.
- [x] Define schema/version.
- [x] Include `generated_at` and mandatory `as_of`.
- [x] Include symbol/contract/latest price metadata.
- [x] Include data-quality/freshness/session-coverage state.
- [x] Include sessions/key levels/VWAP/timeframe summaries.
- [x] Include HTF/daily and intraday bias.
- [x] Include swings/liquidity/dealing ranges/premium-discount.
- [x] Include PD arrays.
- [x] Include FVG/IFVG.
- [x] Include structure/displacement.
- [x] Include volume/RVOL.
- [x] Include signal-to-noise.
- [x] Include support/resistance confluence zones.
- [x] Include Primary/Alternate DOL.
- [x] Include scores/components.
- [x] Include news/event-risk field, even if MVP is manual/unavailable.
- [x] Include trade-candidate section.

## Required levels

- [x] PDH/PDL.
- [x] Previous close.
- [x] Prior-day half-back.
- [x] PMH/PML.
- [x] Asia High/Low.
- [x] London High/Low.
- [x] Overnight High/Low.
- [x] Week High/Low.
- [x] VWAP.
- [x] Nearest important swing high/low.
- [x] Nearest equal highs/lows.
- [x] Important HTF FVG above/below.
- [x] Important 5m FVG above/below.
- [x] Important support/resistance zone.
- [x] Cash open / OR5 / OR15 when available.

## Snapshot storage

- [x] Create `data/state/`.
- [x] Save timestamped snapshots, e.g. `YYYY-MM-DD_0900_market_state.json`.
- [x] Save separate 09:25 snapshot.
- [x] Maintain `latest.json` only as convenience copy/pointer.
- [x] Never overwrite the only historical state.
- [x] Include schema version and source snapshot references.

## Safe failure states

- [x] `NO ANALYSIS — PROJECTX DATA UNAVAILABLE`.
- [x] `NO ANALYSIS — STALE MARKET DATA`.
- [x] `ANALYSIS DEGRADED — REQUIRED HISTORY INCOMPLETE`.
- [x] Never silently substitute an old state for a fresh one.

## Tests

- [x] `tests/test_market_state.py`.
- [x] Schema test.
- [x] `as_of` test.
- [x] Storage test.
- [x] Fatal/degraded data-quality tests.
- [x] Historical prefix invariant with future bars appended.

## Done when

- [x] One JSON contains every deterministic fact required for morning analysis.
- [x] State is versioned and snapshot-safe.
- [x] No-lookahead is proven.
- [x] Full suite is green.
- [x] Push checkpoint and update this file.

> **Market-state evidence:** `src/market_state.py` builds the versioned, JSON-safe snapshot from the shared enriched dataframe after applying the canonical completed-bar `as_of` filter. `run_pipeline.py` invokes it after scoring and before backtesting. `tests/test_market_state.py` covers the schema and required levels, explicit incomplete-bar visibility, collector-shaped stale state, unavailable/degraded states, immutable 09:00/09:25 snapshots plus `latest.json`, and hostile-future append invariance. Verified with the focused Phase 2–5 dependency suite at **94 passed, 80 warnings** and the full suite at **437 passed, 281 warnings** on 2026-09-04.

---

# Phase 6 — Trade Planner

## Goal

Convert deterministic market state into at most one preferred and one alternate trade hypothesis.

## Core

- [x] Create `src/trade_planner.py`.
- [x] Consume market state, not arbitrary raw bars.
- [x] Produce `preferred`.
- [x] Produce `alternate`.
- [x] Support `NO TRADE`.

## Each candidate must include

- [x] Direction.
- [x] Setup family/subtype.
- [x] Trigger level/zone.
- [x] Entry zone.
- [x] Structural invalidation.
- [x] SL and risk distance.
- [x] TP1/TP2/TP3/TP4.
- [x] Reason/source for every target.
- [x] Confirmation criteria.
- [x] Invalidation criteria.
- [x] Nearby obstacles.
- [x] Distance to first obstacle/primary target.
- [x] Reward/risk.
- [x] Raw/component scores.
- [x] DOL/bias alignment.

## Reversal planner

- [x] Important liquidity.
- [x] Sweep.
- [x] Failure to accept beyond level.
- [x] Opposite displacement.
- [x] MSS/CHOCH.
- [x] Retest.
- [x] Entry confirmation.
- [x] 09:00 scenario remains a hypothesis unless triggers already exist.

## Continuation planner

- [x] Important level.
- [x] Displacement break.
- [x] Body close beyond level.
- [x] Acceptance/follow-through.
- [x] Pullback.
- [x] Level/FVG hold.
- [x] Micro BOS.
- [x] Entry confirmation.

## Stop logic

- [x] Find protected/invalidation structure.
- [x] Add configurable buffer.
- [x] Calculate actual risk.
- [x] Prefer ~20–25 NQ points only when structure permits.
- [x] Never force a stop inside structural invalidation.
- [x] Reject setup when valid stop is materially too large.

## Target logic

- [x] TP1 from nearest internal objective / ~1R where possible.
- [x] TP2 from next meaningful objective.
- [x] TP3 from Primary DOL / major objective.
- [x] TP4 from external-liquidity runner when room exists.
- [x] Record why each target was selected.

## Room-to-run

- [x] Detect immediate opposing HTF obstacle.
- [x] Detect insufficient room to TP1/primary target.
- [x] Reject/downgrade poor asymmetric setups.
- [x] Record rejection reason.

## Tests

- [x] `tests/test_trade_planner.py`.
- [x] Structural stop test.
- [x] Oversized-risk rejection.
- [x] Target-priority test.
- [x] Room-to-run test.
- [x] Preferred/alternate test.
- [x] No-trade test.
- [x] No-lookahead test.

## Done when

- [x] Preferred/alternate are deterministic.
- [x] Stops are structural.
- [x] Targets are market-derived.
- [x] Poor setups are rejected.
- [x] Replay-safe.
- [x] Full suite green.
- [x] Push checkpoint and update this file.

> **Trade-planner evidence:** `src/trade_planner.py` consumes only the completed-bar market-state mapping and preserves the Phase 4 reversal/continuation sequence flags. It applies the configured structural buffer without forcing a 20–25 point stop, derives TP1–TP4 from state objectives and ranked DOL, and records all rejection/downgrade evidence. `tests/test_trade_planner.py` covers structural stops, oversized-risk and insufficient-room rejection, target priority, preferred/alternate ordering, `NO TRADE`, reversal confirmation, raw-data refusal, pipeline placement, and future-payload invariance. Verified with the focused dependency suite at **72 passed, 74 warnings** on 2026-09-04.

---

# Phase 7 — Morning Output / Report

## Goal

 Produce the complete 09:00 ET plan deterministically first, then optionally add LLM narrative.

Verified 2026-09-04: `src/report_generator.py` renders JSON/Markdown exclusively
from immutable market-state and trade-plan payloads; its optional narrative boundary
cannot modify or replace that deterministic output. Focused report/state/planner suite:
20 passed, 23 warnings.

## Deterministic outputs

- [x] Structured morning alert JSON.
- [x] Deterministic Markdown report.
- [x] Save under `data/reports/`.
- [x] Timestamp every report.
- [x] Link report to source market-state snapshot.

## Required sections

- [x] Current Market Context.
- [x] Bias — HTF/daily + intraday + confidence/reasons.
- [x] Primary DOL.
- [x] Alternate DOL where useful.
- [x] Key Liquidity & Structure Levels above/below price.
- [x] Chart Markup.
- [x] Scenario A — Preferred.
- [x] Scenario B — Alternate.
- [x] Trigger Zones.
- [x] Best Play Right Now.

## Chart markup

- [x] PDH/PDL.
- [x] PMH/PML.
- [x] Asia H/L.
- [x] London H/L.
- [x] Primary DOL.
- [x] Important bullish/bearish FVG.
- [x] Preferred long/short trigger.
- [x] No-trade zone.
- [x] Entry/SL/TP1–TP4.

## Behavior

- [x] 09:00 report is explicitly a hypothesis/plan.
- [x] Do not mark a setup confirmed unless deterministic state confirms it.
- [x] Use `NO TRADE` when appropriate.
- [x] Use `NO ANALYSIS` on fatal data problems.
- [x] Never invent/recalculate deterministic levels in prose.

## Optional LLM layer

- [x] Create `src/report_generator.py` only after deterministic output is reliable.
- [x] Version-control prompt files.
- [x] Send market state rather than raw 10k bars.
- [x] Explicitly forbid invented/altered levels.
- [x] Preserve deterministic JSON if LLM generation fails.

## Done when

- [x] Deterministic report matches the required format.
- [x] Chart markup is complete.
- [x] Preferred/alternate scenarios are clear.
- [x] LLM is optional rather than required for calculations.
- [x] Full suite green.
- [x] Push checkpoint and update this file.

---

# Phase 8 — 09:25 Premarket Refresh

## Goal

Update the 09:00 thesis using only information available by approximately 09:25 ET.

Verified 2026-09-04: focused Phase 8 suite 4 passed; full suite 454 passed,
281 warnings. The refresh enforces an explicit 09:25 ET `as_of` guard, preserves
separate 09:00/09:25 snapshots, deterministically classifies `UNCHANGED`,
`STRENGTHENED`, `WEAKENED`, and `FLIPPED`, and records traceable before/after/reason
changes. The canonical completed-bar filter plus the 09:25 guard prevents 09:30+
leakage.

## Checklist

- [x] Pull fresh ProjectX bars.
- [x] Validate freshness.
- [x] Save new raw snapshot.
- [x] Rebuild market state with 09:25 `as_of`.
- [x] Save separate 09:25 state.
- [x] Recalculate PMH/PML, overnight, London, sweeps, displacement, structure, FVG/IFVG, DOL, bias, scores, planner candidates.
- [x] Compare 09:00 vs 09:25.
- [x] Classify `UNCHANGED`.
- [x] Classify `STRENGTHENED`.
- [x] Classify `WEAKENED`.
- [x] Classify `FLIPPED`.
- [x] Explain level/sweep/structure/DOL/bias/entry/invalidation/target changes.

## Tests

- [x] Identical snapshots -> UNCHANGED.
- [x] Added supportive evidence -> STRENGTHENED.
- [x] Lost confluence -> WEAKENED.
- [x] Directional reversal -> FLIPPED.
- [x] No 09:30+ information in 09:25 state.

## Done when

- [x] Both snapshots are preserved independently.
- [x] Comparison is deterministic and traceable.
- [x] Full suite green.
- [x] Push checkpoint and update this file.

---

# Phase 9 — Live Setup State Machines

## Goal

Monitor 09:30–10:30 ET using deterministic setup-state machines instead of repeated vague AI analysis.

Verified 2026-09-04: `src/live_setup_state.py` is the single transition core
used by replay and live adapters. The dedicated Phase 9 suite passes 13 tests;
the focused structure/state/planner/refresh dependency suite passes 59 tests,
35 warnings; the full suite passes 467 tests, 281 warnings. Updates are
completed-bar/as-of gated, advance at most one state
per observation, persist JSON-safe state and alert keys, and stop at 10:30 ET.
ProjectX scheduling and Telegram transport remain Phase 10 deployment concerns,
not alternate strategy paths.

## Live loop

- [x] Poll roughly once per minute.
- [x] Use completed bars only.
- [x] Validate each update and detect stale feed.
- [x] Preserve state between iterations/restarts where needed.
- [x] End standard monitoring at 10:30 ET.

## Reversal states

- [x] `ARMED`
- [x] `LIQUIDITY_REACHED`
- [x] `SWEEP_CONFIRMED`
- [x] `DISPLACEMENT_CONFIRMED`
- [x] `MSS_CONFIRMED`
- [x] `WAIT_RETEST`
- [x] `RETEST_HOLDS`
- [x] `ENTRY_VALID`
- [x] `INVALIDATED`

## Continuation states

- [x] `ARMED`
- [x] `LEVEL_REACHED`
- [x] `DISPLACEMENT_BREAK`
- [x] `ACCEPTANCE`
- [x] `WAIT_RETEST`
- [x] `RETEST_HOLDS`
- [x] `MICRO_BOS`
- [x] `ENTRY_VALID`
- [x] `INVALIDATED`

## Alerts

- [x] PREMARKET PLAN READY.
- [x] BIAS CHANGED.
- [x] TRIGGER ZONE REACHED.
- [x] LIQUIDITY SWEPT.
- [x] DISPLACEMENT CONFIRMED.
- [x] MSS/CHOCH CONFIRMED.
- [x] RETEST IN PROGRESS.
- [x] ENTRY VALID.
- [x] SETUP INVALIDATED.
- [x] TP1/TP2/TP3/TP4 HIT.

## Deduplication

- [x] Persist scenario ID.
- [x] Persist last state/alert time.
- [x] Alert only on meaningful state change.
- [x] Do not repeat the same alert every minute.

## Replay tests

- [x] Reversal sequence replay.
- [x] Continuation sequence replay.
- [x] Invalidation replay.
- [x] No-lookahead transition test.
- [x] No duplicate-alert test.
- [x] Restart/recovery test.

## Done when

- [x] Both setup families work deterministically.
- [x] Alerts occur only on meaningful transitions.
- [x] Replay/live logic is shared.
- [x] Full suite green.
- [x] Push checkpoint and update this file.

---

# Phase 10 — VPS Orchestration, Health, Logging, Scheduling

## Goal

Run the complete morning workflow reliably without manual intervention.

## Health check

- [x] Create `scripts/healthcheck.py`.
- [x] Check credentials/auth.
- [x] Check current contract.
- [x] Check data directory write access.
- [x] Check latest-bar freshness.
- [x] Check required modules/config files.
- [x] Run lightweight test subset if appropriate.
- [x] Exit non-zero on critical failure.

## Logging

- [x] Structured logs under `data/logs/`.
- [x] Log auth success/failure without secrets.
- [x] Log requests, contract, bar count, latest timestamp, validation, state-build duration, scenario scores, reports, alerts, failures.
- [x] Never log passwords/API keys.

## Orchestrator

- [x] Create one orchestrator if practical.
- [x] Premarket mode.
- [x] Refresh mode.
- [x] Live-monitor mode.
- [x] Minimize duplicated code.

## Schedule

- [x] 08:55 ET — health check.
- [x] 08:58 ET — ProjectX collection.
- [x] 09:00 ET — state + morning plan.
- [x] 09:25 ET — refresh + thesis comparison.
- [x] 09:29 ET — live monitor armed.
- [x] 09:30–10:30 ET — monitoring.
- [x] 10:30 ET — close monitor + save recap.

## VPS scheduling

- [ ] Check `timedatectl`. **REQUIRES VPS VERIFICATION.**
- [x] Choose systemd timers vs cron.
- [x] Use ET-aware scheduling and automatic EST/EDT handling.
- [ ] Verify each job manually first. **REQUIRES VPS VERIFICATION.**
- [ ] Verify jobs survive VPS reboot. **REQUIRES VPS VERIFICATION.**
- [ ] Verify logs prove execution. **REQUIRES VPS VERIFICATION.**

## Done when

- [ ] Full weekday workflow runs automatically. **REQUIRES VPS VERIFICATION.**
- [x] Logs provide audit trail.
- [x] Failure handling is safe.
- [ ] Services survive restart. **REQUIRES VPS VERIFICATION.**
- [x] Push checkpoint and update this file.

## Phase 10 Work evidence

- Work-side checklist: **29/35**; all six open roadmap items require Hostinger VPS execution.
- Focused Phase 10 tests cover health PASS/failure/staleness, credential aliases,
  secret-safe JSONL logs, all orchestrator paths, Telegram transport, artifact
  paths, deployment safety, systemd schedules, and ProjectX Parquet ingestion.
- The existing Phase 1–9 dependency suites remain green with the production
  entry points; rendered unit files and every `OnCalendar` expression validate.
- `deploy.sh` is fast-forward-only, preserves `.env`, runs the Phase 10 smoke
  suite and health check, and fails non-zero on unsafe or unhealthy deployment.
- VPS certification still requires real environment/authentication, contract and
  freshness checks, filesystem permissions, Telegram delivery, systemd install
  and manual mode execution, scheduled execution/log inspection, and reboot
  survival. No Work-side test is represented as VPS proof.

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
