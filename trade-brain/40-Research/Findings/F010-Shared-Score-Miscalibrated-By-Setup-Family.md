# F010 — Shared score is miscalibrated by setup family

Status: Supported

Source: [[../Experiments/EXP-003-Setup-Family-Comparison]]

## Finding

The current shared confluence score does not rank reversal and continuation setup families equally well. Continuation trades receive lower scores on average than reversals while delivering materially stronger realized expectancy.

## Evidence

Overall score distributions:

- Reversal: n=1,033, mean score 76.22, median 74.58.
- Continuation: n=185, mean score 73.24, median 71.82.

Overall performance:

- Reversal: +1.04 pts expectancy, PF 1.06.
- Continuation: +5.93 pts expectancy, PF 1.34.

Within the same score bands:

- 70–79 reversal: 798 trades, +0.11 pts expectancy, PF 1.01.
- 70–79 continuation: 160 trades, +4.36 pts expectancy, PF 1.25.
- 80–89 reversal: 214 trades, +3.26 pts expectancy, PF 1.18.
- 80–89 continuation: 25 trades, +15.96 pts expectancy, PF 1.99.

The 80–89 continuation sample is only 25 trades and remains exploratory, but the 70–79 comparison is large enough to establish a meaningful family calibration mismatch.

## Implication

Family-specific thresholds or score models are justified as a later research candidate. EXP-003 does **not** authorize an immediate production split because the continuation sample is much smaller and the archived ledger does not encode every full continuation-state confirmation.

Any later family-specific scorer should be validated across years, directions, and held-out data before promotion.
