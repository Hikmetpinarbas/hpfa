# GK Taxonomy Source Role Reconciliation Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `gk_taxonomy_source_role_reconciliation_lite_v1`
Claim safety: `SOURCE_ROLE_RECONCILIATION_ONLY`

## Purpose

Classify goalkeeper/player cross-surface identity overlap as a source-role taxonomy review issue.

This module does not merge rows, deduplicate rows, change player roles, create a primary event stream, or emit event truth.

## Inputs

Required:

```text
identity_review_resolution_lite_v1.json
```

Optional support:

```text
event_identity_resolution_gate_lite_v1.json
source_conflict_registry_lite_v1.json
source_mapping_contract_v1.json
```

## Outputs

Flat phone outputs only:

```text
gk_taxonomy_source_role_reconciliation_lite_v1.json
gk_taxonomy_source_role_reconciliation_lite_v1.txt
```

## Decisions

```text
FAIL_CLOSED_NO_IDENTITY_REVIEW
FAIL_CLOSED_IDENTITY_REVIEW_INPUT
NO_GK_PLAYER_OVERLAP_DETECTED
GK_PLAYER_ROLE_OVERLAP_REVIEW_REQUIRED
SOURCE_ROLE_SUPPORT_CONFLICT_REMAINS
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
source_role_truth=false
gk_taxonomy_truth=false
event_count_claim_allowed=false
production_binding_allowed=false
claim_safety=SOURCE_ROLE_RECONCILIATION_ONLY
```

## Required behaviour

- detect review candidates whose `source_roles` contain both `goalkeepers` and `players`
- report affected cluster count and affected row count
- keep all candidates as review-only
- do not assign player position truth
- do not infer GK action truth
- do not resolve duplicate truth
- keep downstream gates WAIT when overlap remains
- keep downstream gates WAIT when identity review input is fail-closed

## Must not emit

```text
clean GK taxonomy truth
confirmed player role
confirmed goalkeeper event
deduplicated event truth
canonical event count
phase truth
possession truth
sequence truth
```

## Required tests

```text
test_missing_identity_review_fail_closed
test_fail_closed_identity_review_input_does_not_clear
test_no_gk_player_overlap_passes_review_clearance
test_gk_player_overlap_remains_review_required
test_source_role_support_conflict_remains_review_required
test_no_role_or_event_truth_claims
```
