# Historical contract inventory evidence — 2026-10-10

This is a read-only data diagnostic, not a trading experiment. The user supplied
the complete VPS inventory produced by the script published at 8bfea0c, as a
gzip/base64 terminal export. Gzip checksum/length and JSON parsing passed on
decode. The large source files remain on the VPS and were not reopened locally.

The report returned INVENTORY_COMPLETE_COVERAGE_UNCERTIFIED, zero errors and
inputs_unchanged=true. Its 57 inspected contract files have 19 distinct hashes:
three byte-identical copies of each dataset across the supplied directories.
All 18 used raw segments have three matching download comparisons. Every used
row exists in those downloads; all overlapping OHLCV values match exactly; no
download-only timestamps occur inside the used segment spans. This is source
correspondence evidence, not independent exchange/vendor completeness proof.

Seven incoming contracts lack pre-segment history in these downloads: NMM23,
NMU23, NMZ23, NMM24, NMU24, NMZ24 and NMU25. Their first used/source bar is
01:00 America/New_York on the recorded rollover Monday. The prescribed Globex
session begins at 18:00 on the preceding date; neither its earlier overnight
bars nor the preceding Friday's RTH are present in these individual files.
The exact exchange/provider treatment still needs classification. No universal
warmup duration or eligibility rule is asserted here.

NMH23, NMH24, NMH25, NMM25, NMZ25 and NMH26 each have 960 earlier unused rows.
Their interval is rollover Monday 01:00–16:59 ET (with 17:00–18:00 break before
the used source starts at 18:00). These intervals contain the configured
09:30–15:59 RTH bar timestamps. Including this known history in a new corrected
derivation could supply Monday's RTH levels for the following session; that
derivation has not been performed or validated and broader warmup remains open.
The initial preceding-year NMZ segments also omit 20,280 / 20,280 / 14,880
available context rows; they contain no evaluation-year bars themselves.

Recorded first-non-null PDH/missing-row counts are descriptive and include
later missing context (e.g. NMM23: 2,340 missing rows; NMH25's 2025 build: 2,760).
They must not all be attributed to the initial reset without a dated audit.

Next locate original CSV/chunk downloads and their manifests, then classify
session coverage and sufficient existing-contract context. Do not order vendor
downloads solely from these normalized files or rerun whole-year features now.
Research selection stays paused. Existing historical findings remain archived;
changes in history can alter later state beyond the first rollover session.
