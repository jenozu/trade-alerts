# ChatGPT Command Shorthand

This file defines the compact commands the user can use with an AI agent working on
`jenozu/trade-alerts`.

The words below are user-interface shorthand. They do **not** redefine Git itself.

## Core Git / engineering commands

| User command | Required behavior |
| --- | --- |
| `status` | Inspect branch, latest commit, working/repository state, relevant tests/workflows, and report what is ready. Make no changes. |
| `diff` | Summarize changes since the previous committed checkpoint. Make no changes. |
| `commit` | Commit the coherent changes from the current task. Do not push unless requested. |
| `commit "message"` | Commit with the requested message. Do not push unless requested. |
| `push` | Commit the current coherent, tested task if needed, then push it to the intended GitHub branch. **Never execute a research experiment.** |
| `pull` | Safely bring the relevant checkout up to date using fast-forward-only behavior. Do not execute research. |
| `sync` | Check local/GitHub state, safely fast-forward where appropriate, and report whether they are aligned. |
| `test` | Run the normal automated tests. Do not execute a research experiment unless the tests themselves require it. |
| `save point` | Create a clearly labelled checkpoint commit before risky work. |
| `what changed` | Give a plain-English summary of changes since the previous checkpoint. |
| `next` | Determine the next roadmap task and proceed with everything that does not need user input. |

## Research commands

Experiment numbers are normalized. These all refer to the same experiment:

```text
1
exp1
EXP-001
```

| User command | Required behavior |
| --- | --- |
| `prepare 1` | Prepare EXP-001 code, config, wrapper commands, tests, and documentation. Do **not** execute it. |
| `run 1` | Explicit authorization to execute the prepared EXP-001 wrapper on the trading VPS. |
| `rerun 1` | Execute the same prepared experiment again without silently changing its experiment logic/config first. |
| `status 1` | Inspect the most recent EXP-001 automation/workflow state and report queued/running/passed/failed. |
| `logs 1` | Retrieve/summarize the most recent EXP-001 automation logs. |
| `results 1` | Retrieve and analyze the most recent durable EXP-001 outputs that are available. |
| `compare 1 2` | Compare experiment definitions and results without changing either experiment. |

## Critical semantics

1. **Push never means run.** A Git push must not execute a research experiment unless the pushed change is an explicit run request created because the user said `run N` or `rerun N`.
2. **Run is explicit authorization.** Never infer `run N` from `prepare N`, `push`, `next`, `test`, or ordinary code changes.
3. **No arbitrary remote shell from a run request.** The run request identifies an experiment only. Executable commands live in a reviewed, committed allowlisted wrapper at `automation/experiments/EXP-NNN.sh`.
4. **No force/reset cleanup.** Follow `RULES.md` and preserve unknown VPS changes.
5. **Strategy ambiguity still stops execution/change.** The command layer does not override the strategy guardrails in `RULES.md`.

## How `prepare N` works

For an experiment to be runnable, the repository must contain:

```text
automation/experiments/EXP-NNN.sh
```

That wrapper contains the exact VPS commands for the experiment: inputs, Python runner,
output locations, validation, and any small artifacts that should be copied to
`$AUTOMATION_RUN_DIR`.

Preparing an experiment may also create/update the Python research code, configs, tests,
or archive metadata it needs. Preparation itself does not touch
`run-requests/current.json`.

## How `run N` works

After confirming the experiment wrapper is prepared, the agent updates:

```text
run-requests/current.json
```

with an explicit request such as:

```json
{
  "action": "run",
  "experiment": "EXP-001",
  "request_id": "EXP-001-r01",
  "requested_by": "chatgpt",
  "note": "Run prepared EXP-001"
}
```

and pushes that request to `main`.

The GitHub Actions workflow then:

1. validates the request;
2. connects to the trading VPS over SSH;
3. refuses to overwrite a dirty tracked working tree;
4. fast-forwards `/docker/trade-alerts` to the triggering commit;
5. verifies the exact Git SHA;
6. runs the normal test preflight;
7. executes only the committed allowlisted experiment wrapper;
8. stores a manifest and run log under `.automation-runs/<request_id>/`;
9. copies that small run record back to the GitHub Actions run as an artifact.

Changing `current.json` to a new unique `request_id` is what makes a rerun explicit.

## Command examples

```text
prepare 22
diff
push
run 22
status 22
logs 22
results 22
```

The expected interpretation is: build EXP-022, review it, push its code, explicitly run it,
then inspect execution and results.
