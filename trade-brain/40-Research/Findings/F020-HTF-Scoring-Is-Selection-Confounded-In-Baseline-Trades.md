# F020 — HTF scoring is selection-confounded in the baseline trades

Status: Supported

Source: [[../Experiments/EXP-006-HTF-Bias]]

## Finding

The baseline trade ledger cannot by itself determine whether the current HTF score weight or conflict penalty is too high or too low, because the sample was already selected using those HTF scoring rules.

## Evidence

Current scoring contract:
- +10 points when production intraday HTF bias aligns with trade direction.
- -20 points when production intraday HTF bias opposes trade direction.

Observed pure intraday relation among the 1,218 baseline trades:
- aligned: 1,119 trades, +2.16 expectancy, PF 1.12.
- neutral: 99 trades, -2.45 expectancy, PF 0.87.
- opposed: 0 trades.

Score-band interactions are therefore conditional on surviving the existing score logic. For example, 80–89 conflicting trades produced +16.73 expectancy / PF 2.11 while 80–89 aligned trades produced -0.64 / PF 0.97, but conflicting trades that still reach a high score necessarily carry unusually strong non-HTF components.

## Interpretation

This is classic selection/collider risk: comparing only trades that passed the existing score threshold can make a penalized feature appear stronger among the survivors.

## Implication

Do not change the +10/-20 HTF treatment from EXP-006 observational results alone. A controlled scoring-component ablation or rescoring exercise is required later before any weight change is justified.
