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

## Workflow rule

When an experiment is completed:

1. Update its experiment note.
2. Create or update finding notes supported by its results.
3. Update `FINDINGS-INDEX.md` and `Research-Index.md`.
4. Update `refine-roadmap.md` only with proven completion evidence.
5. Record any accepted strategy/configuration change under `30-Decisions/`.
6. Keep large generated CSV/JSON/Parquet artifacts out of Git; reference their immutable paths/hashes instead.
