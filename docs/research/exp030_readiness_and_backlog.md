# EXP-030 execution readiness and R7–R12 specification backlog

Updated 2026-10-09. Inspected main at
`70451c8521474aa671ac74a536805daa92019d64`. Documentation only; no experiment
execution, SSH connection, strategy change or run-request modification.

## Readiness decision

### Execution attempt — 2026-10-10

This entry supersedes the operational status in the original audit below.
The user explicitly authorized `run 30`. Request `EXP-030-r01-20261010`
was committed to main at `fc1e8c2be3989df70cb5923ee765da70d26c1534`.
[Actions run 38061224851](https://github.com/jenozu/trade-alerts/actions/runs/38061224851)
completed with failure. Checkout, request validation and SSH configuration
passed; the remote execution step failed with
`Permission denied (publickey,password)` and exit code 255.

The SSH server was reachable, but login was rejected before any remote command
ran. VPS pytest and the EXP-030 wrapper did not start. No research results,
VPS run manifest or downloadable run artifact were produced. EXP-030 remains
prepared and unexecuted; research review and dependent specifications remain
pending. User-provided terminal evidence before this attempt showed a clean
main checkout at `26cfb40`, an executable project venv and an existing chronology
source; workflow validation of these prerequisites has not occurred.

Next resolve account/key authorization: confirm the Actions username, match
the private key's derived public-key fingerprint to the selected account's
authorized keys, check SSH file ownership/permissions and server policy.
Do not disclose private keys or commit credentials. The active request is
preserved as the failed attempt; documentation changes do not trigger execution.
After access is corrected, an explicit `rerun 30` must create a new unique
request ID. Do not treat this infrastructure failure as a research outcome.

**EXP-030 is code-prepared and compatible with the existing dispatcher. VPS
operational readiness is unverified, not failed.** No further trading-rule
decision is needed to run this already approved diagnostic. Specifications for
EXP-031 onward are not prerequisites for EXP-030.

| Prerequisite | Evidence / current status |
| --- | --- |
| Approved research variant | `r7_family_policy_proposal.md`: confirmation-first policy approved for implementation/testing. |
| Implementation / wrapper | On main; all seven code/test hashes in the preparation TEST_REPORT match. Wrapper shell syntax passes. |
| Regression | Last local full suite: 824 passed, 967 warnings. No code has changed since that check. Workflow runs its own VPS pytest preflight. |
| Workflow / dispatcher | Main push restricted to `run-requests/current.json`; matching committed wrapper only; exact triggering SHA enforced. |
| GitHub Actions enabled / SSH configured | Not verified. Read-only repository Actions-runs endpoint returned zero total runs at inspection; this gives no end-to-end proof. Secrets cannot be inspected with available tools. |
| VPS checkout / venv / source access | Not inspected; requires checks below. |
| Explicit execution authorization | Not provided in this task; request remains idle. A separate `run 30` instruction is required. |
| Results review / permanent archive | Pending execution. Workflow uploads a temporary run record; it does not commit a permanent research archive. |

The absent SSH/VPS verification is an infrastructure unknown. It is distinct
from the zero-trade corrected control, which is the diagnostic's research context
and does not prevent EXP-030 from running. Actual fee selection and future
holdout design are later performance-research prerequisites, not requirements
for this frozen diagnostic.

## Personal setup checklist

Complete only checks not already verified; do not rotate/recreate working keys
or rebuild data merely because this conversation cannot see their status.

1. In repository **Settings → Secrets and variables → Actions**, confirm these
   repository secrets exist: `TRADE_VPS_HOST`, `TRADE_VPS_USER`,
   `TRADE_VPS_SSH_KEY`. Host identifies the VPS, user is the SSH account, and key
   contains its private SSH key. Keep values in GitHub; do not paste them into
   chat, commits or command output. Its public key must already authorize the
   selected account on the VPS. Confirm Actions is enabled/permitted.
2. Confirm the VPS permits this account's noninteractive SSH on the workflow's
   default port 22, Git fetch from origin, read access to the locked source and
   historical configs, and write access to the source's parent directory and
   `/docker/trade-alerts/.automation-runs`. Source is under `/root`; account
   permissions must therefore actually cover that path.
3. Confirm `/docker/trade-alerts` is the project's Git checkout on `main`, with
   a clean `git status --porcelain` including untracked files, and no local
   commits/divergence that would prevent fast-forward. Do not reset or delete
   changes to make this pass. The workflow fetches/fast-forwards itself; a manual
   pull is not inherently required. `.venv/bin/python` must exist with the
   existing `requirements.txt` dependencies. Do not globally install packages.
4. Confirm the exact chronology source below and **every non-code file referenced
   by its lock** remain present/readable, unchanged from the preserved build.
   Original producer commit objects must remain available in the project Git
   history; the runner reads their blobs with `git show`. Do not relocate files
   or regenerate locks to bypass missing evidence.
5. After these checks, give the separate instruction `run 30` when ready to
   authorize execution. This document does not create that request. Neither a
   documentation push nor the GitHub Actions Run button substitutes for the
   documented request-based workflow (there is no workflow_dispatch trigger).

If the venv or source is missing, retain the reported failure and obtain a
specific setup/recovery plan before execution. There is no authorized automatic
cleanup, source rebuild, path substitution or requirement relaxation.

### Optional read-only VPS check

Run in the existing VPS terminal **as the account named in TRADE_VPS_USER**.
This reads metadata and checks access; it does not run a wrapper, rehash all data,
create outputs, fetch/pull, change a request or certify data integrity. An initial
failure identifies which setup item needs attention. Do not share secret values.

```bash
cd /docker/trade-alerts
.venv/bin/python - <<'PY'
import importlib
import json
import os
from pathlib import Path
import subprocess

def check(ok, message):
    if not ok:
        raise SystemExit('FAIL: ' + message)
    print('PASS: ' + message)

root = Path.cwd()
git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
check(git('branch', '--show-current') == 'main', 'checkout branch is main')
check(not git('status', '--porcelain'), 'checkout is clean including untracked files')
print('Checkout SHA:', git('rev-parse', 'HEAD'))
check((root / 'automation/experiments/EXP-030.sh').is_file(), 'EXP-030 wrapper exists')
for name in ('pandas', 'numpy', 'yaml', 'pyarrow', 'pytest', 'tzdata'):
    importlib.import_module(name)
    print('PASS: dependency import', name)
source = Path('/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/chronology')
for name in ('LINKED_SEQUENCE_SUMMARY.json', 'LINKED_OUTPUT_LOCK.json'):
    check((source / name).is_file() and os.access(source / name, os.R_OK),
          'chronology ' + name + ' readable')
lock = json.loads((source / 'LINKED_OUTPUT_LOCK.json').read_text())
producer = lock['identity']['git_commit']
for role, item in lock['artifacts'].items():
    if role.startswith('code:'):
        subprocess.run(['git', 'cat-file', '-e', producer + ':' + role[5:]], check=True)
    else:
        path = Path(item['path'])
        check(path.is_file() and os.access(path, os.R_OK), 'locked file readable: ' + role)
check(os.access(source.parent, os.W_OK | os.X_OK), 'fresh sibling output can be created')
check(os.access(root, os.W_OK | os.X_OK), 'project root permits run directory creation')
runs = root / '.automation-runs'
if runs.exists():
    check(runs.is_dir() and os.access(runs, os.W_OK | os.X_OK), 'run directory writable')
print('Metadata checks complete; SSH connectivity, fast-forward and full hashes are not certified.')
PY
```

## What EXP-030 answers

The single controlled change is `confirmation_first_family_v1` instead of the
default context-first family selection. Reversal retains precedence when both
families are confirmed. Sequence/event freshness, score, entry timing, stop,
obstacle, targets, costs and management stay frozen.

| Research question | Evidence to review |
| --- | --- |
| Do the seven original 2023 decisions remain identical? | Wrapper comparator removes only the explicit policy annotation and compares each decision against the archived control. |
| Is the additional signal exactly the specified continuation? | `additional_decisions`: NMU23 short, 2023-08-24 13:45 UTC; no other additions permitted. |
| Does that signal pass planning, or which unchanged constraints reject it? | Its complete plan/candidate/rejections in `decisions.json` and `FAMILY_POLICY_COMPARISON.json`; aggregate rejection counts overlap. |
| Does an accepted standalone plan become an executed diagnostic trade? | Summary's accepted_plans versus simulated_trades, optional ledger; side tie/one-position policy can distinguish these counts. |
| Does actual simulated execution reproduce the independent shared plan? | `executed_plan_parity_checked` and execution_plan in the diagnostic ledger; no accepted-path claim if no trades. |
| Are the compared input/config identities genuinely the same apart from policy? | Input/output locks, effective config, preserved-source verification and wrapper comparison assertions. |

The audit reads the existing 2023 segments and recomputes opted-in qualification;
it simulates segments only if they have accepted plans. It does not rebuild
upstream features or rerun the empty control. Any P&L is bounded diagnostic
evidence, with frozen uncertified actual fees. One signal/trade does not establish
edge, useful sample size, cross-year stability, or production suitability.

## Execution and review handoff

On a later explicitly authorized `run 30`, the agent follows CHATGPT_COMMANDS:
create a unique request, push it to main, observe Actions preflight/SSH/runner,
and retrieve the run record. A moving main head or dirty VPS may reject the
exact-SHA/fast-forward check; resolve the cause without force/reset.

Small results reside in `.automation-runs/<request_id>/`; full fresh sibling
diagnostic output is named `EXP-030-<trigger SHA>-<request_id>`. Actions artifact
retention is 30 days. The evidence bundle includes comparison, summary, decisions,
effective config, both locks, optional diagnostic ledger, dispatcher manifest and
run log. Preserve reasonably sized results/config/locks in a new
`research-archive/EXP-030/` using `scripts/archive_experiment.py`, per RULES.md.
Keep the existing EXP-030-PREPARATION record intact. Logs remain outside normal
Git. Archiving/review is a follow-up task; the wrapper does not complete it.

Review outcomes must distinguish:

- **Infrastructure or identity failure:** no valid research conclusion. Inspect
  the log and failed prerequisite; do not interpret missing results as rejection
  of the research hypothesis. Rerun needs separate authorization.
- **Diagnostic completed, extra plan rejected:** record the exact unchanged
  constraints. Preserve zero-plan evidence; no automatic relaxation.
- **Plan accepted but no trade executed:** inspect side selection/position
  behavior before claiming historical execution proof.
- **Diagnostic trade executed with plan parity:** establishes this bounded path
  only. Review trade/config/locks, then decide whether a larger comparison is
  justified; no automatic performance selection or promotion.
- **Comparator drift:** experiment fails its preservation contract even if
  the diagnostic wrote files. Investigate before selecting any future candidate.

After reviewing, record an evidence-based decision and limitations, archive hashes,
triggering SHA and input identities; update the EXP-030 research note/index,
refinement roadmap and canonical milestone before marking it complete.

## Proposed R7–R12 specification backlog

These are **proposed specification work packages**, not assigned experiment IDs,
approved parameters, or runnable definitions. All objectives come from
`refine-roadmap.md` sections 11–16 and its discipline/report sections 3/17.
The detail needed to convert them into experiments is separated below. No
EXP-031 onward is created. No numerical success threshold is invented.

| Work package | Documented objective / established constraints | Proposal or decision still requiring approval | Dependency |
| --- | --- | --- | --- |
| R7 next comparison | Isolated interactions supported by completed component evidence; incremental expectancy/PF/drawdown/MFE/MAE/trade-count and yearly stability. Preserve corrected execution and causal inputs. | Select an executable control with meaningful coverage and exactly one candidate change; preregister sample/decision criteria. A confirmation stack is conceptual, not a mandate to add every component. | EXP-030 reviewed; zero-control limitation addressed explicitly. |
| R7 subsequent interactions | Level reaction/break, retest, RVOL, HTF, sweep, displacement, structure, FVG, DOL, premium/discount, SNR and room-to-target are listed objectives. | Which interaction follows, feature availability, exact values and freeze/attribution contract; do not automatically reuse rejected R7.0. | Previous isolated evidence and approved preregistration. |
| R8 causal regime segmentation | Volatility, trend/range, SNR, overnight/premarket ranges, gap; optionally news with deterministic data. Family-specific conditions and pre-entry causality. | Exact classifier fields, cutoffs, lookback/availability and missing-data policy; optional news source. Start as segmentation, not an approved entry filter. | Review applicable control/candidate identities; meaningful data/ledger coverage. |
| R9 stratified stability | Year/month, long/short and setup-family robustness; expose concentration and broken subgroups. | Frozen candidate list, comparable controls and quantitative interpretation/sample requirements. Reuse existing segmentation utilities where compatible. | Selected development candidates and their evidence; R8 definitions for later regime reports. |
| R9 parameter sensitivity | Neighboring parameters should support plateaus rather than isolated optima. | Which already chosen parameter to perturb and exact grid; the roadmap's RVOL numbers are an illustrative example, not an approved sweep. | Frozen candidate and isolated parameter contract. |
| R9 realistic costs | Realistic MNQ fees/slippage; edge must survive costs. Existing accounting/units stay unchanged. | Actual account fee schedule, quantity/point-value context and stress assumptions. | Frozen candidate, executable accepted paths and fee evidence. |
| R9 outlier dependence | Report performance with/without largest winners. | Exact exclusion counts/fractions and tie/order handling, fixed before evaluation. | Comparable locked ledgers; no altered entry rules. |
| R10 held-out validation | Development/calibration separate from untouched validation; no repeated tuning on validation. Existing policy labels 2023–25 development and 2026 pseudo out of sample. | Specific proven-unexamined period, freeze identity, start/end and criteria. No relabeling already inspected history as untouched. | Candidate freeze and R9 review; dataset policy evidence. |
| R10 walk-forward | Freeze earlier-period candidate and test next unseen window, roll and aggregate. | Training/validation lengths, step, warmup, embargo if needed, permitted calibration method and aggregation; none assigned by conceptual diagram. | Approved window/data protocol and candidate/calibration contract. |
| R11 final comparison | Baseline, best entry-quality, best scoring, best exit, combined candidate; only independently supported changes may combine. Reports cover family/direction/year/bands/time/regimes/drawdown/costs/validation. | Actual variants and combination after independent evidence, with equivalent execution/control identities. Historical R4–R6 winners are leads, not proof for the corrected contract. | R7–R10 reviewed evidence; resolve missing R4-06 archive before relying on it. |
| R12 acceptance evidence | Hypothesis, sample, expectancy/PF/risk, stability, outliers, score discrimination, redundancy, sensitivity, costs, validation, shadow/live consistency, final config/archive. | Quantitative gates where unspecified and separate promotion decision; no automatic deployment. | Final comparison and Phase 11 evidence. |

EXP-030 directly informs the **first R7 control/candidate choice** and whether a
larger confirmation-first comparison is warranted. It does not itself choose
regime cutoffs, costs, sensitivity grids, holdout windows or a final candidate.
Those design decisions can be drafted independently, clearly marked proposed;
performance execution depends on frozen usable candidates/evidence.

No batch of five is currently preregistered. Once R7 review establishes the next
contract, assign approved IDs in dependency order and prepare executable batches
of five. Specification drafting may proceed before all upstream outcomes exist;
candidate-dependent values remain explicit pending fields. This distinction avoids
blocking all planning while also avoiding invented runnable strategy semantics.

## Validation and scope

- All seven EXP-030 prepared code/test hashes match TEST_REPORT; bash syntax passes.
- Prior full suite remains 824 passed / 967 warnings; no redundant full regression
  for documentation-only changes.
- Optional setup block parsed as Python and Bash without executing it.
- Backlog checked against documented R7–R12 objectives; no assigned EXP IDs or
  strategy parameters introduced.
- Run-request hash remains
  `72a02a1e5c34891cc1f7ab54d1592697cb4eaa16636f3b88119cd22bb9d0898c`.
- No secrets, VPS state or SSH connectivity are certified by these checks.
