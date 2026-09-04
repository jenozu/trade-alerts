# Live Execution Assistant / Low-Latency Entry Alerts Roadmap

This document is part of the `trade-alerts` master roadmap. It defines the future alerting layer that sits on top of the existing deterministic premarket plan, Phase 9 live setup state machines, and Phase 10 VPS orchestration.

## Goal

Turn the existing live monitor into an execution-assistant that can surface only meaningful, high-value developments and issue explicit `BUY NOW` / `SELL NOW` alerts when a pre-defined setup becomes objectively valid.

The system remains **analysis/alerts only**. It must not place orders or manage brokerage positions automatically.

## Core principle

The premarket plan defines what the system is waiting for. The live monitor should not react to every market fluctuation. It should watch the armed scenario and only alert when new evidence materially changes the setup.

The alert ladder is:

1. `WATCH` — price/evidence is approaching a planned setup.
2. `READY` — multiple required confirmations are assembling and entry may be near.
3. `BUY NOW` / `SELL NOW` — the deterministic entry criteria are satisfied.
4. `INVALIDATED` — the setup is no longer valid.

Alerts must be deduplicated and tied to a specific scenario ID.

---

# Stage 1 — Explicit execution-alert contract

## WATCH

Use only for noteworthy developments that materially increase relevance of an armed setup, for example:

- price entering or approaching the planned trigger/support/resistance zone
- important liquidity pool reached
- PMH/PML/PDH/PDL/Asia/London/overnight level interaction
- meaningful RVOL/volume expansion near the armed zone
- fresh sweep/reclaim at the planned liquidity level
- strong displacement forming in the expected direction
- bias/DOL/confluence materially improving

WATCH must not fire for routine noise or every small indicator change.

## READY

Use when the setup has progressed beyond simple proximity and is close to a valid entry, for example:

### Reversal

- planned liquidity reached
- sweep confirmed
- opposite displacement confirmed
- MSS/CHOCH confirmed
- retest/FVG hold beginning or confirmed

### Continuation

- planned level reached
- displacement break confirmed
- acceptance/body close confirmed
- pullback/retest underway
- level/FVG holding
- micro BOS approaching or confirmed

READY means: prepare to act, but the full deterministic entry criteria are not necessarily complete yet.

## BUY NOW / SELL NOW

Map the existing deterministic `ENTRY_VALID` state to an explicit directional execution alert.

Required alert payload:

- `BUY NOW` or `SELL NOW`
- symbol/contract
- current/entry price or entry zone
- structural stop price
- TP1 / TP2 / TP3 / TP4
- setup family/subtype
- raw score and report-friendly confidence display if calibrated
- Primary DOL / bias alignment
- concise list of confirmations that caused the alert
- scenario ID
- timestamp

Example format:

```text
BUY NOW — MNQ
Entry: 18842.25–18845.00
SL: 18821.00
TP1: 18870.00
TP2: 18895.00
TP3: 18924.00
TP4: 18960.00
Setup: bullish reversal

Confirmed:
- sell-side liquidity sweep
- bullish displacement
- bullish MSS
- FVG retest held
- volume expansion
```

The wording is an execution alert, not an order instruction to a broker. The user remains responsible for manually entering any trade.

---

# Stage 2 — Noteworthy-confluence monitor

Add an objective confluence-change layer that compares the current state with the armed/premarket state and emits alerts only when evidence changes materially.

Candidate factors:

- rolling RVOL acceleration
- time-of-day RVOL percentile
- sudden volume spike relative to recent bars
- breakout volume vs rejection volume
- displacement magnitude and body/wick quality
- rapid sweep-and-reclaim behavior
- MSS/CHOCH/BOS development
- FVG creation and retest quality
- support/resistance confluence-zone interaction
- VWAP distance/cross/reclaim
- SNR improvement/deterioration
- DOL alignment changes
- score/component changes
- new obstacle/room-to-run conditions

Requirements:

- no alert for a single trivial fluctuation
- configurable minimum material-change threshold
- deduplicate repeated alerts
- preserve exact reason/components that triggered each alert
- persist alert state across process/VPS restart
- replay-identical behavior where the same completed observations are supplied

---

# Stage 3 — Two-speed monitoring architecture

The current Phase 9 state machine is intentionally completed-bar and approximately one-minute based. Preserve that as the default safety path.

## Confirmed path

- use completed 1-minute bars
- deterministic Phase 9 state transitions
- `ENTRY_VALID` maps to confirmed `BUY NOW` / `SELL NOW`
- this remains the production baseline until faster behavior is independently validated

## Optional fast micro-monitor

Only after the confirmed path is stable and backtested, add a faster monitor that activates **only when an armed setup is near its trigger zone**.

Potential faster observations:

- sub-minute price updates if ProjectX data permits
- intra-minute volume acceleration
- microstructure breakout/reclaim behavior
- rapid wick/rejection behavior
- short-horizon price velocity

The fast layer must not replace the completed-bar state machine. It may emit:

- `WATCH — FAST`
- `READY — FAST`
- experimentally, `FAST ENTRY`

A later confirmed-bar alert should still follow when the canonical entry state is satisfied.

---

# Stage 4 — Latency and delivery requirements

Measure rather than assume alert speed.

Persist timestamps for:

- market observation received
- state calculation started
- state calculation finished
- alert decision created
- Telegram/API send started
- Telegram/API send completed

Track:

- data-to-decision latency
- decision-to-send latency
- total observation-to-alert latency

Goals should be set empirically after ProjectX and VPS timing is measured. Do not sacrifice causal correctness or data validation merely to reduce latency.

---

# Stage 5 — Replay/backtest validation before aggressive alerts

Every execution-alert rule must be reproducible historically or in deterministic replay before being trusted live.

Required comparisons:

- existing confirmed `ENTRY_VALID` timing
- proposed `BUY NOW` / `SELL NOW` timing
- optional faster READY/FAST ENTRY timing
- false-entry rate
- win rate
- expectancy R
- MFE/MAE
- stop-out rate
- TP1–TP4 hit rates
- latency improvement vs outcome degradation/improvement

Important experiment:

Compare a fast/intra-bar entry against the standard completed-bar entry on the same historical/replay setups. Earlier is only better if expectancy and false-positive behavior remain acceptable.

---

# Stage 6 — Alert quality / anti-spam rules

The system should feel like a focused trading assistant, not an indicator feed.

Requirements:

- one scenario ID per armed thesis
- alert only on meaningful state/evidence change
- no repeated WATCH every minute while price remains in the same zone
- cooldown/deduplication for unchanged confluence
- READY should require stronger evidence than WATCH
- BUY NOW / SELL NOW only on deterministic entry validity
- immediate INVALIDATED alert when structural invalidation is confirmed
- stale-feed/data-health warning takes precedence over entry alerts
- no entry alert if market state is `NO ANALYSIS` or critically stale

---

# Stage 7 — Telegram presentation

Recommended alert hierarchy:

```text
WATCH — LONG REVERSAL
READY — LONG REVERSAL
BUY NOW — MNQ
TP1 HIT
TP2 HIT
SETUP INVALIDATED
```

Messages should be compact enough to understand immediately on a phone, with the most actionable information first.

For BUY/SELL alerts put near the top:

- direction
- entry/current price
- SL
- TP1–TP4
- setup type

Then show the small number of decisive confirmations.

---

# Safety / architecture constraints

- analysis and alerts only
- no automated order placement
- no brokerage position management
- no bypass of stale-data checks
- no bypass of completed-bar rules in the confirmed path
- no LLM deciding numerical entry/SL/TP values
- Python deterministic state/planner remains authoritative
- LLM prose may summarize deterministic reasons but cannot invent or modify levels
- faster experimental alerts must be separately labelled until validated

---

# Implementation order

Do not build all of this at once.

Recommended sequence:

1. Finish Phase 10 automatic weekday certification.
2. Run Phase 11 shadow mode and preserve real live-state transitions.
3. Continue Phase 12 historical calibration.
4. Convert `ENTRY_VALID` to explicit directional `BUY NOW` / `SELL NOW` Telegram payloads.
5. Add WATCH / READY alert severity on top of existing Phase 9 states.
6. Add material confluence-change detection and anti-spam rules.
7. Measure end-to-end latency.
8. Replay/backtest the new alert semantics.
9. Only then investigate sub-minute / fast monitoring.
10. Compare fast alerts against the canonical completed-bar alerts before enabling them in normal use.

---

# Completion gates

This roadmap extension is complete only when:

- WATCH / READY / BUY NOW / SELL NOW semantics are deterministic and documented
- explicit directional entry alerts contain entry, SL, TP1–TP4, setup, score/confidence, and reasons
- material confluence changes can trigger useful alerts without spam
- stale/incomplete data cannot generate entry alerts
- alert deduplication survives restart
- historical/replay tests prove alert causality
- latency is measured and documented
- fast monitoring, if enabled, is separately validated against completed-bar entries
- Telegram delivery is proven in shadow mode
- no automated order placement has been introduced
