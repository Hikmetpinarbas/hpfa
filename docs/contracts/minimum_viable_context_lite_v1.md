# Minimum Viable Context Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `minimum_viable_context_lite_v1`
Claim safety: `CONTEXT_CANDIDATE_ONLY`

## Purpose

Build minimal event-only context candidates from ACTIVE_MATCH surface rows before analyst-facing interpretation.

This module does not create phase truth, possession truth, sequence truth or tactical truth.

## Why this exists

Surface-row evidence without context can create misleading football readings.

HPFA must know at least:

```text
minute or time bucket
team label
action family
zone/channel candidate
previous/next visible action family when order is available
source confidence
```

before downstream report grammar can produce analyst sentences.

## Inputs

Flat input directory:

```text
/sdcard/Download/HPFA
```

Supported local surface suffixes:

```text
.csv
.tsv
.xml
```

Optional upstream support files:

```text
triangulated_event_reflection_resolver_lite_v1.json
primary_event_surface_gate_lite_v1.json
identity_review_resolution_lite_v1.json
```

## Outputs

Flat phone outputs only:

```text
minimum_viable_context_lite_v1.json
minimum_viable_context_lite_v1.txt
```

## Context candidate fields

```text
context_id
source_file
source_format
source_row_index
minute_bucket
team_label
action_family
zone_candidate
channel_candidate
previous_action_family
next_action_family
context_completeness
source_confidence
claim_allowed
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
phase_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
dominance_truth=false
claim_safety=CONTEXT_CANDIDATE_ONLY
```

## Allowed language

```text
context candidate
visible event context surface
minute-bucket context candidate
zone/channel candidate
previous/next visible action family
```

## Forbidden language

```text
phase truth
possession truth
sequence truth
tactical truth
coach intention
dominance
validated event count
```

## Required tests

```text
test_semicolon_csv_context_extraction
test_previous_next_action_context
test_claim_boundaries_remain_false
test_no_sample_match_identity_leak
test_flat_outputs
```
