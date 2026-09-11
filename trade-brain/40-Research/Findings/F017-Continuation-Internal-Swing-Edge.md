# F017 — Continuation internal-swing edge

Status: Preliminary

Source: [[../Experiments/EXP-005-Important-Liquidity-Level]]

## Finding

Among continuation trades whose trigger level could be classified exactly from the archived features, internal-swing continuations were very strong.

## Evidence

- Internal swing continuation: 61 trades, 37.7% win rate, +13.39 pts expectancy, +0.532R, PF 1.87, +816.75 net points.
- Internal swing reversal: 511 trades, +1.64 pts expectancy, +0.065R, PF 1.09, +839.00 net points.

However, only 63 of 185 continuation trades were exactly level-classified in EXP-005; 122 continuation trades remained unclassified rather than being assigned by proximity.

## Interpretation

This is a promising interaction between continuation structure and internal swing levels, and it is directionally consistent with the broader continuation advantage found in [[F012-Continuation-Outperforms-Reversal-Across-Years]]. But incomplete continuation classification prevents treating this as a fully representative continuation result.

## Implication

Do not create a hard internal-swing continuation rule yet. Later acceptance/BOS and interaction experiments should test whether the edge survives when continuation trigger-level coverage is improved and other confirmations are controlled.
