# Source Mapping Contract Lite V1

Status: SPEC_WRITTEN

## Purpose

Source Mapping Contract Lite V1 records how visible source columns from ACTIVE_MATCH CSV/XML/XLSX surfaces map to HPFA canonical-lite field families.

It is not a canonical event producer.
It does not create event truth.
It does not deduplicate events.
It does not select a primary event surface.

## Inputs

```text
runtime/active_single_match/current
```

The module reads only visible local surfaces in the active match directory.

Supported visible surface formats:

```text
csv
xml
xlsx
```

## Outputs

Flat phone-root outputs:

```text
source_mapping_contract_v1.json
source_mapping_audit_v1.json
source_mapping_audit_v1.txt
```

Allowed flat phone roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output directories must be rejected with:

```text
nested_phone_output_directory_rejected
```

## Canonical-lite field families

```text
event_type
team
player
minute
second
timestamp
x
y
```

## Mapping record

Each source column is evaluated as:

```json
{
  "source_file": "...",
  "source_format": "csv|xml|xlsx",
  "source_role": "goalkeepers|players|teams|unknown",
  "source_field": "...",
  "normalized_source_field": "...",
  "canonical_field": "event_type|team|player|minute|second|timestamp|x|y|null",
  "mapped": true,
  "required": false,
  "unmapped_policy": "preserve_in_extras",
  "claim_allowed": false
}
```

## Required-field policy

For event-like surfaces, these field families are required for a production-bound event surface:

```text
event_type
x
y
```

Missing required fields do not create event truth. They produce degraded or fail-closed audit decisions.

## Decisions

Allowed per-source decisions:

```text
ACCEPT_MAPPING
DEGRADED_MISSING_REQUIRED
NO_ROWS_OR_NO_HEADERS
FAIL_CLOSED_MISSING_REQUIRED
```

Overall module status values:

```text
PASS
REVIEW_REQUIRED
FAIL_CLOSED
```

## Claim boundary

Blocked claims:

```text
canonical event count
primary event truth
validated event truth
complete event stream
deduplicated event count
possession truth
phase truth
sequence truth
tactical truth
```

Allowed analyst wording:

```text
source field mapping shows...
unmapped source columns were preserved as extras...
required field family missing on this surface...
source lineage is available for later gates...
```

## Donor support

This module adapts concepts from:

```text
HP-Motor canonicalize/provider registry
HP-PROJELERI hp_cdl canonicalize/readers
hpfa canonical_event_lite reader/detect column utilities
kloppy provider-adapter discipline
```

Rule:

```text
ADAPT_NOT_COPY
```

## Required tests

```text
test_unmapped_columns_preserved
test_required_columns_fail_closed
test_row_lineage_preserved
test_no_sample_match_identity_leak
test_nested_phone_output_directory_rejected
test_active_match_contract_outputs_are_flat
```

## Release status

```text
SPEC_WRITTEN
PRODUCTION_RELEASE_NOT_GRANTED
```
