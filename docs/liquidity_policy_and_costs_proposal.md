# Remaining fidelity decisions: liquidity policy and actual costs

**Scope correction — 2026-10-09:** This proposal is deferred and is not a required
Manus engineering fix or a prerequisite to documenting the integrity checkpoint.
The current liquidity policy remains unchanged. No proposed rule is implemented.
Actual account fees are required before claiming realistic net performance; they
are not a blocker to accounting-engine verification or archiving completed
diagnostics. The earlier proposed gates below are retained as proposal history,
not as the current work order. See the current assessment in
`research_resume_readiness.md` for the next task.


Status: proposed specification, not an implemented or frozen strategy contract.
Prepared 2026-10-09 after reviewing the seven corrected 2023 rejection records.
No historical profitability or 2026 outcome was used to choose this proposal.

## Why this needs an explicit decision

The current shared planner uses the nearest directional objective as a hard
obstacle. It also preferentially selects the nearest internal objective as TP1.
Five of seven 2023 first obstacles were internal equal highs/lows only 0.25–1.75
points ahead. Merely skipping them in the obstacle check still leaves them
selected as TP1, failing its reward/risk check. Both uses must be addressed
consistently if the intended model permits intermediate liquidity.

The written project materials describe opposing liquidity as a target and
distinguish engineered/internal liquidity from protected structure. They do not
define a fully executable weak/strong level classifier. The main-branch context
principles likewise distinguish draws from reaction zones without giving that
classifier. Neither proximity nor an equal-high label proves price will pass a
level. This proposal is an explicit modeling choice, not a demonstrated bug fix.

## Smallest proposed policy

Use a new opt-in policy named `internal_equal_liquidity_intermediate_v1`;
retain the current policy as the default and preserve all old diagnostics.

1. Only objectives with source `nearest_equal_high` or `nearest_equal_low` and
   category `internal`, with neither HTF nor external-liquidity classification,
   qualify for this intermediate treatment. Do not generalize to all swings,
   VWAP, confluence zones, session levels, PDH/PDL or weekly levels.
2. If such an objective is closer than the existing minimum room of 25 points,
   retain it in the decision as intermediate liquidity. Do not let it alone
   reject room-to-first-obstacle, and do not select it as TP1 or TP2. This uses
   the existing room requirement, not a newly fitted distance threshold.
3. All other objectives retain their existing obstacle/target treatment. An
   internal equal pool at or beyond the minimum room retains its current role.
   Do not invent a protected/weak classifier from labels that lack that evidence.
4. The selected primary DOL remains authoritative. If it is a nearby internal
   pool, continue rejecting insufficient primary-DOL room; do not silently
   switch to a farther DOL merely to allow entry.
5. Select TP1/TP2 from the remaining real objectives using the existing priority
   and strictly-before-primary-DOL conditions. Preserve minimum TP1 asymmetry.
   Missing TP1 or external TP4 continues to reject. Never manufacture fixed
   targets, promote the primary target to TP1, or alter runner management.
6. Preserve the 25-point structural risk cap, source-level prices, chronology,
   entry window, next-open timing, slippage, score weights and thresholds.
7. Apply one policy through the shared planner/backtest API, persist policy ID
   and intermediate-level explanations in decisions, and fingerprint it with
   effective configuration. Never change the producing source features.

This intentionally leaves many existing rejections intact. A goal of obtaining
accepted trades is not a justification for broadening the policy.

## Verification sequence after the decision

1. Add failing deterministic tests for both directions: near equal liquidity
   becomes intermediate only in the opt-in policy; default output stays exact.
2. Test that nearby selected DOL, HTF/external classification, confluence zones,
   missing targets, invalid stops and oversized stops still reject. Verify
   intermediate levels remain observable and do not become TP1 accidentally.
3. Check real shared planner/backtest parity, causal/future invariance, policy
   validation and input locks; run relevant tests followed by the full suite.
4. Commit/publish the tested change before VPS work. Reuse completed chronology
   features for a fresh locked execution audit; do not rebuild raw/features or
   overwrite prior execution outputs. Evaluate only development years.
5. Review actual decisions and compare accepted plan fields with executed
   ledger fields if accepted trades exist. A zero-trade result remains valid
   diagnostic evidence and cannot certify historical accepted execution.

## Actual-fee input required

Obtain the all-in fee for the account intended for this baseline. Record:

- provider/account type and instrument (MNQ, not NQ);
- currency, fee schedule date and source (account statement or fee page);
- whether the quoted fee is per side or per complete round trip per contract;
- whether exchange, clearing, regulatory and broker charges are included;
- quantity to model, explicitly confirmed rather than copied from past chats.

No fee value was present in the supplied strategy materials. The completed
diagnostics used commissions disabled, quantity 1 and configured point value 2.
Do not label those costs realistic or verified. Do not guess an account's fee
from a general advertised price. Public schedules can be supporting evidence;
the correct account/plan still needs identification.

For an all-in round-trip fee of C dollars per MNQ contract and configured point
value 2 dollars/point, commission is C/2 price points per contract. For quantity
Q, position commission is C*Q dollars. A per-side quote F gives C=2*F only when
both sides have that charge and all additional fees are included.
Slippage is already applied to fill prices and is not deducted a second time.
These formulas describe the existing tested accounting contract, not new code.

## Baseline gate

After semantics, accepted-path verification and actual cost inputs are settled,
freeze the chosen effective configuration and inputs, generate a separate
corrected baseline, retain old baseline artifacts, and archive reasonably sized
summaries/decisions/configs/manifests in Git. Do not select policy, thresholds or
fees by comparing historical P&L. Record any absent historical accepted-path
proof honestly rather than changing the model to produce it.

R7 remains paused until the checkpoint is reviewed and the required evidence is
complete. This proposal itself is not permission to resume strategy selection.
