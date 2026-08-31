# MNQ Backtesting MVP Handoff and Next-Step Plan

## Purpose of this document

This file is the handoff point for continuing development in a new ChatGPT session without losing the current project context.

The project is an **MNQ historical research and backtesting system** that uses **read-only ProjectX/TopstepX market data**. The tool is not intended to place, modify, cancel, route, or relay trades. Trade execution remains manual.

Repository:

`https://github.com/jenozu/trade-alerts`

VPS project path:

`/docker/trade-alerts`

Current environment:

- Hostinger Ubuntu VPS
- Python virtual environment: `/docker/trade-alerts/.venv`
- ProjectX credentials stored locally in `/docker/trade-alerts/.env`
- `.env` is gitignored and must never be committed
- Current market: MNQ
- Current contract used for the first MVP test: `MNQU6`
- Historical source: ProjectX Gateway API

---

# 1. Safety / account-protection rule

The project must remain **market-data / research / alert only**.

Allowed ProjectX use for this project:

- authenticate
- search contracts
- retrieve historical bars
- later receive/read live market data for alerts
- store data
- backtest
- calculate signals
- log simulated trades

Do not add order-transmission features.

Specifically, do not add code that can:

- place orders
- modify orders
- cancel orders
- flatten positions
- move stops
- submit brackets
- copy trades
- route or relay an order to another service

The current `fetch_projectx_history.py` is a read-only historical downloader and contains no order-execution functionality.

---

# 2. Current repository architecture

```text
trade-alerts/
├── .gitignore
├── pytest.ini
├── requirements.txt
├── fetch_projectx_history.py
├── analyze_exit_models.py
├── run_pipeline.py
│
├── config/
│   ├── sessions.yaml
│   └── strategy.yaml
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── validate_data.py
│   ├── resample.py
│   ├── sessions.py
│   ├── volume.py
│   ├── snr.py
│   ├── swings.py
│   ├── liquidity.py
│   ├── fvg.py
│   ├── structure.py
│   ├── scorer.py
│   └── backtest.py
│
├── tests/
│   ├── __init__.py
│   ├── test_data_loader.py
│   ├── test_validate_data.py
│   ├── test_exit_models.py
│   └── test_fvg_timezone.py
│
└── docs/
    └── BACKTESTING_MVP_HANDOFF.md
```

Generated market data and backtest results remain outside Git history because `.gitignore` excludes raw/processed market data, Parquet files, `.env`, and generated result files.

---

# 3. Current strategy configuration

The repo configuration is now set for MNQ:

```yaml
market:
  symbol: "MNQ"
  tick_size: 0.25
  point_value: 2.0
```

Important distinction:

- MNQ moves in the same Nasdaq-100 index points used by the strategy logic.
- MNQ is worth `$2 per point` per contract.
- The current backtester primarily measures results in points and R multiples.
- Monetary P&L should use MNQ's `$2/point` contract value when dollar reporting is added later.

Current target research distances remain:

- TP1: +25 points
- TP2: +50 points
- TP3: +75 points
- TP4: +100 points

Current preferred stop range remains approximately 20-25 points.

---

# 4. Current ProjectX historical downloader

Script:

`fetch_projectx_history.py`

The first successful download command was:

```bash
python fetch_projectx_history.py \
  --symbol MNQ \
  --contract-name MNQU6 \
  --days 30 \
  --output data/raw/projectx/mnq_1m.csv
```

The first successful ProjectX dataset contained:

- 28,740 completed 1-minute MNQ bars
- start: approximately 2026-08-02 22:00 UTC
- end: approximately 2026-08-31 16:59 UTC
- current September 2026 MNQ contract: `MNQU6`

The downloader retrieves bars in 10-day chunks by default with a built-in delay and stays comfortably below the documented ProjectX historical-request rate limit.

Once the CSV is downloaded, all pipeline/backtest work is local on the VPS and makes no additional ProjectX requests.

---

# 5. Current pipeline

The end-to-end historical pipeline is:

```text
ProjectX MNQ 1m data
        ↓
data_loader.py
        ↓
validate_data.py
        ↓
resample.py
        ↓
sessions.py
        ↓
volume.py / RVOL
        ↓
snr.py
        ↓
swings.py
        ↓
liquidity.py
        ↓
fvg.py
        ↓
structure.py
        ↓
scorer.py
        ↓
backtest.py
        ↓
results
```

Full run command:

```bash
python run_pipeline.py \
  --input data/raw/projectx/mnq_1m.csv \
  --source PROJECTX \
  --symbol MNQ \
  --contract MNQU6 \
  --timezone UTC
```

Important execution assumptions already in the backtester:

- completed bars only
- signal known at bar close
- entry on next bar open
- conservative same-bar handling
- if stop and target occur in the same OHLC bar and order is unknowable: stop first
- adverse entry slippage
- adverse exit slippage
- one open trade at a time
- maximum holding time: 60 minutes
- TP1-TP4 tracked as milestones
- current baseline fully exits only at TP4, stop, timeout, or end of data

---

# 6. First data-validation result

First 30-day MNQ dataset:

- rows: 28,740
- validation status: PASS
- timestamp-gap warnings: 20
- extreme-bar-range warnings: 10

The timestamp gaps were warnings rather than hard failures because the current validator is not yet fully exchange-session-aware. These must be reviewed before a final production-grade one-year study, but they did not block the exploratory MVP run.

The validator successfully created normalized Parquet output.

---

# 7. First resample / feature results

The 30-day dataset generated:

```text
1m:   28,740 bars
5m:    5,748 bars
15m:   1,916 bars
30m:     958 bars
1h:      479 bars
4h:      130 bars
1d:       26 bars
```

Session enrichment identified:

- 21 trading sessions

Volume / RVOL:

- rolling RVOL available: 28,720 bars
- time-of-day RVOL available: 21,840 bars
- rolling volume spikes: 4,258
- time-of-day volume spikes: 3,332

Median SNR results:

- 1m SNR: ~0.894
- 5m SNR: ~0.907
- 15m SNR: ~0.815

Confirmed swings:

- internal highs: 3,870
- internal lows: 3,869
- external highs: 1,768
- external lows: 1,702

Liquidity sweeps:

- total: 3,479
- buy-side: 1,712
- sell-side: 1,767

FVGs:

- bullish: 2,800
- bearish: 2,690
- bullish retest holds: 1,636
- bearish retest holds: 1,685

Structure:

- bullish displacement: 2,169
- bearish displacement: 2,076
- bullish MSS: 373
- bearish MSS: 341
- bullish BOS: 424
- bearish BOS: 429

Scoring:

- long candidates: 18
- short candidates: 26
- max long score: 80
- max short score: 80

Because only one open trade is allowed at a time, the final simulator produced fewer executed simulated trades than raw candidates.

---

# 8. First 30-day exploratory backtest result

The first complete backtest generated:

- trades: 18
- wins: 1
- losses: 17
- baseline win rate: 5.56%
- expectancy: -18.31 points/trade
- expectancy: -0.732R/trade
- profit factor: 0.232
- average MFE: 40.44 points
- median MFE: 31.25 points
- average MAE: 31.13 points
- median MAE: 30.63 points
- average score: 73.11
- average hold time: 6 minutes

Milestone hit rates:

- TP1 (+25): 55.56%
- TP2 (+50): 27.78%
- TP3 (+75): 16.67%
- TP4 (+100): 5.56%
- stop hit rate: 94.44%

Important interpretation:

The headline 5.56% win rate does **not** mean only one signal moved favorably. The current baseline model requires TP4 (+100 points) for a full profit exit. TP1, TP2, and TP3 are only recorded as milestones.

A trade may move +25, +50, or even +75 points in the intended direction and later reverse to the stop, which the current baseline records as a full loss.

The key first finding is therefore:

> 55.56% of the first 18 trades reached +25 points, while the median favorable excursion was +31.25 points. The current all-or-nothing +100-point exit model appears to be a major contributor to the poor headline result and must be studied separately from signal quality.

Do not conclude that the strategy works or fails from 18 trades.

---

# 9. Housekeeping changes completed after the first run

## 9.1 MNQ configuration corrected in GitHub

The repo now permanently uses:

- symbol: MNQ
- tick size: 0.25
- point value: 2.0

This replaces the earlier NQ `$20/point` configuration.

## 9.2 FVG timezone warnings fixed

The first run produced Pandas `FutureWarning` messages because timezone-aware ProjectX UTC timestamps were being assigned into timezone-naive FVG lifecycle columns.

`src/fvg.py` now initializes FVG lifecycle timestamp columns using the same timezone-aware dtype as the source `timestamp` column.

Affected lifecycle fields include:

- first_touch_time
- full_fill_time
- retest_hold_time
- invalidation_time
- inverse_fvg_time

A focused regression test was added in:

`tests/test_fvg_timezone.py`

## 9.3 Exit-model comparison added

New script:

`analyze_exit_models.py`

It compares the same already-generated signals/stops under:

- current baseline
- full exit at TP1
- full exit at TP2
- full exit at TP3
- full exit at TP4

It does **not** change entries, scores, signal selection, stops, or market path.

It uses the milestone flags already produced by the causal backtester. Same-bar stop-first handling is therefore preserved.

Default command:

```bash
python analyze_exit_models.py
```

Default inputs:

- `data/results/backtest/trades.csv`
- `config/strategy.yaml`

Default outputs:

- `data/results/backtest/exit_model_comparison.csv`
- `data/results/backtest/exit_model_comparison.json`

A focused regression test was added in:

`tests/test_exit_models.py`

---

# 10. Immediate next steps on the VPS

After these GitHub changes are pushed, run:

```bash
cd /docker/trade-alerts
source .venv/bin/activate
git pull
pytest -v
```

The previous suite had 51 passing tests. Two focused housekeeping tests were added, so the expected count is now approximately 53 passing tests if there are no environment differences.

Then rerun the same 30-day pipeline once to confirm the FVG warning is gone:

```bash
python run_pipeline.py \
  --input data/raw/projectx/mnq_1m.csv \
  --source PROJECTX \
  --symbol MNQ \
  --contract MNQU6 \
  --timezone UTC
```

Then run:

```bash
python analyze_exit_models.py
```

Review:

```bash
cat data/results/backtest/exit_model_comparison.csv
```

This is the very next research result to examine.

---

# 11. Phase A — Determine whether the main problem is signal quality or exit management

Do not change strategy entries yet.

First compare the same 18 signals under the four fixed full-exit targets.

Questions to answer:

1. Does full TP1 (+25) become positive expectancy?
2. Does full TP2 (+50) improve or worsen expectancy?
3. Does TP3 (+75) work only for high-score / high-SNR subsets?
4. Does TP4 simply demand more continuation than these setups usually provide?
5. Does the TP4 comparison exactly reproduce the current baseline? If not, investigate the comparison logic before using it.

Do not optimize target distances beyond the pre-declared 25/50/75/100 values yet.

The first purpose is to understand the existing strategy, not to curve-fit it.

---

# 12. Phase B — Manually audit the first 18 trades

Before adding more data, inspect every first-sample trade against a chart or exported bars.

For each trade verify:

- signal timestamp
- entry was truly next-bar open
- direction
- score and score band
- entry occurred inside the allowed 09:30-10:30 ET window
- session levels were actually known at that time
- liquidity sweep was genuinely confirmed
- swing used by structure logic was already confirmed
- displacement occurred before the structure signal
- MSS/BOS was not using future bars
- FVG existed before it was used
- higher-timeframe SNR value came only from a closed HTF candle
- stop was correctly selected
- TP milestones correspond to the actual path
- same-bar ambiguous cases used stop-first treatment
- MFE/MAE values are reasonable

Create a small audit table with columns such as:

```text
trade_id
signal_time
direction
entry_correct
session_correct
sweep_correct
structure_correct
fvg_correct
snr_correct
stop_correct
milestones_correct
notes
```

Do not tune the model until the first trades have been visually audited.

---

# 13. Phase C — Finish causality-sensitive unit tests

The first two original test files covered loading and validation. Additional housekeeping tests now cover FVG timezone handling and exit-model comparison.

Before treating a large one-year result as trustworthy, add dedicated tests in approximately this order:

1. `test_resample.py`
2. `test_sessions.py`
3. `test_volume.py`
4. `test_snr.py`
5. `test_swings.py`
6. `test_liquidity.py`
7. `test_fvg.py`
8. `test_structure.py`
9. `test_scorer.py`
10. `test_backtest.py`
11. `test_pipeline.py`

Priority causality assertions:

### Resampling

- five completed 1m bars create one completed 5m bar
- incomplete HTF bars cannot be used as confirmed information

### Sessions

- PDH/PDL cannot appear before the relevant prior session is finalized
- PMH/PML cannot expose the completed premarket range before 09:30
- ONH/ONL cannot expose the completed overnight range before 09:30
- LOH/LOL cannot expose final London values before the London window closes
- OR5 cannot be final before 09:35
- OR15 cannot be final before 09:45
- OR30 cannot be final before 10:00
- specifically test evening-session leakage across the futures `session_date` boundary

### Volume

- rolling RVOL excludes the current bar from its baseline where configured
- time-of-day RVOL excludes the current session from the historical baseline

### SNR

- a 5m value is unavailable to the 1m stream until the 5m bar has fully closed
- same for 15m

### Swings

- an internal 2-right-bar pivot is unusable until both right-side bars close
- an external 5-right-bar pivot is unusable until all five right-side bars close

### Liquidity

- sweeps reference only levels that were already known
- repeated level values should eventually use unique level identities rather than price-only reset logic

### FVG

- an FVG becomes known only on the third candle close
- lifecycle events never appear before they happen
- expiration / full-fill lifecycle rules should be made explicit and tested

### Structure

- BOS/MSS/ChoCH use confirmed swings only
- event order must be explicit when testing the core sequence
- do not treat `sweep`, `displacement`, `MSS`, `FVG/retest` merely being inside the same rolling window as proof that they happened in the correct chronological order

### Scoring

- score only uses fields available as of that bar close
- no future session / swing / HTF values can contribute

### Backtest

- signal at bar close enters only on the next bar open
- same-bar stop + target uses stop-first
- one-open-trade rule behaves as expected
- target milestones are recorded without accidentally changing baseline exits

---

# 14. Known technical debt to resolve before trusting final one-year results

These are not necessarily blocking the exploratory MVP, but they are important before calling the system validated.

## 14.1 Session finalized-level leakage

Earlier review identified a risk that finalized overnight/premarket/London values can be exposed to evening bars because futures `session_date` rolls at 18:00 ET while some availability masks use only local clock time.

This must receive a dedicated causality test and fix before final research conclusions.

## 14.2 Structure sequence ordering

The current rolling core-sequence fields may show that sweep/displacement/MSS/FVG all occurred recently without strictly proving the intended chronological order.

A proper ordered state machine should eventually enforce something like:

```text
sweep_time <= displacement_time <= MSS_time <= FVG_or_retest_time
```

## 14.3 Unique liquidity / swing IDs

Price-only reset logic can confuse a newly-created liquidity level with an older level at the same numerical price.

Longer-term, levels should have stable IDs containing source + creation time/pivot identity.

## 14.4 FVG lifecycle completeness

The timezone warning is fixed, but the larger lifecycle model should still receive explicit tests for:

- expiry after configured maximum bars
- whether a full fill remains active
- IFVG persistence
- exact boundary-touch semantics

## 14.5 Bar-availability convention

All feature modules should consistently document whether a row labeled at time `T` represents information available at bar open or only after bar close.

The historical engine currently intends **bar-close availability** for signals.

## 14.6 Config / column naming harmonization

Continue checking that scorer expectations and feature-output column names match exactly. A particular historical risk was room-to-target naming differences between `distance_to_unswept...` and `distance_to_nearest_unswept...` style columns.

---

# 15. Phase D — Expand the sample gradually

Do not jump straight from 18 trades into tuning.

Suggested progression:

### Step 1: current 30-day sample

Use it for debugging, visual audit, and exit-model comparison.

### Step 2: 60-90 day single-contract-compatible sample

Expand once the 30-day mechanics are verified.

Goals:

- increase candidate count
- check whether TP1 behavior persists
- inspect score-band separation
- inspect long vs short differences
- inspect SNR buckets with larger counts

### Step 3: one-year MNQ study

After contract-roll handling is implemented, download and combine approximately one year of MNQ 1-minute history.

Do not blindly concatenate quarterly contracts across rollover boundaries. The downloader should explicitly identify the active quarterly contracts and apply a documented rollover rule.

Likely quarterly cycle:

- March
- June
- September
- December

At each boundary:

- prevent fake price gaps caused by switching contracts
- prevent previous-contract final close from being treated as the next contract's continuous next minute
- preserve source contract identifier per row
- document the rollover timestamp / rule

---

# 16. Phase E — Improve results scientifically

Once mechanics and causality are verified, improve the system in a controlled order.

## 16.1 Exit-management research first

Compare:

- full TP1
- full TP2
- full TP3
- full TP4

Only after those are understood, consider partial-management models, for example:

- partial at TP1, runner to TP2/TP3
- partial at TP1, move remainder to breakeven
- partial at TP1/TP2, runner to TP4

Do not mix entry-rule changes and exit-rule changes in the same experiment.

## 16.2 Stop-distance research

Use the existing predeclared stop research values:

- 15
- 20
- 25
- 30
- 35 points

Compare them on identical signals.

Look at:

- expectancy
- profit factor
- stop-out rate
- MFE/MAE
- R distribution

## 16.3 Score-band validation

The 0-100 score is a confluence score, **not a probability**.

Test whether higher score bands actually rank better outcomes.

Examples:

- 55-69
- 70-79
- 80-89
- 90+

Desired pattern:

```text
higher raw score -> better historical outcome distribution
```

If higher bands do not outperform lower bands, inspect contribution weights rather than relabeling the score as probability.

## 16.4 SNR research

Test SNR as a market-quality filter, not just an isolated threshold.

Study:

- 1m SNR
- 5m SNR
- 15m SNR
- direction alignment
- slope
- delta
- path efficiency

Do not optimize to the first tiny sample. The first 30-day SNR buckets contain too few trades for strong conclusions.

## 16.5 Feature ablation

Once there is a larger sample, test each feature's incremental value.

Examples:

- remove sweep contribution
- remove FVG contribution
- remove RVOL contribution
- remove SNR contribution
- remove HTF bias contribution
- remove DOL contribution

Compare performance while leaving all other rules unchanged.

This helps distinguish genuinely useful confluences from decorative complexity.

---

# 17. Phase F — Proper chronological validation

Do not optimize on an entire one-year sample and then report that same year as proof.

Use chronological splits.

One simple approach:

```text
Months 1-6   development
Months 7-9   validation
Months 10-12 final holdout
```

Also consider walk-forward analysis:

```text
Develop Jan-Apr -> test May
Develop Feb-May -> test Jun
Develop Mar-Jun -> test Jul
...
```

The final holdout should not be repeatedly used for tuning decisions.

---

# 18. Phase G — Live forward testing later

Live work is not the next task yet.

After historical causality is verified and the strategy has a defensible historical profile, reuse the same deterministic modules for a read-only live scorer.

Desired architecture:

```text
ProjectX live market data
        ↓
same sessions / RVOL / SNR / swings / liquidity / FVG / structure modules
        ↓
same scorer
        ↓
alert
        ↓
manual trader decision
```

No order endpoints are required.

The purpose of live mode is:

- forward-test signals
- compare live vs historical behavior
- send alerts
- log hypothetical entries/stops/targets

Actual trade execution remains manual.

---

# 19. Recommended next-session prompt

A new ChatGPT session can start with:

> Review `docs/BACKTESTING_MVP_HANDOFF.md` in my `jenozu/trade-alerts` GitHub repository and continue from the immediate next steps. The first 30-day MNQ ProjectX backtest is complete. Do not redesign the strategy. First verify the new housekeeping changes, run the exit-model comparison, help me interpret it, then continue the causality test suite before expanding to the one-year dataset.

---

# 20. Immediate checklist

```text
[ ] SSH / open Hostinger terminal
[ ] cd /docker/trade-alerts
[ ] source .venv/bin/activate
[ ] git pull
[ ] pytest -v
[ ] confirm FVG incompatible-dtype warnings are gone
[ ] rerun same 30-day pipeline if needed
[ ] python analyze_exit_models.py
[ ] inspect exit_model_comparison.csv
[ ] manually audit first 18 trades
[ ] begin test_resample.py
[ ] continue causality tests
[ ] only then expand the historical sample
```

The next research decision should be based on the fixed-target exit comparison, not on the original 5.56% TP4-only headline win rate alone.
