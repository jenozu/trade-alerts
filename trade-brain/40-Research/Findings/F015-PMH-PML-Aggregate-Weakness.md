# F015 — PMH/PML aggregate weakness

Status: Supported

Source: [[../Experiments/EXP-005-Important-Liquidity-Level]]

## Finding

Across the classified 2023–2025 baseline, PMH/PML interactions were materially weak in aggregate, but the weakness was not stable in every year.

## Evidence

Combined PMH/PML:

- 109 trades.
- -4.07 pts expectancy.
- -0.159R expectancy.
- PF 0.79.
- -443.75 net points.
- 75.2% stop rate.

The sample was overwhelmingly reversal-classified:

- PMH/PML reversal: 107 trades, -3.68 pts expectancy, PF 0.81.
- PMH/PML continuation: only 2 trades, too small to interpret.

By year:

- 2023: 40 trades, -8.06 pts expectancy, PF 0.57.
- 2024: 28 trades, +2.90 pts expectancy, PF 1.17.
- 2025: 41 trades, -4.95 pts expectancy, PF 0.76.

## Interpretation

PMH/PML is a legitimate area for later refinement, especially for reversal setups, but the positive 2024 counterexample means it should not be treated as universally weak. This is another example of the regime dependence documented in [[F005-Year-Regime-Dependence]].

## Implication

Do not remove PMH/PML or apply a hard PMH/PML penalty yet. Later experiments should control for direction, confirmation stack, premarket range width, and regime before testing a production change.
