# F029 — MSS and CHOCH are historically redundant

Status: Supported

Sources:
- [[../Experiments/EXP-007-Liquidity-Sweep-Contribution]]
- [[../Experiments/EXP-010-Structure-Shift]]

## Finding

MSS and CHOCH produced identical segmentation across the archived baseline research.

EXP-010:

- both absent: 732 trades, +0.10 expectancy / PF 1.01
- both present: 486 trades, +4.33 / PF 1.25

The setup-family and sequence analyses also matched exactly.

## Interpretation

The current historical feature implementation should be treated as effectively redundant for MSS versus CHOCH until source-level semantics are reviewed.

They should not receive separate independent score credit solely because the labels are conceptually different.
