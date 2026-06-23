# Identity Review Resolution Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `identity_review_resolution_lite_v1`
Claim safety: `IDENTITY_REVIEW_RESOLUTION_ONLY`

## Purpose

Resolve identity-overlap review blockers emitted by Event Identity Resolution Gate Lite V1 without creating deduplicated event truth.

This module does not merge rows, delete rows, deduplicate rows, create a clean event stream, or emit validated event counts.

## Inputs

Required:

```text
event_identity_resolution_gate_lite_v1.json
```

Optional support:

```text
primary_event_surface_gate_lite_v1.json
primary_surface_review_resolution_lite_v1.json
source_conflict_registry_lite_v1.json
```

## Outputs

Flat phone outputs only:

```text
identity_review_resolution_lite_v1.json
identity_review_resolution_lite_v1.txt
```

Allowed phone roots:

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
FAIL_CLOSED_NO_IDENTITY_GATE
NO_IDENTITY_OVERLAP_DETECTED
RESOLVED_IDENTITY_REVIEW_CANDIDATE_ONLY
UNRESOLVED_IDENTITY_OVERLAP_REMAINS
UNRESOLVED_IDENTITY_INSUFFICIENT_FIELDS
UNRESOLVED_SOURCE_SUPPORT_CONFLICTS_REMAIN
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
identity_resolution_truth=false
event_count_claim_allowed=false
production_binding_allowed=false
claim_safety=IDENTITY_REVIEW_RESOLUTION_ONLY
```

## Must not emit

```text
deduplicated event count
clean event stream
validated identity truth
merged event truth
phase truth
possession truth
sequence truth
```

## Required behaviour

- read `candidate_cluster_count`
- read `duplicate_risk_candidate_count`
- read `unresolved_candidate_count`
- keep zero-cluster / zero-unresolved outputs reachable as `NO_IDENTITY_OVERLAP_DETECTED`
- keep nonzero unresolved candidate outputs in review-required state
- read duplicate cluster candidate metadata as review candidates only
- preserve provenance and strategy names where available
- block downstream if overlap remains
- clear only when no overlap candidates and no unresolved candidates exist
- do not mutate source rows
- do not derive deduplicated counts

## Required tests

```text
test_missing_identity_gate_fail_closed
test_no_overlap_detected_allows_review_clearance
test_unresolved_insufficient_fields_stays_review_required
test_upstream_unresolved_label_with_zero_unresolved_count_can_clear
test_overlap_candidates_remain_review_required
test_duplicate_candidate_provenance_is_preserved
test_source_support_conflict_keeps_unresolved
test_no_deduplicated_event_count_claim
test_flat_phone_outputs
test_nested_phone_output_directory_rejected
test_no_sample_match_identity_leak
```
