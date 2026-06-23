# Source Conflict Registry Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `source_conflict_registry_lite_v1`
Claim safety: `SOURCE_CONFLICT_EVIDENCE_ONLY`

## Purpose

Classify conflicts across mapped ACTIVE_MATCH source surfaces after Source Mapping Contract Lite V1.

This module does not select primary truth, does not create canonical event counts and does not validate complete event streams.

## Inputs

Required input, preferred:

```text
source_mapping_contract_v1.json
```

Fallback:

```text
source_mapping_audit_v1.json
```

Optional support inputs:

```text
canonical_event_lite_audit_v1.json
primary_event_surface_gate_lite_v1.json
event_identity_resolution_gate_lite_v1.json
physical_cost_surface_audit_v1.json
metric_family_registry_lite_v1.json
```

## Outputs

Flat phone outputs only:

```text
source_conflict_registry_lite_v1.json
source_conflict_registry_lite_v1.txt
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

## Conflict classes

```text
NO_SUPPORTED_SURFACES
UNMAPPED_EVENT_SURFACE
EVENT_LIKE_VS_AGGREGATE_SUPPORT
SCHEMA_DIVERGENCE_BY_ROLE
ROW_COUNT_DISCREPANCY_BY_ROLE
PRIMARY_SURFACE_UNRESOLVED
METRIC_FAMILY_COUNT_NOT_VALUE
SOURCE_ROLE_CONFLICT
REVIEW_REQUIRED_SOURCE
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
event_count_claim_allowed=false
production_binding_allowed=false
```

Blocked claims:

```text
primary source truth
canonical event count
complete event stream
validated event truth
clean possession truth
clean phase truth
clean sequence truth
tactical truth
fitness truth
```

## Status rules

```text
FAIL_CLOSED
= no supported source mapping input or no sources

REVIEW_REQUIRED
= one or more conflicts detected

PASS
= sources exist and no conflict detected
```

`PASS` is not production release.

## Expected ACTIVE_MATCH behaviour

Current source mapping audit shows:

```text
ACCEPT_MAPPING=3
DEGRADED_MISSING_REQUIRED=3
AGGREGATE_SUPPORT_MAPPING_ONLY=2
```

Expected conflict evidence:

```text
UNMAPPED_EVENT_SURFACE for XML surfaces
EVENT_LIKE_VS_AGGREGATE_SUPPORT for XLSX support surfaces
SCHEMA_DIVERGENCE_BY_ROLE for role-level CSV/XML differences
ROW_COUNT_DISCREPANCY_BY_ROLE when role surfaces have different row counts
PRIMARY_SURFACE_UNRESOLVED if primary gate remains unresolved
```

## Required tests

```text
test_detect_unmapped_event_surface_conflict
test_aggregate_support_not_event_required_conflict
test_row_count_discrepancy_by_role
test_no_supported_surfaces_fail_closed
test_primary_surface_unresolved_conflict
test_metric_family_count_not_value_conflict
test_flat_phone_outputs
test_nested_phone_output_directory_rejected
test_no_sample_match_identity_leak
```
