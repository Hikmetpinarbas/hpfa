# XLSX Entity-View Aggregate Support Lineage V1

## Purpose

Preserve exact XLSX row-projection provenance when the current rich multiformat producer compacts XLSX aggregate rows into player/team/goalkeeper entity-view candidates, and attach that aggregate support only to a compatible current match-local identity candidate when the relation is unambiguous.

This is an aggregate-support attachment contract only. It does not create timeline identity, physical-action identity, event truth, metric truth, validated player/team identity, action-trace identity, or an independent evidence vote.

## Required lineage

Every entity-view candidate derived from an XLSX row projection carries `aggregate_support_lineage` with:

- `row_projection_id`
- `file_id`
- `relative_path`
- `source_sha256`
- `source_role`
- `sheet_name`
- `source_row_number`
- `match_surface_binding_id`

`aggregate_support_lineage_complete=true` requires all textual fields above to be non-empty and `source_row_number` to be a positive non-boolean integer.

If the lineage is incomplete, the candidate remains visible for diagnosis but must carry:

`aggregate_support_attachment_state=PROVENANCE_INCOMPLETE_REVIEW_REQUIRED`

and the rich lane must surface `xlsx_entity_view_aggregate_support_lineage_incomplete` as review debt.

## Match-local identity candidate relation

The existing `match_local_identity_candidates_lite_v1` output may be used only as a candidate-level relation surface. A relation is eligible only when:

- the identity payload is from `match_local_identity_candidates_lite_v1`;
- the XLSX row and identity payload share the same non-empty `match_surface_binding_id`;
- the relevant upstream identity candidate is in `TEAM_IDENTITY_CANDIDATE_BOUND` or `ACTOR_IDENTITY_CANDIDATE_BOUND` state;
- the normalized team key, and for PLAYER/GOALKEEPER rows also the normalized actor key, match exactly;
- exactly one bound candidate satisfies the relation.

When exactly one candidate matches, the entity-view row may carry:

`aggregate_support_attachment_state=MATCH_LOCAL_IDENTITY_CANDIDATE_LINK_ONLY`

plus `aggregate_support_match_local_identity_candidate_ref` and the explicit relation basis. This remains a match-local candidate relation only.

A cross-binding payload must never be linked. More than one matching bound candidate must fail to review with:

`aggregate_support_attachment_state=IDENTITY_CANDIDATE_AMBIGUOUS_REVIEW_REQUIRED`

No raw player/team name, filename, row order, or XLSX presence by itself is identity authority.

## Claim invariants

The following locks are mandatory:

- `aggregate_support_identity_relation_is_identity_truth=false`
- `aggregate_support_identity_relation_is_action_trace_attachment=false`
- `aggregate_support_attachment_is_match_local_identity_truth=false`
- `aggregate_support_attachment_is_action_trace_identity=false`
- `aggregate_support_is_timeline_identity=false`
- `aggregate_support_is_event_truth=false`
- `aggregate_support_is_independent_vote=false`
- `validated_identity=false`
- `metric_truth=false`
- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

XLSX remains aggregate/support evidence. Candidate-level linkage does not admit global roster identity, canonical event identity, timeline identity, action-trace identity, independent confirmation, or physical-action count.

## Scope

This contract rehabilitates the existing `rich_multiformat_analysis_lattice_v1` producer and reuses the current match-local identity candidate producer. It does not create a parallel trace, identity, metric, or reasoning engine.
