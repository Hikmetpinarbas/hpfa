# XLSX Entity-View Aggregate Support Lineage V1

## Purpose

Preserve exact XLSX row-projection provenance when the current rich multiformat producer compacts XLSX aggregate rows into player/team/goalkeeper entity-view candidates.

This is an aggregate-support attachment contract only. It does not create timeline identity, physical-action identity, event truth, metric truth, or an independent evidence vote.

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

## Claim invariants

The following locks are mandatory:

- `aggregate_support_is_timeline_identity=false`
- `aggregate_support_is_event_truth=false`
- `aggregate_support_is_independent_vote=false`
- `validated_identity=false`
- `metric_truth=false`
- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

XLSX remains aggregate/support evidence. Presence or exact raw-name alignment must not be promoted to action identity, timeline identity, independent confirmation, or physical-action count.

## Scope

This contract rehabilitates the existing `rich_multiformat_analysis_lattice_v1` producer. It does not create a parallel trace, identity, metric, or reasoning engine.
