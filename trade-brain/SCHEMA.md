# Trade Brain Schema

## Purpose

Keep research knowledge durable, linked, evidence-backed, and separate from generated artifacts.

## Sections

- `00-Inbox/` — uncategorized notes to triage.
- `10-Strategy/` — current strategy concepts, rules, scoring model, setup families.
- `20-Architecture/` — system architecture and implementation notes.
- `30-Decisions/` — validated project/research decisions and rationale.
- `40-Research/` — experiments, hypotheses, findings, and research indexes.
- `50-Backtests/` — baseline/run summaries and links to archived evidence.
- `60-Data-Sources/` — ProjectX, Barchart, rollover and data-quality notes.
- `70-Project-State/` — current checkpoint/handoff state.
- `90-Sources/` — source references, config baselines, external/reference material.

## Experiment note standard

Every experiment should record:

- Experiment ID and title
- Status
- Hypothesis/question
- Control/baseline
- Inputs and artifact paths
- Method
- Metrics required
- Results
- Interpretation
- Limitations
- Decision
- Links to resulting findings
- Next experiment

## Finding note standard

Every durable finding should record:

- Finding ID and concise statement
- Status: `preliminary`, `supported`, `validated`, `rejected`, or `superseded`
- Source experiment(s)
- Evidence/metrics
- Interpretation
- Limitations
- What would falsify or strengthen it
- Related findings/decisions

## Evidence rule

Do not convert an observation into a validated finding without sufficient evidence. Preserve sample-size limitations and year/regime instability explicitly. Never present the confluence score as a probability unless it has been separately calibrated and validated as one.

## Permanent evidence archive

`trade-brain/` stores human-readable research knowledge. The underlying durable experiment outputs are preserved separately under:

```text
research-archive/EXP-XXX/
```

Working VPS outputs may remain under gitignored paths such as `data/reports/`, but every completed experiment must copy all reasonably sized research evidence into `research-archive/EXP-XXX/` and commit it to GitHub.

Expected archived evidence includes Markdown, JSON, CSV, config snapshots, manifests, hashes, and other small text artifacts. Large Parquet/Arrow/Feather files, raw market data, processed caches, logs, secrets, tokens, and credentials remain outside normal Git.

Every archived experiment must contain `ARCHIVE_MANIFEST.json` with SHA-256 hashes and sizes for the copied artifacts. Use `scripts/archive_experiment.py` for this step.

## Workflow rule

When an experiment is completed:

1. Run the experiment against the authoritative dataset/ledger.
2. Preserve the working outputs under the appropriate VPS run/report directory.
3. Run `scripts/archive_experiment.py` to copy durable evidence into `research-archive/EXP-XXX/` and create `ARCHIVE_MANIFEST.json`.
4. Update the matching trade-brain experiment note.
5. Create or update finding notes supported by its results.
6. Update `FINDINGS-INDEX.md` and `Research-Index.md`.
7. Update `refine-roadmap.md` only with proven completion evidence.
8. Record any accepted strategy/configuration change under `30-Decisions/`.
9. Run relevant tests.
10. Commit and push the archive, code, tests, trade-brain notes, and roadmap changes to GitHub.

An experiment must not be marked complete before the tracked research archive and manifest have been pushed.
