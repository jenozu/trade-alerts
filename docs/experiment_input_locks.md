# Experiment input locks

Create locks from a **clean committed code/config checkout** before running an
experiment. Use existing ledgers/certified caches. This utility hashes files in
chunks; it never runs feature generation or imports a pipeline. Preserve raw/cache
bytes outside Git; a digest identifies content but does not preserve it.

Create a JSON spec with experiment_id, files (role → path), years, contracts,
counts (bars/candidates/trades, null for unknown), settings (execution/cost/slippage),
optional archive_identifier and unavailable (explicit reasons for missing provenance).
Required config roles are strategy, sessions, research_policy. At least one ledger
or scored_cache role is required. Use ledger_YEAR for several yearly ledgers, and
include cache metadata, requirements and source/archive manifests where available.
Contracts/counts/settings must be checked against producer metadata: these are
recorded declarations, not reconstructed facts. Candidate count means directional
eligible signals; trade count means actual resulting ledger rows. Source config
for old ledgers means the **original producer config**, not today's config. If that
is unavailable, record the limitation; don't claim exact producer reproduction.

Example ledger-only spec:

```json
{
  "experiment_id": "EXP-999",
  "files": {
    "ledger_2023": "/preserved/2023/trades.csv",
    "strategy": "config/strategy.yaml",
    "sessions": "config/sessions.yaml",
    "research_policy": "config/research_policy.yaml"
  },
  "years": [2023],
  "contracts": [],
  "counts": {"bars": null, "candidates": null, "trades": 344},
  "settings": {"execution": null, "cost": null, "slippage": null},
  "unavailable": {"upstream": "producer cache/config unavailable; ledger-only identity"}
}
```

This illustrates an explicitly **partial** ledger-only provenance record, not a
complete frozen producer run. Fill known producer settings rather than using null.

```bash
python scripts/lock_experiment_inputs.py --spec /path/spec.json --output /path/run/EXPERIMENT_INPUT_LOCK.json
python scripts/lock_experiment_inputs.py --verify /path/run/EXPERIMENT_INPUT_LOCK.json
python scripts/archive_experiment.py --experiment EXP-999 --source /path/run --input-lock /path/run/EXPERIMENT_INPUT_LOCK.json
```

Verify before and after computation to detect input mutation; commit/push the lock
with reports. Identity includes code commit, role-based file hashes, sizes,
coverage/classification, counts and settings; timestamp, experiment label and local
paths are outside the digest so identical inputs at another location compare equal.
Declared hashes are checked against files; metadata tampering is rejected. The CLI
also checks the current clean commit. Existing function callers without a lock
remain a legacy compatibility path; all new experiment archive CLI calls require
a lock. No old archives receive invented provenance or new output values.

Cached backtests automatically write a lock before execution, verify it afterward,
and record result trade count separately in the summary (unknown before execution).
Use a new output directory for each run. Cache certification refuses existing
metadata/code manifests; use a new versioned cache directory when definitions
change. No helper prevents arbitrary manual filesystem overwrites: subsequent
verification detects them and old retained artifacts remain necessary.
