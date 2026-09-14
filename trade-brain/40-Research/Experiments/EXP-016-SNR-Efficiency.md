# EXP-016 — SNR / Efficiency

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-016/EXP-016-SNR-Efficiency]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Main result

SNR and efficiency are useful, but strongly non-linear.

There is no evidence that higher SNR or higher efficiency is universally better.

## 1m SNR

Quartiles:

- Q1: +2.81 expectancy / PF 1.16
- Q2: -1.68 / PF 0.91
- Q3: +1.30 / PF 1.07
- Q4: +4.67 / PF 1.27

The highest 1m SNR quartile was strongest, but the relationship was not monotonic.

## 5m SNR

- Q1: +4.23 / PF 1.25
- Q2: +1.14 / PF 1.06
- Q3: +3.02 / PF 1.17
- Q4: -1.28 / PF 0.93

Very high 5m SNR was weaker rather than stronger.

## 15m SNR

- Q1: -0.85 / PF 0.95
- Q2: +7.40 / PF 1.45
- Q3: +0.73 / PF 1.04
- Q4: -0.13 / PF 0.99

The middle-lower 15m SNR range was materially stronger than the highest range.

## Efficiency

Efficiency behaved differently by timeframe.

1m efficiency:
- lowest quartile: +3.80 / PF 1.22
- highest quartile: -1.60 / PF 0.91

5m efficiency:
- Q2: +7.26 / PF 1.43
- highest quartile: -2.40 / PF 0.87

15m efficiency:
- highest quartile: +4.51 / PF 1.25

Therefore efficiency cannot be collapsed into one universal rule across timeframes.

## SNR changes

Large positive SNR changes were not automatically beneficial.

Examples:

- highest 5m SNR-delta quartile: -3.27 / PF 0.83
- highest 15m SNR-delta quartile: -0.92 / PF 0.95
- moderate 15m SNR delta: +7.44 / PF 1.44

## Persisted SNR quality class

The historical production classification did not behave as expected:

- `developing`: +3.30 expectancy / PF 1.19
- `strong`: +0.90 / PF 1.05

This indicates that the current SNR quality label is not a simple ordinal predictor of trade quality.

## Interpretation

SNR appears useful as contextual market-state information rather than as a universal monotonic score.

The current SNR implementation may contain overlapping information across:

- timeframe SNR;
- efficiency;
- SNR alignment;
- composite quality;
- production quality class.

Those components should not automatically receive independent score credit.

## Decision

**INVESTIGATE — no strategy change.**

Do not:

- require high SNR;
- require maximum efficiency;
- increase SNR scoring globally;
- interpret `strong` SNR quality as automatically superior.

Later calibration should test specific SNR zones and timeframe interactions rather than a one-dimensional threshold.
