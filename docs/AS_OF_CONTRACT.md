# Production `as_of` contract (Phase 2 C1)

Authoritative reference for how time works in /docker/trade-alerts. The
canonical implementation lives in `src/data_clock.py`; this document states
the contract that implementation (and every downstream consumer) must honor.
Approved 2026-09-03 as part of the Phase 2 data/time semantics.

## 1. Timestamps are bar open times

Every bar `timestamp` is the time the bar OPENED, stored timezone-aware in
UTC. A bar that opens at 09:30 ET is not complete until 09:31 ET.

## 2. Availability: `available_at <= as_of`

- Raw one-minute bars normally carry no `available_at` column; their
  visibility is inferred as `timestamp + 1 minute` (configurable via
  `bar_duration` for other base feeds).
- Resampled and derived bars carry an explicit `available_at` column equal to
  `bar_timestamp + bar_duration` for that timeframe (a 15m bar opening 09:30
  ET is available at 09:45 ET).
- A row may influence analysis at time `as_of` **if and only if**
  `available_at <= as_of`.

## 3. Incomplete bars are never production inputs

When a dataframe exposes a `bar_complete` flag, `filter_as_of` also excludes
rows whose flag is false. An intraday higher-timeframe bucket missing any of
its required constituent minutes is incomplete and stays hidden even after
its nominal `available_at` has passed. No tolerance is added that could
expose gap-affected bars.

The same rule holds for the session-aware `1d` bar (`src/resample.py`): a
daily bar aggregates exactly the half-open Globex window
`[prior-day 18:00 ET, trading-date 17:00 ET)` and is complete only when the
completed input contains every constituent minute of that window (the true ET
wall-clock count: 1380 on a normal day, 1320 across spring-forward, 1440
across fall-back). Bars opening in the daily maintenance window
`[17:00, 18:00)` ET belong to no session and never enter a daily aggregate. A
fully covered session is complete from its 17:00 ET `available_at` even when
it is the last session in the data; a still-developing session, or an earlier
session with missing constituent minutes, stays incomplete regardless of
whether later sessions exist. Only complete (finalized) daily bars reach the
HTF bias engine.

## 4. `as_of` is timezone-aware and normalized to UTC

- Naive timestamps are rejected (`DataClockError`). Production and replay
  callers must state the timezone explicitly rather than relying on host
  locale.
- `as_of` is converted to UTC; comparisons happen on the UTC timeline, which
  is DST-safe by construction.
- The canonical UTC cutoff is recorded on filtered frames as
  `dataframe.attrs["as_of"]` (ISO 8601 UTC).

## 5. Prefix invariance (no look-ahead)

`filter_as_of` is prefix-stable: appending future rows to a dataset never
changes the rows visible at an earlier `as_of`. A replay at time T therefore
produces exactly the same completed-prefix inputs that a live run would have
seen at T. `run_pipeline.py` cuts the 1m frame after the load stage and
re-filters every resampled result with the same cutoff before any downstream
stage (bias, sessions, volume, SNR, swings, liquidity, FVG, structure, DOL,
scoring, backtest) runs.

## 6. Consumer rule

Direct session helpers and downstream feature modules may assume their input
is already this completed prefix. They must never re-introduce future or
incomplete bars, and any additional availability rules they add (session
windows, developing vs finalized levels) must be at least as strict as this
contract.

In particular, a session feature row's knowledge instant is its own
completion (`timestamp + 1 minute` for the 1m master feed), never its
bar-open timestamp. Finalized session levels (London/overnight/premarket
H/L, Asia H/L, PD levels, opening ranges, cash open) are therefore visible
from the first row that completes at or after their availability instant,
which is exactly the edge row of the completed prefix at
`as_of == availability instant`:

- London H/L (`loh_lol` availability 05:00 ET) are on the completed prefix at
  `as_of == 05:00 ET` (whose last row opens 04:59);
- overnight and premarket H/L (`onh_onl`/`pmh_pml`, availability 09:30 ET)
  are on the completed prefix at `as_of == 09:30 ET` (last row opens 09:29);
- the cash open (`rth_open`, availability 09:31 ET) is on the completed
  prefix at `as_of == 09:31 ET` (last row opens 09:30, the bar whose open IS
  the cash open).

Evaluating these availabilities against the bar-open timestamp instead would
delay every finalized level by exactly one minute relative to the approved
`as_of` instants.

## Boundary consequences

- At a snapshot at exactly T, the bar opening at T is NOT visible; the last
  visible bar is the one opening at T-1 minute.
- A 09:00 ET replay sees through the 08:59 ET bar.
- The 09:30 ET cash-open bar is not visible until 09:31 ET; a completed-prefix
  analysis at exactly 09:31 ET sees the cash open on the 09:30 bar.
- A 15m bucket opening at 09:30 ET (constituents 09:30..09:44) is visible
  from 09:45 ET and only when all 15 minutes are present and complete.
- A fully covered Globex session's 1d bar is complete and visible at its
  17:00 ET `available_at` (the prefix then ends with the 16:59 ET bar, which
  completes exactly at 17:00).
