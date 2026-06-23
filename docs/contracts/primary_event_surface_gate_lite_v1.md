# HPFA Primary Event Surface Gate Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
Primary Event Surface Gate Lite V1
```

## Purpose

Evaluate ACTIVE_MATCH visible surfaces and determine whether a primary event surface candidate can be selected safely.

The gate may return:

```text
primary_event_surface_candidate=<source role or source file>
```

or:

```text
primary_event_surface_candidate=UNRESOLVED
```

This gate does not create event truth. It only creates a candidate decision for downstream gates.

## Why This Gate Exists

P2S established:

```text
surface_row_inventory_total=15516
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
```

P2D established:

```text
pattern_structure_status=NOT_BUILT_REQUIRES_LATER_GATES
```

Therefore Time / Phase, Possession and Sequence modules must not start from raw multi-surface inventory alone.

## Required Inputs

Preferred inputs:

```text
canonical_event_lite_audit_v1.json
team_binding_lite_audit_v1.json
surface_inventory_interpretation_gate_lite_v1.json
```

Optional input:

```text
canonical_event_lite_v1.json
```

## Outputs

Flat phone output only:

```text
primary_event_surface_gate_lite_v1.json
primary_event_surface_gate_lite_v1.txt
```

## Candidate Evaluation Fields

For each visible source surface, the gate should compute:

- source_file
- source_role
- source_format
- rows_read
- event_type_coverage_rows
- team_coverage_rows
- coordinate_coverage_rows
- event_type_coverage_pct
- team_coverage_pct
- coordinate_coverage_pct
- aggregate_surface_flag
- missing_column_families
- candidate_score
- candidate_risk_flags

## Candidate Logic

A surface can be a candidate only if it has usable row-level evidence.

Minimum soft indicators:

```text
event_type_coverage_rows > 0
coordinate_coverage_rows > 0
source_format in csv/xml/json-like row surface
aggregate_surface_flag=false
```

Preferred indicators:

```text
team_coverage_rows > 0
event_type_coverage_pct high
coordinate_coverage_pct high
```

XLSX aggregate surfaces must not become primary event surface.

## Decision Values

Allowed decision values:

```text
CANDIDATE_SELECTED
UNRESOLVED_REVIEW_REQUIRED
FAIL_CLOSED
```

If multiple surfaces are plausible and overlap risk remains unresolved, the gate must return:

```text
UNRESOLVED_REVIEW_REQUIRED
```

## Claim Boundary

Allowed language:

```text
primary event surface candidate
candidate selected for downstream review
candidate unresolved
requires analyst validation
requires downstream gate validation
```

Blocked language:

```text
primary surface is event truth
candidate equals deduplicated event stream
complete event count
validated event truth
possession truth
phase truth
sequence truth
pattern truth
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. contract exists;
2. module compiles;
3. tests pass;
4. ACTIVE_MATCH run writes flat outputs;
5. candidate evaluation is produced for all visible surfaces;
6. XLSX aggregate surfaces are excluded from primary selection;
7. ambiguous cases return UNRESOLVED_REVIEW_REQUIRED;
8. canonical_event_count remains UNKNOWN;
9. deduplicated_event_count remains UNKNOWN;
10. event_count_claim_allowed remains false unless a later explicit validation contract changes policy;
11. no blocked claim is emitted.

## Downstream Unlocks

If the gate returns a candidate:

```text
Time / Phase Lite may evaluate temporal fields on candidate surface.
Possession Boundary Lite may evaluate candidate continuity if temporal fields exist.
Sequence Candidate Lite may evaluate ordered event-family transitions if temporal fields exist.
```

If the gate returns unresolved:

```text
Time / Phase Lite must remain candidate-only or fail closed.
Possession Boundary Lite must remain blocked.
Sequence Candidate Lite must remain blocked.
```

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
