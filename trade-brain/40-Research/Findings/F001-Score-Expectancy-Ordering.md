# F001 — Score expectancy ordering

Status: Supported

Sources:
- [[../Experiments/EXP-001-Score-Band-Analysis]]
- [[../Experiments/EXP-004-Year-and-Regime-Stability]]

## Finding

Across the combined executed-trade sample, expectancy and profit factor improve as score increases even though win rate is not strictly monotonic. EXP-004 shows that this ordering is an aggregate relationship, not a guarantee within every individual year.

## Evidence

Combined baseline:

- 70–79: +0.82 pts expectancy, PF 1.05.
- 80–89: +4.59 pts expectancy, PF 1.25.
- 90–100: +13.70 pts expectancy, PF 1.88.

EXP-004 year decomposition:

- 2023: 70–79 +3.62 / PF 1.22; 80–89 -0.67 / PF 0.96.
- 2024: 70–79 -0.24 / PF 0.99; 80–89 +3.41 / PF 1.18.
- 2025: 70–79 -0.28 / PF 0.99; 80–89 +10.00 / PF 1.57.

## Interpretation

The score remains useful as an ordinal confluence rank in aggregate, but calibration is regime-dependent. A higher band can underperform a lower band within a particular year.

## Limitation

The 90–100 band contains only 21 trades in total and only 3, 5, and 13 trades by year. No executed trades exist in 50–59 or 60–69 for this baseline. Do not interpret the score as a calibrated probability.
