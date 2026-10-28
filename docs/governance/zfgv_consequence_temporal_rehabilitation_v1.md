# ZFGV Consequence Temporal Rehabilitation V1

Status: `SPEC_CORRECTION_ACCEPTED`

## Problem

`trackable_action_consequence_candidates_lite_v1` currently identifies later visible traces from positive numeric deltas in the same period. That is useful for provenance-bounded windows, but numeric parseability and positive delta alone do not establish football chronology.

The ZFGV observation model therefore must not allow the existing 5/8/12-second window machinery to silently promote `start_candidate` into admitted BEFORE/AFTER truth.

## Current producer

Current producer remains:

`hpfa/modules/core/trackable_action_consequence_candidates_lite/src/trackable_action_consequence_candidates.py`

No parallel consequence engine is authorized.

## Rehabilitation rule

The producer is to be strengthened in place.

Directional consequence language requires an explicit temporal relation admission compatible with the current partial-order vocabulary:

- `BEFORE_CONFIRMED`
- `AFTER_CONFIRMED`
- `SAME_TIME_UNORDERED`
- `ORDER_INDETERMINATE`
- `PROVENANCE_ORDER_ONLY`

Only admitted directional states may unlock directional follow-up semantics. `PROVENANCE_ORDER_ONLY`, numeric sorting, source row order, or same-period membership cannot do so.

Until executable binding lands, the current positive-delta windows are classified as:

`PROVENANCE_WINDOW_CANDIDATE_ONLY_UNTIL_TEMPORAL_BINDING`

and the rehabilitation state is:

`REVIEW_REQUIRED_UNTIL_EXECUTABLE_TEMPORAL_BINDING`.

## ZFGV capability manifest

Required capabilities:

- ACTION
- ACTOR
- TEMPORAL
- OUTCOME
- PROVENANCE

Optional enrichment:

- SPATIAL
- RELATIONAL
- CONTEXT
- PROCESS

Forbidden without:

- TEMPORAL_SEMANTICS
- IDENTITY_ADMISSION
- REFLECTION_CONTROL
- DEPENDENCY_CONTROL

Tracking/video is not globally required for this construct.

## Football-analysis gain

The rehabilitation separates two statements that must not be conflated:

1. `A different visible row occurs at a numerically larger candidate time.`
2. `An admitted football-time relation supports that the later action is a visible consequence candidate after the anchor.`

Only the second may support directional process reasoning.

This preserves consequence-chain utility while preventing row/time formatting from becoming invented chronology.

## Red Team

Do not promote:

- numeric field -> football chronology
- row order -> BEFORE/AFTER
- same timestamp -> total order
- positive delta -> causality
- follow-up -> possession truth
- opponent follow-up -> tactical response truth
- recurrence -> coach intention

## Next executable step

Bind current trace/consequence processing to admitted temporal relation evidence already present in HPFA's partial-order vocabulary. Do not create a separate chronology engine. Add regression coverage proving that numeric-only, same-time, provenance-only, and indeterminate relations cannot unlock directional consequence claims.

`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
