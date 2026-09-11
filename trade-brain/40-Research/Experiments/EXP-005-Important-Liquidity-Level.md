# EXP-005 — Important Liquidity Level

Status: Complete — diagnostic only

Sources:
- `research-archive/EXP-005/EXP-005-Important-Liquidity-Level.md`
- `research-archive/EXP-005/exp005_level_results.json`
- `research-archive/EXP-005/level_metrics.csv`
- `research-archive/EXP-005/classified_trades.csv`

Related findings:
- [[../Findings/F005-Year-Regime-Dependence]]
- [[../Findings/F007-Short-Liquidity-Sweep-Weakness]]
- [[../Findings/F015-PMH-PML-Aggregate-Weakness]]
- [[../Findings/F016-Premarket-Range-Width-Is-Non-Monotonic]]
- [[../Findings/F017-Continuation-Internal-Swing-Edge]]

## Objective

Determine whether trigger/interaction level materially changes trade quality across the untouched 2023–2025 baseline, and whether level type deserves different treatment later. EXP-005 changes no strategy rules or score weights.

## Method

Existing baseline trade ledgers were joined to existing scored feature artifacts at exact signal time. Reversal trades use the recorded directional sweep source. Continuation trades are only classified when `structure_broken_level` exactly matches a supported known level; unmatched continuation trades remain unclassified rather than being assigned by nearest price.

## Coverage

- Total baseline trades: 1,218.
- Classified by level: 1,096 (90.0%).
- Reversal coverage: 1,033 / 1,033.
- Continuation coverage: 63 / 185.
- Unclassified continuation trades: 122.

This coverage limitation is important: reversal-level conclusions are much more complete than continuation-level conclusions.

## Aggregate level-group performance

| Level group | Trades | Exp pts | Exp R | PF | Net pts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Asia high/low | 12 | +8.08 | +0.310R | 1.56 | +97.00 |
| London high/low | 32 | -5.90 | -0.243R | 0.70 | -188.75 |
| PDH/PDL | 13 | -9.85 | -0.394R | 0.54 | -128.00 |
| PMH/PML | 109 | -4.07 | -0.159R | 0.79 | -443.75 |
| External swing | 314 | +2.34 | +0.095R | 1.13 | +734.25 |
| Internal swing | 572 | +2.89 | +0.115R | 1.16 | +1,655.75 |
| Overnight high/low | 44 | +2.64 | +0.105R | 1.15 | +116.00 |

Asia and PDH/PDL samples are too small for strong conclusions. PMH/PML, internal swing, and external swing have more useful sample sizes.

## Exact-source asymmetry

The strongest exact-source split was within internal swings:

- Active internal swing low: 296 trades, +7.56 pts expectancy, +0.301R, PF 1.46, +2,236.75 points.
- Active internal swing high: 276 trades, -2.11 pts expectancy, -0.084R, PF 0.89, -581.00 points.

This materially reinforces the short-side/sweep asymmetry already identified in [[../Findings/F007-Short-Liquidity-Sweep-Weakness]].

## Setup-family interaction

Among level-classified continuation trades, internal swings dominate:

- Internal swing continuation: 61 trades, +13.39 pts expectancy, +0.532R, PF 1.87, +816.75 points.
- Internal swing reversal: 511 trades, +1.64 pts expectancy, +0.065R, PF 1.09, +839.00 points.

Only 63 of 185 continuation trades could be exactly level-classified, so this is promising but not yet sufficient to generalize to all continuations.

PMH/PML was mostly a reversal sample:

- PMH/PML reversal: 107 trades, -3.68 pts expectancy, PF 0.81.
- PMH/PML continuation: only 2 trades, too small to interpret.

## Year stability

Level behavior is regime-dependent:

- PMH/PML: 2023 -8.06, 2024 +2.90, 2025 -4.95 pts expectancy.
- Internal swing: 2023 +5.93, 2024 -2.14, 2025 +5.01.
- External swing: 2023 +6.91, 2024 -1.40, 2025 +2.24.
- Overnight high/low: 2023 -5.48, 2024 +6.08, 2025 +6.00.

This strengthens [[../Findings/F005-Year-Regime-Dependence]]: level identity alone is not a universal edge across all years.

## PMH–PML range width

Performance by premarket-range quartile was strongly non-monotonic:

- Q1 narrow, 13.75–82.50 pts: 312 trades, -0.04 expectancy, PF 1.00.
- Q2, 82.75–114.75: 297 trades, +7.63, PF 1.47.
- Q3, 115.25–157.00: 306 trades, -4.10, PF 0.79.
- Q4 wide, 157.75–839.25: 303 trades, +3.87, PF 1.21.

Therefore the evidence does not support a simple rule such as “wide premarket ranges are bad.” The relationship appears non-linear and needs dedicated validation before any range filter is considered.

## Multi-level confluence

- No multi-level confluence: 1,071 trades, +1.66 expectancy, PF 1.09.
- Multi-level confluence: 25 trades, +2.79 expectancy, PF 1.16.

The confluence sample is too small to claim a reliable independent benefit.

## Strong evidence

- PMH/PML interactions were negative in aggregate across 109 trades, primarily driven by reversals.
- Internal swing levels were positive overall across 572 classified trades.
- Internal swing low and internal swing high performance differed dramatically.
- Level performance changes materially by year, so no level should be treated as universally strong or weak from aggregate results alone.

## Preliminary evidence

- Exactly classified internal-swing continuations were very strong, but continuation coverage is only 63/185.
- Premarket-range width materially separates performance, but the relationship is non-monotonic and not yet causal.
- Multi-level confluence shows a small positive difference but only 25 trades qualify.
- Asia, PDH/PDL, and several exact session-level cells are too small for robust conclusions.

## Decision

**INVESTIGATE — no strategy change.**

EXP-005 does not justify removing PMH/PML, promoting internal swings to a hard requirement, changing score weights, or applying a PMH–PML width filter. These observations should guide later controlled contribution, interaction, and validation experiments.

Next experiment: **EXP-006 — HTF bias**.
