# Primary Surface Review Resolution Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `primary_surface_review_resolution_lite_v1`
Claim safety: `PRIMARY_SURFACE_REVIEW_RESOLUTION_ONLY`

## Purpose

Resolve the review state emitted by Primary Event Surface Gate Lite V1 into a downstream-safe review decision.

This module does not create primary event truth, complete event truth, canonical event count, deduplicated event count, phase truth, possession truth or sequence truth.

## Inputs

Required:

```text
primary_event_surface_gate_lite_v1.json
```

Optional support:

```text
source_conflict_registry_lite_v1.json
event_identity_resolution_gate_lite_v1.json
source_mapping_contract_v1.json
```

## Outputs

Flat phone outputs only:

```text
primary_surface_review_resolution_lite_v1.json
primary_surface_review_resolution_lite_v1.txt
```

Allowed output roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must fail with:

```text
nested_phone_output_directory_rejected
```

## Resolution decisions

```text
FAIL_CLOSED_NO_PRIMARY_GATE
FAIL_CLOSED_NO_REVIEW_CANDIDATE
ALREADY_CANDIDATE_SELECTED_BY_GATE
RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW
UNRESOLVED_IDENTITY_CONFLICTS_REMAIN
UNRESOLVED_SOURCE_CONFLICTS_REMAIN
UNRESOLVED_REVIEW_REQUIRED
```

## Decision semantics

`RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW` means only:

```text
A candidate can be carried forward as a review candidate.
```

It does not mean:

```text
primary event truth
validated event stream
canonical event count
deduplicated event count
production release
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
event_count_claim_allowed=false
production_binding_allowed=false
claim_safety=PRIMARY_SURFACE_REVIEW_RESOLUTION_ONLY
```

## Blocking reasons

```text
no_primary_gate_output
no_review_candidate
identity_overlap_candidates_present
top_candidate_has_source_conflict
no_supported_surfaces
unknown_source_role
```

## Non-blocking review signals

These can remain visible but do not produce event truth:

```text
multiple_eligible_event_surfaces
schema_divergence_by_role
row_count_discrepancy_by_role
aggregate_support_surface_present
metric_family_count_not_value
```

## Required tests

```text
test_missing_primary_gate_fail_closed
test_no_review_candidate_fail_closed
test_already_selected_gate_is_preserved
test_unresolved_multiple_surface_can_resolve_to_review_candidate
test_identity_overlap_keeps_unresolved
test_top_candidate_source_conflict_keeps_unresolved
test_flat_phone_outputs
test_nested_phone_output_directory_rejected
test_no_sample_match_identity_leak
```
