# Triangulated Event Reflection Resolver Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `triangulated_event_reflection_resolver_lite_v1`
Claim safety: `REFLECTION_RESOLUTION_CANDIDATE_ONLY`

## Purpose

Group possible multi-surface reflections of the same visible match action across CSV, XML and XLSX-like surfaces before analyst-facing action volume is interpreted.

This module does not create true event counts, canonical event truth or deduplicated event truth.

## Problem

CSV/XML/XLSX surfaces may contain different reflections of the same action. Summing them can overstate football actions.

Example:

```text
1300 pass-family surface rows
```

must not be written as:

```text
1300 passes
```

## Inputs

Primary input directory:

```text
/sdcard/Download/HPFA
```

Required support files when available:

```text
canonical_event_lite_audit_v1.json
primary_event_surface_gate_lite_v1.json
source_mapping_contract_v1.json
source_conflict_registry_lite_v1.json
event_identity_resolution_gate_lite_v1.json
```

Event-like local surfaces may be discovered from flat input directory files with supported suffixes:

```text
.csv
.xml
.tsv
```

## Reflection candidate keys

```text
time proximity bucket
team label
player label if available
action family
event type/code/label
x/y coordinate bucket
source role
source file
row provenance
```

## Outputs

Flat phone outputs only:

```text
triangulated_event_reflection_resolver_lite_v1.json
triangulated_event_reflection_resolver_lite_v1.txt
```

## Output concepts

```text
surface_row_count
reflection_group_count
single_surface_group_count
multi_surface_group_count
unresolved_reflection_count
candidate_action_family_volume
reflection_group_examples
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
deduplicated_event_count=UNKNOWN
reflection_group_truth=false
action_count_claim_allowed=false
claim_safety=REFLECTION_RESOLUTION_CANDIDATE_ONLY
```

## Allowed language

```text
pass-family surface rows
candidate pass reflection groups
multi-surface reflection candidate
requires canonical validation
```

## Forbidden language

```text
1300 passes
2700 attacks
true event count
validated action count
complete event stream
```

## Required tests

```text
test_groups_same_action_across_surfaces
test_keeps_surface_rows_separate_from_candidate_groups
test_does_not_emit_true_action_count
test_unknown_count_claims_stay_unknown
test_no_sample_match_identity_leak
test_flat_outputs
test_nested_phone_output_directory_rejected
```
