# EXP-017 — VWAP

Status: Complete — diagnostic only

Evidence:
- [[../../../research-archive/EXP-017/EXP-017-VWAP]]

## Coverage

- Baseline trades: 1,218
- Exact feature coverage: 1,218 / 1,218

## Main findings

### VWAP side

- Above VWAP: +2.54 expectancy / PF 1.15
- Below VWAP: +1.10 / PF 1.06

Direction-relative:

- with VWAP side: +2.06 / PF 1.11
- against VWAP side: +1.20 / PF 1.07

The aggregate side effect was modest.

### VWAP slope

Slope alignment was much more informative:

- aligned: +2.72 expectancy / PF 1.15
- opposed: -0.04 / PF 1.00

This is one of the stronger VWAP observations.

### VWAP crosses

Same-direction cross at the signal was weak:

- no same-direction cross: +2.16 / PF 1.12
- same-direction cross: -3.42 / PF 0.83

Opposite-direction crosses were also weak:

- opposite cross present: -4.62 / PF 0.76

Therefore a VWAP cross by itself should not be treated as positive confirmation.

### Distance from VWAP

Performance improved materially at larger absolute distances.

Absolute-distance quartiles:

- closest: -2.68 / PF 0.85
- Q2: -0.65 / PF 0.96
- Q3: +4.30 / PF 1.25
- farthest: +6.16 / PF 1.35

Percent-distance results showed the same broad pattern.

This does not prove that being far from VWAP is causal, but it clearly rejects a simple assumption that entries close to VWAP are automatically superior.

### Setup-family interaction

Continuation trades showed a much stronger VWAP relationship:

- continuation with VWAP side: +7.36 / PF 1.43
- continuation against side: -11.59 / PF 0.42, n=14

That against-side continuation sample is small, so it should remain preliminary.

Reversal trades were far less sensitive to simple VWAP-side alignment.

## Decision

**INVESTIGATE — no strategy change.**

Do not:

- require a VWAP cross;
- require entry close to VWAP;
- globally reward all VWAP alignment equally.

VWAP slope alignment and continuation-side context are candidates for later calibration.
