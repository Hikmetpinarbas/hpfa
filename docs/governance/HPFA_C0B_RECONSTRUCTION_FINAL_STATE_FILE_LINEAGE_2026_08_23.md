# HPFA C0B — Reconstruction Final-State File Lineage — 2026-08-23

Status: `C0B_RECONSTRUCTION_FILE_LINEAGE_CLOSED / EXTRACTION_SOURCE_SELECTED / NOT_MERGED / NOT_PRODUCTION`

## Purpose

Freeze the exact current Reconstruction capability/file lineage for controlled `FINAL_CAPABILITY_SNAPSHOT` extraction. This is not a historical PR merge plan.

The Reconstruction chain is:

```text
#263 Cross-Role Relation
→ #264 Trackable Action Trace
→ #265 Trackable Action Consequence
→ #266 Visible Action Sequence
→ #267 Partial-Order Hardening
```

## Current coherent boundary

Reconstruction boundary snapshot:

```text
PR=#267
branch=work/reconstruct-visible-sequence-partial-order-v1
head=a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
base=#266 / cdfe9fc5b3b15ba68818c9702d98a372103e52fe
open=true
draft=true
mergeable=true
merged=false
production_release=false
```

#267 does not fork or replace the #266 Visible Action Sequence producer. It hardens the current sequence contract and regression surface for partial/uncertain order.

## R01 — Trackable Action Trace — source #264

Final file family introduced by #264:

```text
.github/workflows/trackable-action-trace-current-v1.yml
hpfa/modules/core/trackable_action_trace_candidates_lite/contract/trackable_action_trace_candidates_lite_v1.json
hpfa/modules/core/trackable_action_trace_candidates_lite/src/trackable_action_trace_candidates.py
hpfa/modules/core/trackable_action_trace_candidates_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_trackable_action_trace_current_v1.sh
trackable_action_trace_candidates_current_v1.py
```

Required retained behaviour:
- actor-bearing PLAYER/GOALKEEPER primary trace candidates;
- TEAM reflections remain context, not primary traces;
- unresolved relation surfaces remain quarantined;
- selection partition remains complete;
- trace candidate count is not physical-action/event count;
- source row order and same-time evidence do not create temporal truth.

Historical #199 is donor provenance only. Selection behaviour was adapted from it; the historical module is not an extraction authority.

## R02 — Trackable Action Consequence — source #265

Final file family introduced by #265:

```text
.github/workflows/trackable-action-consequence-current-v1.yml
hpfa/modules/core/trackable_action_consequence_candidates_lite/contract/trackable_action_consequence_candidates_lite_v1.json
hpfa/modules/core/trackable_action_consequence_candidates_lite/src/trackable_action_consequence_candidates.py
hpfa/modules/core/trackable_action_consequence_candidates_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_trackable_action_consequence_current_v1.sh
trackable_action_consequence_candidates_current_v1.py
```

Required retained behaviour:
- one consequence candidate per current trace anchor;
- visible follow-up windows only;
- no same-time link;
- no negative-time link;
- no cross-period link;
- mixed-team same-time first-layer ambiguity remains REVIEW_REQUIRED;
- consequence candidate is not causal/possession/sequence/tactical truth.

Historical #199 consequence behaviour remains `DONOR_SUPPORT / ADAPT_NOT_COPY` only.

## R03 — Visible Action Sequence — source #266

Final producer file family introduced by #266:

```text
.github/workflows/visible-action-sequence-current-v1.yml
hpfa/modules/core/visible_action_sequence_candidates_lite/contract/visible_action_sequence_candidates_lite_v1.json
hpfa/modules/core/visible_action_sequence_candidates_lite/src/visible_action_sequence_candidates.py
hpfa/modules/core/visible_action_sequence_candidates_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_visible_action_sequence_current_v1.sh
visible_action_sequence_candidates_current_v1.py
```

Required retained behaviour:
- period + visible timestamp time-layer construction;
- same timestamp has no internal ordering;
- mixed-team same-time layers remain review-bounded;
- strict positive time between admitted layers;
- 12-second visible gap ceiling;
- period/team-handover/restart/terminal-support boundaries;
- every current trace gets exactly one sequence-member or review-layer assignment;
- TEAM reflection remains embedded context, not a primary sequence member;
- sequence candidate is not possession/control/phase/tactical truth.

Historical #205, HP-Motor sequence segmentation and HP-Engine sequence apparatus remain donors only. Their stronger assumptions must not override current claim boundaries.

## R04 — Partial-Order hardening — source #267

#267 changes only:

```text
.github/workflows/visible-action-sequence-partial-order-v1.yml
hpfa/modules/core/visible_action_sequence_candidates_lite/contract/visible_action_sequence_candidates_lite_v1.json
hpfa/modules/core/visible_action_sequence_candidates_lite/tests/test_partial_order_same_time_regression.py
tools/bootstrap_termux_visible_action_sequence_partial_order_v1.sh
```

The canonical partial-order vocabulary retained for extraction is:

```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

Mandatory invariants:

```text
ordering_evidence_scope=VISIBLE_TIMESTAMP_ONLY
same_timestamp_internal_ordering_allowed=false
source_row_order_is_temporal_truth=false
strictly_later_visible_time_is_directly_follows_truth=false
relation_records_create_action_volume=false
sequence_truth=false
possession_truth=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Physical ACTIVE_MATCH evidence boundary

This governance lineage record does not promote or rewrite ACTIVE_MATCH truth.

The GitHub #267 PR metadata still contains the earlier `ACTIVE_MATCH_REVALIDATION_REQUIRED` wording. Physical exact-head runtime evidence must remain bound to the sole runtime authority:

```text
runtime/active_single_match/current
```

Any already-produced operator/runtime evidence is evidence for its exact head only; it is not converted into a GitHub code claim by this C0B document.

## Final extraction decision

For Reconstruction alone, #267 is the final behavioural boundary.

For the later combined C3 snapshot, #278 is preferred as the single coherent extraction head because it is a strict descendant of #267 and the #267→#278 compare shows no Reconstruction producer changes. Therefore:

```text
RECONSTRUCTION_BEHAVIOURAL_BOUNDARY=#267/a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
C3_COMBINED_EXTRACTION_HEAD=#278/33ebcc161576e0e11012cc8f3c221512013c77f2
RECONSTRUCTION_FILES_UNCHANGED_ACROSS_267_TO_278=true
```

Historical PR chronology must not be replayed.

## Status

```text
C0B_RECONSTRUCTION_FILE_LINEAGE_CLOSED
FINAL_BEHAVIOURAL_BOUNDARY_267
C3_COMBINED_EXTRACTION_HEAD_278
HISTORICAL_DONORS_ADAPT_NOT_COPY
MERGE=NOT_AUTHORIZED
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```
