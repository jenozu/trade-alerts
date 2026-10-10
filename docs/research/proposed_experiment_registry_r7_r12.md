# Proposed remaining experiment registry — R7–R12

Status: **planning proposal, not approved executable experiments**. Source:
`refine-roadmap.md` sections 11–16, `docs/research/exp030_readiness_and_backlog.md`,
and the 2026-10-10 EXP-030 r02 evidence. This registry assigns **provisional**
EXP-031–EXP-050 identifiers so preparation can be tracked. These identifiers
do not themselves authorize strategy parameters, wrappers, backtests, deployment
or executions. Historical EXP-001–EXP-021 retain their own identities;
EXP-022–EXP-029 remain unassigned. EXP-012 remains blocked. R7.0 is completed
and rejected; do not rerun it.

## Headline accounting

- **20 provisional future work packages** in R7–R12; **0 are executable or approved**.
- R7: 4; R8: 4; R9: 6; R10: 2; R11: 2; R12: 2.
- EXP-030 diagnostic completed successfully in GitHub Actions
  [run 38062346882](https://github.com/jenozu/trade-alerts/actions/runs/38062346882);
  its 2023 diagnostic reports eight eligible signals, zero accepted plans and
  zero simulated trades. Review and durable archive remain necessary.
- This is a **planning count**, not an empirically determined number of required
  hypothesis tests. Work packages may be merged, split, cancelled, or added
  after preregistration. Do not calculate a purported experimental completion
  percentage using these provisional IDs as if they were finished experiments.

## Proposed mapping and dependency graph

| ID | Stage | Proposed scoped question / output | Dependencies / outstanding decisions | State |
| --- | --- | --- | --- | --- |
| EXP-031 | R7 | Identify a valid executable control and characterize planning rejections | EXP-030 archive/review; certified source data; do not loosen stops/obstacles implicitly | Proposed |
| EXP-032 | R7 | Isolated level-reaction/break + retest interaction | 031; independently specified rule, frozen baseline and attribution | Proposed |
| EXP-033 | R7 | Isolated volume/RVOL + HTF-context interaction | 032 or separately justified executable control; select one isolated variable | Proposed |
| EXP-034 | R7 | Isolated sweep/displacement/structure/FVG confirmation interaction | 031–033 evidence; exact feature timing, precedence and single-change definition | Proposed |
| EXP-035 | R8 | Causal volatility and trend/range segmentation | Valid candidate/control and accepted trade ledger; as-of classifier | Proposed |
| EXP-036 | R8 | Causal SNR and overnight/premarket range segmentation | 035 or independent segmentation; cutoff/missingness plan | Proposed |
| EXP-037 | R8 | Opening-gap/day-type segmentation | 035–036; causal opening classification and window boundaries | Proposed |
| EXP-038 | R8 | Family-by-regime interaction report; optional news only with deterministic data | 035–037; adequate samples; no ex-post regime at entry | Proposed |
| EXP-039 | R9 | Year/month performance stability | Frozen candidate, comparable ledgers, sample policy | Proposed |
| EXP-040 | R9 | Long/short and reversal/continuation stability | 039 or same locked ledger; subgroup sample policy | Proposed |
| EXP-041 | R9 | Parameter sensitivity around one selected parameter | Frozen candidate, exact approved grid; avoid searching after seeing results | Proposed |
| EXP-042 | R9 | Realistic MNQ commissions/slippage stress | Account fee evidence, fill/slippage cases, approved quantity assumptions | Proposed |
| EXP-043 | R9 | Outlier dependence of returns | Comparable ledger, preregistered exclusion and tie rules | Proposed |
| EXP-044 | R9 | Robustness synthesis and candidate freeze recommendation | 039–043 evidence; explicit criteria; no silent selection | Proposed |
| EXP-045 | R10 | Truly held-out evaluation | 044 candidate freeze; independently established untouched dates, criteria and dataset integrity | Proposed |
| EXP-046 | R10 | Rolling walk-forward evaluation | 044–045 protocol; approved train/test windows, step, embargo and calibration | Proposed |
| EXP-047 | R11 | Equivalent-contract baseline versus isolated candidate variants | 044–046; baseline, entry, scoring and exit candidates on comparable assumptions | Proposed |
| EXP-048 | R11 | Combined-candidate comparison against frozen controls | 047; only independently validated improvements combined | Proposed |
| EXP-049 | R12 | Shadow/live consistency and acceptance-evidence audit | 047–048; live/shadow observations and risk/operational gate evidence | Proposed |
| EXP-050 | R12 | Final readiness decision and immutable evidence/config package | 049 and all acceptance gates; separate explicit promotion approval | Proposed |

## Gates and permitted preparation

Every proposal begins as `PROPOSED`, not `PREPARED`. Before creating an
executable `automation/experiments/EXP-NNN.sh`, require:

1. Approved preregistration: testable hypothesis, comparable control,
   exactly one changed factor where appropriate, freeze settings, source/time
   semantics, metrics, statistical/sample rules, failure conditions and
   immutable input/output contracts.
2. Dependency evidence: no invented historical accepted paths, fees,
   thresholds, regime cutoffs, parameter grids, held-out windows or post-hoc
   selection. R7 corrected control currently has zero accepted trades.
3. Data-integrity certificate against the actual immutable source features
   and contract-isolated bars. Missing provenance means **BLOCKED**, not PASS.
4. Reviewed runner and wrapper; synthetic/fixture tests and full regression.
   The wrapper must refuse absent/mismatched data identities.
5. Explicit `run N` or `rerun N` authorization after all gates pass.
   `prepare N`, registry edits and a Git push of this file never authorize
   experiment execution.

Planning/documentation, fixture-only tests and nonexecuting scaffolding may be
prepared in advance. A data-integrity failure prevents historical selection,
not drafting hypotheses. The GitHub Actions system currently supports single
explicit run requests; a durable unattended multi-experiment queue still
requires a separate implementation. Do not describe batch parsing as a running
persistent queue.

## Work sequencing while data is under audit

- **Now:** review and archive EXP-030; develop preregistrations for 031–034
  and causal segmentation contracts for 035–038. Missing values stay visibly
  pending; never create runnable placeholders.
- **After certified data and executable baseline:** finalize candidate choices
  and wrappers in dependency order. Use synthetic fixtures to validate code
  prior to historical runs.
- **After R7/R8 evidence:** freeze candidates, costs and robustness design
  for 039–044.
- **After robustness review:** freeze true holdout and walk-forward protocols.
- **After validation:** final comparisons and production acceptance, with an
  explicit separate deployment decision.

## Registry lifecycle

`PROPOSED -> SPEC_APPROVED -> PREPARED -> DATA_READY -> RUN_AUTHORIZED ->
RUNNING -> REVIEWED -> ARCHIVED` (or `BLOCKED`/`REJECTED` with reason).
Each stage must record its evidence paths, git SHA and decision owner. No
implicit transition from `PROPOSED` to `RUN_AUTHORIZED`.

This registry is intentionally separate from `phases.md` milestones and
historical experiment IDs. Update both only when justified by evidence.
