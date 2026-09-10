# Research Archive

This directory is the permanent, Git-tracked archive of experiment evidence for `trade-alerts`.

## Purpose

Generated working reports live under `data/reports/EXP-XXX_*` on the VPS. Those directories remain gitignored because they may contain transient or large artifacts. Every completed experiment must copy its durable, reasonably sized evidence into this directory before the experiment can be marked complete.

Canonical layout:

```text
research-archive/
  EXP-001/
  EXP-002/
  EXP-003/
  ...
```

## Files that should be archived

Archive all reasonably sized research evidence, including:

- Markdown reports (`.md`)
- JSON results/metrics (`.json`)
- CSV tables/segmentations (`.csv`)
- YAML/YML config snapshots (`.yaml`, `.yml`)
- TOML/INI/TXT metadata where useful (`.toml`, `.ini`, `.txt`)
- hashes, manifests, and experiment metadata

The archive helper also writes `ARCHIVE_MANIFEST.json` containing SHA-256 hashes, sizes, and relative paths for every copied artifact.

## Files that should not be archived in normal Git

Do not copy large/generated binary datasets into normal Git, including:

- `.parquet`
- `.feather`
- `.arrow`
- raw minute/tick datasets
- processed market-data caches
- virtual environments
- logs
- secrets or credentials

If a future experiment genuinely requires preserving a large binary artifact, use an explicit large-file/artifact-storage decision rather than silently committing it to normal Git.

## Completion gate

An experiment is not complete until all of the following are true:

1. The experiment has been executed against the authoritative data.
2. The working report exists under `data/reports/...` (or an equivalent run directory).
3. Durable outputs have been archived into `research-archive/EXP-XXX/`.
4. `ARCHIVE_MANIFEST.json` exists and hashes the archived files.
5. The experiment note in `trade-brain/40-Research/Experiments/` has been updated.
6. Supported findings and the findings index have been updated.
7. `refine-roadmap.md` has been updated with proven completion evidence.
8. Relevant tests have passed.
9. The archive, code, tests, trade-brain notes, and roadmap changes have been committed and pushed to GitHub.

## Helper

Use:

```bash
python scripts/archive_experiment.py \
  --experiment EXP-003 \
  --source data/reports/EXP-003_setup-family 
```

The helper copies only approved text/research formats by default and refuses obvious secret-like filenames. Use `--dry-run` to preview what would be archived.
