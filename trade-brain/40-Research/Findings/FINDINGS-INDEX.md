# Findings Index

## EXP-001 findings

- [[F001-Score-Expectancy-Ordering]] — higher observed score bands show materially better expectancy/PF even though win rate is not strictly monotonic.
- [[F002-80-89-Outperforms-70-79]] — 80–89 materially outperforms 70–79 on expectancy and profit factor.
- [[F003-90-100-Sample-Too-Small]] — 90–100 is promising but statistically thin with 21 trades.
- [[F004-Long-Short-Score-Asymmetry]] — score quality is materially stronger for longs than shorts in aggregate, but the direction gap is not stable across every year.
- [[F005-Year-Regime-Dependence]] — score-band, direction, setup-family, and several context relationships vary materially by year/regime.
- [[F006-Score-Is-Ordinal-Not-Probability]] — current score should remain an ordinal confluence score, not a probability.

## EXP-002 findings

- [[F004-Long-Short-Score-Asymmetry]] — EXP-002 strengthens the aggregate calibration asymmetry while showing that 2023 is a counterexample to a universal long advantage.
- [[F005-Year-Regime-Dependence]] — 2023 favored shorts while 2024–2025 favored longs, strengthening the regime-dependence warning.
- [[F007-Short-Liquidity-Sweep-Weakness]] — supported: short reversal/sweep-present trades are materially weaker than short continuation/sweep-absent trades in the archived baseline.
- [[F008-FVG-Context-Concentrates-Short-Edge]] — preliminary: FVG-present shorts were strongly positive while non-FVG shorts were slightly negative.
- [[F009-Similar-Scores-Different-Directional-Quality]] — long/short score distributions are similar even though realized expectancy differs materially.

## EXP-003 findings

- [[F005-Year-Regime-Dependence]] — EXP-003 shows 2024 weakness was concentrated in reversal-classified trades while continuation trades remained strongly profitable.
- [[F007-Short-Liquidity-Sweep-Weakness]] — EXP-003 strengthens the short-side asymmetry: short reversals were negative while short continuations were strongly positive.
- [[F010-Shared-Score-Miscalibrated-By-Setup-Family]] — continuations scored lower on average than reversals while producing materially higher expectancy, including within the 70–79 band.
- [[F011-Reversal-Quality-Depends-On-Confirmation-Context]] — reversal performance is materially stronger when displacement and FVG context are present.
- [[F012-Continuation-Outperforms-Reversal-Across-Years]] — continuation has higher expectancy/PF in all three baseline years, but its aggregate advantage is strongly direction-dependent.

## EXP-004 findings

- [[F005-Year-Regime-Dependence]] — EXP-004 confirms 2024 weakness was concentrated rather than universal and that score-band behavior changes materially by year.
- [[F013-Displacement-and-FVG-Are-Cross-Year-Stable-Confirmations]] — displacement-present and FVG-present trades were profitable in all three baseline years; displacement-absent trades were negative in all three.
- [[F014-2024-Weakness-Was-Lower-Favorable-Excursion-Not-Higher-Adverse-Excursion]] — 2024 had lower MFE and target reach than peer years without higher MAE.

## Status convention

- Preliminary — interesting but sample/evidence is insufficient.
- Supported — repeated evidence exists, but more validation is needed.
- Validated — passed the roadmap's robustness/out-of-sample requirements.
- Rejected — evidence did not support the hypothesis.
- Superseded — replaced by a later, stronger finding.
