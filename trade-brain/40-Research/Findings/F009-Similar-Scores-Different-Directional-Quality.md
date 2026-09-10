# F009 — Similar scores, different directional quality

Status: Supported

Source: [[../Experiments/EXP-002-Long-vs-Short]]

## Finding

Long and short trades receive very similar raw score distributions, yet realized performance differs materially. The current single score therefore does not appear equally calibrated across directions.

## Evidence

Score distribution:

- LONG: n=653, mean 76.11, median 74.42, standard deviation 5.45.
- SHORT: n=565, mean 75.36, median 73.59, standard deviation 5.11.

Realized performance:

- LONG: +2.94 pts expectancy, PF 1.17.
- SHORT: +0.45 pts expectancy, PF 1.02.

Large score bands show the same pattern:

- 70–79: LONG +1.67 / PF 1.10 versus SHORT -0.14 / PF 0.99.
- 80–89: LONG +7.52 / PF 1.43 versus SHORT +1.04 / PF 1.05.

## Implication

A score near 75–85 currently carries different realized quality depending on trade direction. This supports evaluating separate directional calibration later, but not implementing separate weights yet.

## Limitation

The long advantage is not stable in sign across all three years: 2023 favored shorts. Direction-specific scoring remains a research candidate, not a validated production decision.
