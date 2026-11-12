# Decision (APPROVED 2026-11-11): batch approval of experiment queues

**Status:** approved by owner 2026-11-11. RULES.md §17a added 2026-11-12. Allowlist remains empty until a wrapper qualifies.

## Change being proposed

Today each experiment run needs its own explicit `run N` command and its own
committed `run-requests/current.json`. With the queue runner, one approval —
committing a queue file such as `automation/queues/QUEUE-001.yaml` and starting
it on the VPS — would authorize **every item in that file**, run back to back
without further confirmation between items.

## What stays the same

- Only reviewed wrappers run, and only those in a code-level allowlist.
- No arbitrary commands; each item still goes through `execute_run_request.py`
  with full pytest, exact commit and duplicate request-ID checks.
- The list is fixed in advance; nothing is added, reordered or chosen based on
  earlier results. Pass/fail is decided by Python, never by a language model.
- Any failure halts the queue; nothing is retried automatically.
- Holdout / pseudo-out-of-sample years are refused.

## What changes / risks to weigh

- Later items run without you looking at earlier results first. This is the
  point (no adaptivity), but it also means an issue that only shows up in a
  result, not a failure, will not stop the queue.
- Queue runs are started on the VPS directly, not through GitHub Actions, so
  there is no automatic GitHub run record or Actions artifact for them.
- If approved, RULES.md §17 would need an owner-written amendment stating that
  a committed queue file plus an explicit "run queue QUEUE-NNN" command counts
  as authorization for each listed item. This PR does not edit RULES.md.

## Owner decision

- [x] Approve  - [ ] Reject  - [ ] Approve with changes: ______
