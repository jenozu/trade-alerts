# Integrity engineering closeout — 2026-10-09

Decision: implementation, qualified fidelity audit and yearly execution-evidence
archiving are complete on the review branch. PR #7 is ready for review; it is
not a deployment or permission to start a selection experiment. Main publication
and roadmap sync remain separate next actions.

## Validation

An isolated local checkout was reconstructed from the GitHub integration head
6435d3a87e32495f9baca77a50faa6b72d9372b0. Its full Git tree matches exactly:
9a967cbb4e8d952e4810b5da8b687a24ba1afb00. Full regression passed:
**786 passed, 872 warnings in 48.93 seconds**. The tested tree remained clean.
Warnings include existing NumPy/pandas compatibility and fragmentation warnings.
Subsequent closeout edits are documentation only.

The authoritative execution files for 2023, 2024 and 2025 are retained under
research-archive/EXP-INTEGRITY-{year}-DIAGNOSTIC. Both original lock identities
verify for every year. Exported summary, decisions and effective-config hashes
and byte sizes match producer output locks; 68 code-file hashes match the
integrity checkout. All 21 archived evidence-file hashes verify against the
three archive manifests. No source features or yearly audits were regenerated.

| Year | Source rows including context | Eligible signals | Accepted plans | Simulated trades |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 440032 | 7 | 0 | 0 |
| 2024 | 441600 | 2 | 0 | 0 |
| 2025 | 441015 | 7 | 0 | 0 |

## Completion scope

The five requested tasks have implementation/audit evidence: commission/net
accounting, covered execution invariants, formal dataset classification,
immutable input identities and a qualified strategy-fidelity audit. The current
assessment in PRE_CRITICAL_FIXES_RESULTS.md records their individual limits.
Contract-isolated features and object-linked chronological confirmations prevent
cross-contract state leakage in the corrected diagnostic path. Shared market
planning uses actual next-open entry references, structural risk and real
liquidity objectives. Accepted fixtures cover both directions and setup families.
Existing defaults, producer histories and frozen research results are preserved.

## Limits carried into review

- Zero accepted historical trades prove rejection behavior, not historical
  accepted execution, profitability or equivalence to live alerts. Synthetic
  accepted-path tests are separate evidence.
- Production zone-hypothesis alerts are not migrated to actual next-open market
  execution. Missing-path fills and session liquidation remain uncertified.
- Original 2023 producer provenance remains unavailable where recorded.
  VPS-only upstream files were not independently reopened locally; original
  lock paths and recorded VPS verification are retained without invented facts.
- Diagnostics use disabled commissions and quantity one. Account-specific fees
  must be documented before realistic net-performance claims. Cost conversion
  and accounting correctness are tested independently of fee selection.
- 2023–2025 remain development data. No untouched 2026 holdout or true forward
  freeze is claimed.
- The optional internal-equal-liquidity proposal is deferred. Keeping existing
  rules and documenting their limits completes the audit without manufacturing
  accepted trades or silently optimizing strategy.

## Next action

Review and merge PR #7's qualified engineering checkpoint, then sync the roadmap.
Do not deploy automatically. R5/R6/R7.0 are already reconciled on main and must
not be repeated. Before any next R7 selection run, preregister its executable
control and candidate identities and acknowledge the zero-trade corrected
contract. Preserved historical controls cannot certify the corrected contract;
any future experiment must state exactly which contract it evaluates.
No additional yearly build, full regression or VPS diagnostic rerun is needed
for this closeout unless new code or evidence changes the verified scope.
