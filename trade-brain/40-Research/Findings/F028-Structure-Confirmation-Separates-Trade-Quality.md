# F028 — Structure confirmation separates trade quality

Status: Supported

Sources:
- [[../Experiments/EXP-010-Structure-Shift]]

## Finding

Trades with recent directional structure confirmation materially outperformed trades without it.

## Evidence

Any recent MSS / CHOCH / BOS:

- absent: 380 trades, -1.33 expectancy / PF 0.93
- present: 838 trades, +3.20 / PF 1.18

Same-direction structure break:

- absent: +0.15 / PF 1.01
- present: +3.99 / PF 1.23

## Interpretation

Structure context appears to contain real quality information.

However, individual structure labels are correlated and must not automatically receive independent scoring weights.
