# 2023 R7 qualification diagnosis — 2026-10-09

Read-only diagnosis of existing VPS chronology features, not a new experiment.
The supplied BEGIN_R7_2023_FLAGS export contains 659 unique directional score
candidates. qualification_export.txt preserves its compressed payload; decode
with base64 then gzip to obtain the original JSON bytes. The report records the
decoded SHA-256 and source attachment SHA-256. No new input lock is invented.

The real apply_sequence_contract and confirmed_setup_family APIs reproduce all
seven archived decision keys AND their confirmation FVG identities exactly.
All candidates pass completion and entry-window checks. Earliest failures:
640 have no active sequence for their selected family, 12 have an active sequence
but no fresh event, and seven qualify. Family selection is reversal for 566 and
continuation for 93. These are candidate rows, not trade counts.

The short NMU23 candidate at 2023-08-24 13:45 UTC has a continuation event with
hold 13:43, retest 13:44 and confirmation 13:45, but recent buy-side sweep selects
reversal. The reversal sequence is absent. This follows setup_family_contract.py
and the family precedence documented in docs/strategy_fidelity_audit.md. No
implementation mismatch is established by that suppression; changing precedence
would change strategy semantics. No proposed fallback is implemented.

The sampled flags do not explain why raw sequence generation is mostly inactive:
that requires the preceding completed minute bars and event context, including
noncandidate rows. The next check is a narrow read-only export of two causal
windows, not another yearly build or simulation. See docs/research/r7_next_step.md.

The original archived seven planner decisions remain unchanged and rejected.
This evidence does not certify complete sequence history, accepted-path parity,
profitability, or a meaningful filter-only R7 comparison. The previous 805-test
code baseline remains unchanged; this documentation/evidence task was validated
by decoding, schema/identity checks, production API reproduction and SHA checks.
