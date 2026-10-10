# 40 Research Index

## Experiments

- [[Experiments/EXP-001-Score-Band-Analysis]] — completed diagnostic of score-band behavior across 2023–2025.
- EXP-002–EXP-011 and EXP-013–EXP-021 — historical results archived; preserve their original producer semantics.
- EXP-012 — blocked by missing deterministic Order Block features.
- EXP-030 — prepared R7 family-policy diagnostic; not executed.

For the complete preparation inventory, blockers and continuation instructions,
see `docs/research/experiment_preparation_status.md`. No five-experiment batch is
specified after EXP-030 on the audited main checkpoint.

## Findings

See [[Findings/FINDINGS-INDEX]].

## Research rules

- Preserve the untouched baseline as the control.
- Test one hypothesis/parameter family at a time.
- Do not change scorer weights during diagnostic experiments unless the roadmap explicitly enters a calibration phase.
- Segment findings by year/regime and direction where relevant.
- Treat small samples as preliminary.
- Validate accepted improvements out-of-sample or walk-forward before production changes.

## Current R7 preparation — 2026-10-09

**2026-10-10 priority update:** Data acceptance takes precedence over additional
strategy selection. The read-only VPS source inventory is archived at
`research-archive/EXP-INTEGRITY-HISTORY-INVENTORY/`. Complete report: zero errors,
57 files / 19 distinct datasets, exact raw overlap, seven incoming contracts
with no earlier history and six with 960 unused Monday bars. No source repair,
external completeness certification or new feature build is claimed. Next locate
original/supplemental CSVs and normalized chunks, then establish session/context
coverage. See `docs/contract_history_inventory.md`.

The integrity-corrected control has zero accepted plans across 2023–2025. The
2023 read-only qualification diagnosis reproduces seven archived signal keys,
families and confirmation FVG identities. Of 659 candidates, 640 have no active
selected-family sequence, 12 have no fresh event, and seven qualify. One
continuation event is suppressed by documented reversal precedence; this alone
establishes no implementation mismatch or missed valid trade. No rule relaxation
or filter-only performance experiment is selected. Next evidence: two causal
minute windows from existing VPS features, including noncandidate rows.

See `docs/research/r7_next_step.md` and immutable
`research-archive/EXP-INTEGRITY-2023-QUALIFICATION/QUALIFICATION_REPORT.json`.
Historical R7.0 remains completed and rejected; do not rerun it.

The subsequent 62-row causal-window archive explains the two endpoint cases under
current documented rules; it establishes no sampled implementation defect. A
concrete confirmation-first family diagnostic proposal is pending strategy approval
in `docs/research/r7_family_policy_proposal.md`. Its 2023 flag arithmetic adds one
qualified continuation, not an accepted trade or profitability result. Current
rules and historical evidence are preserved; no further same-kind export is needed
before that decision.

The user approved the isolated confirmation-first family option. Implementation
and 824-test regression are complete; default behavior is retained. EXP-030 is a
prepared qualification/decision diagnostic using existing 2023 chronology files
and archived control evidence. It has not run; historical acceptance/P&L and
performance selection remain unknown. See
`docs/research/r7_family_policy_implementation.md`.
