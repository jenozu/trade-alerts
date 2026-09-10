# F006 — Score is ordinal, not probability

Status: Supported

Source: [[../Experiments/EXP-001-Score-Band-Analysis]]

## Finding

The current 0–100 confluence score should be interpreted as an ordinal setup-quality score, not as a calibrated probability of winning.

## Evidence

Win rate was not strictly monotonic across observed score bands, while expectancy and profit factor improved materially. This supports ranking usefulness but not probabilistic calibration.

## Decision boundary

Do not label a score such as 80 as an 80% win probability. Probability language would require a separate calibration and validation process.
