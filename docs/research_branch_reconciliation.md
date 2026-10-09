# Preserved research branch evidence — 2026-10-05

Earlier readiness checks searched main/the integrity checkout and found no R5/R6
completion records there. That was a checkout boundary, not evidence that the
studies had never run. Read-only inspection of locally preserved remote refs
now found the records below. No branch was merged, archive copied or study rerun.

| Ref | Inspected commit | Evidence |
| --- | --- | --- |
| `origin/research/r53-atr-stop` | `cbf7dffa3ac463f9453433cd8d4d7bbe52d1f637` | Roadmap explicitly closes Phase R5 after fixed, structural, sweep-extreme and ATR studies. |
| `origin/research/r63-equal-partials` | `163251eb48fae95f827f671178cec1f5de12d3cd` | R6.0–R6.3 reviews and all-years summaries; completed fixed-target/partial-exit block. |
| `origin/research/r70-continuation-displacement` | `0a28add2f14ea0159e83458d32c3128a34bf04a7` | Contains the preceding records and archived R7.0 outputs for all three development years. |

The R7 branch's Git blobs passed all listed SHA256SUMS checks:

| Archive | Files verified | SHA256 of manifest |
| --- | ---: | --- |
| R5-00 | 42 | `6568fd39393ee4ee687223458f673313758277922083fdabb7ae2f389bc875eb` |
| R5-01 | 24 | `4698e6742ac6c71e10704682faf764f8ceb3d5da8079f380ae1f12b656465b71` |
| R5-02 | 18 | `6a119b1265fbda41e545b501f2d95176aa8898a702afb72bd6381bfded4a9a80` |
| R5-03 | 30 | `3f3d714b977514d79affeaf7d3ce64968044b2fe8d5512bc8a03ddc309fe9c4f` |
| R7-00 | 21 | `d5cdf39328dfb0f11058b6c38c97df70fb69dd5ca9701b1677d6d81dc1d84dec` |

R6-00 through R6-03 each retain a review and an all-years summary (eight text
artifacts total). Their reviews describe completed 2023–2025 chronological
replays and control parity. They do not retain the same comprehensive individual
ledger/manifest coverage as the R5 archives; this check does not invent it.
Closing that fixed-target/partial-exit block does not prove that every EXIT-A
through EXIT-E roadmap variant was implemented exactly as originally listed.

R7.0 already retains 21 verified output artifacts: per-year control/candidate
ledgers, candidate metrics, gate summaries and segmentation/summary tables.
Its roadmap still leaves run/review/archive/cross-year-decision boxes unchecked
despite those outputs. Do not blindly rerun R7.0 to resolve stale documentation.
The cross-year review/decision and exact relation to the corrected contract need
reconciliation once the integrity gate passes.

These studies used their preserved producer semantics and baseline. Corrected
contract-isolated, object-linked/chronology execution is a new diagnostic identity,
not an exact-output replacement for those controls. Archive checks prove retained
bytes, not that old results certify the corrected strategy or an untouched holdout.
R7 remains paused pending the current integrity gate. Main and existing archive
bytes in the integrity checkout remain unchanged.


## Repository unification update — 2026-10-09

The completed R5.0-R5.3, R6.0-R6.3 and R7.0 archive directories have now been
reconciled out of the preserved research lineage into the canonical repository
history using their existing Git tree objects. No archive bytes were regenerated
or rewritten.

R7.0's stale checklist has also been reconciled from its retained outputs:
all three frozen CONTROL parity gates passed, the three yearly candidate runs
completed, the R7-00 SHA256 manifest exists, and the cross-year decision is
**reject as a production qualification change**. The result remains historical
evidence under its original producer semantics; it does not clear the newer
integrity-corrected execution contract.

The historical research branches remain preserved until the active integrity
PR is merged and a final branch-cleanup audit confirms that no unique evidence
or implementation work is stranded.