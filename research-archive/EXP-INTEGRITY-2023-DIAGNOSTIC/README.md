# Corrected 2023 execution diagnostic evidence

Imported from user-supplied `BEGIN_2023_EVIDENCE` terminal export on 2026-10-09.
The five producer files are preserved byte-for-byte after decoding. This is an
integrity diagnostic archive, not a new strategy-selection experiment.

Both original lock identity digests and artifact metadata were checked locally.
The exported summary, decisions and effective configuration match their recorded
output-lock SHA-256 hashes and sizes. Code-file hashes match the integrity-code
checkout. Counts and every rejection reason reconcile between decisions and summary.
See EXPORT_VERIFICATION.json for verification scope.

Results: 440,032 source rows, 659 score-candidate rows, seven eligible directional
signals, zero accepted plans, zero simulated trades and zero historical executed-plan
comparisons. Six contract segments are retained. The producer records chronology
contract fvg_chronology_v2, market_after_retest_confirmation_v2, commissions disabled,
quantity one and point value two. Fixed-target fields retained in effective config
are not evidence that the v2 planner manufactures fixed targets.

Original locks retain VPS paths. Market-data binaries and other VPS-only inputs
are not supplied here; their contents cannot be independently rehashed locally.
The recorded completed VPS verification remains distinct from this export check.
Do not describe this archive as profitability evidence or accepted-path parity.
No rule/config change, rebuild, audit rerun or production deployment occurred.
