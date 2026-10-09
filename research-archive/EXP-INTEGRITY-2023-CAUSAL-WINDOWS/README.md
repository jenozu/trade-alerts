# R7 causal windows — 2026-10-09

Diagnostic export supplied by the user after resolving manifest-relative paths.
No new experiment or yearly replay was run. The gzip/base64 payload preserves
62 completed rows: 31 consecutive minute bars in each of two windows. Availability
is exactly bar start plus one minute. All three score-candidate rows agree with
the earlier 659-row export for every overlapping field. Decode the text payload
with base64 then gzip; the report preserves byte hashes and validation scope.

## January 3 long candidate, 14:34 UTC

The 14:21 sell-side sweep expires at 14:31 under the ten-bar core lifetime.
The 14:33 new sell-side sweep resets context and occurs on the same minute as
bullish displacement and MSS. That cannot satisfy the required earlier sweep.
At 14:34 there is no later bullish displacement/MSS, and no own bullish FVG
retest sequence has confirmed. Legacy bullish_core_sequence is true, but it is
preserved legacy context rather than the selected chronology contract. Using
that legacy flag as a replacement would silently change the control.

## August 24 short candidates, 13:31 and 13:45 UTC

At 13:22 the buy-side sweep and bearish displacement share a minute. The 13:23
bearish MSS occurs before the later bearish displacement at 13:30. There is no
subsequent MSS completing that core, which expires at 13:32. A 13:37 buy-side
sweep starts fresh context, but no later raw bearish displacement/MSS completes
it before 13:45. Thus neither candidate has a completed reversal core.

The separate continuation does confirm: displacement structure break at 13:42
through frozen 15226.00; later hold at 13:43 closes 15221.75; FVG retest at 13:44
closes 15217.50; later 13:45 close 15206.00 breaks frozen micro level 15212.25.
The same bearish FVG identity is exported with creation 13:43 and retest 13:44.
Recent buy-side sweep nevertheless selects reversal under shared family
precedence. The observed nonqualification matches the current specification.

The production core loop was inspected by capturing its intermediate frame and
stubbing only the linkage boundary; it reports no completed core in either
window. Full tracked FVG objects were not supplied, so this is not a full
chronology/lifecycle replay. No defect is established in these samples, and the
reason for every unconfirmed yearly candidate remains unproven.

## Next decision, not more of the same exports

A concrete research-only confirmation-first family proposal is recorded in
`docs/research/r7_family_policy_proposal.md`. Applying its flag arithmetic to
the existing 659 candidates changes qualification from seven to eight; only the
13:45 August 24 continuation is added. This does not establish planner acceptance,
trades, profitability or performance selection. No executable rule was changed.
