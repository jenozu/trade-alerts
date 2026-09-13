# EXP-013 — Premium / Discount

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-013/EXP-013-Premium-Discount]]

## Objective

Determine whether premium/discount location contributes unique directional edge once setup direction and DOL context are considered.

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Internal premium / discount

- Discount: +1.05 expectancy / PF 1.06
- Premium: +2.19 / PF 1.13

## External premium / discount

- Discount: +1.12 / PF 1.06
- Premium: +3.26 / PF 1.19

## Direction-relative classification

The conventional directional interpretation did not outperform.

Internal:

- favorable: -0.64 / PF 0.97
- unfavorable: +3.79 / PF 1.22

External:

- favorable: +0.17 / PF 1.01
- unfavorable: +4.44 / PF 1.26

For reversals the difference was even clearer:

Internal:
- favorable: -1.02 / PF 0.94
- unfavorable: +3.20 / PF 1.18

External:
- favorable: -0.32 / PF 0.98
- unfavorable: +3.74 / PF 1.22

Continuation trades were profitable in both states.

## Internal/external agreement

- agreement: +1.53 / PF 1.09
- disagreement: +2.44 / PF 1.14

Agreement itself did not add obvious edge.

## Dealing-range location

Distance from equilibrium was non-linear.

The far positive-distance quartiles were among the stronger cells, while some near-equilibrium ranges were weaker.

This does not support a simple "only trade from discount/premium" threshold.

## DOL limitation

The surviving baseline was overwhelmingly aligned with DOL:

- aligned: 1,189 trades
- neutral/unknown: 28
- opposed: 1

Therefore EXP-013 cannot independently determine whether premium/discount adds unique value after fully controlling for DOL opposition.

EXP-014 will examine DOL directly.

## Decision

**INVESTIGATE — no strategy change.**

Do not:
- require longs from discount;
- require shorts from premium;
- penalize the opposite side;
- add a hard equilibrium filter.

Premium/discount should remain context until its interaction with DOL and target selection is better understood.
