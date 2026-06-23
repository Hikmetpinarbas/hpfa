# HPFA Surface Inventory Interpretation Gate Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
P2D Surface Inventory Interpretation Gate Lite V1
```

## Purpose

Convert large multi-surface row inventory counts into analyst-safe summary language before those counts enter match reports.

This gate exists because raw counts such as `surface_row_inventory_total=15516` can be misread as match event counts if they are shown without structure.

## Problem

P2S correctly reports:

```text
surface_row_inventory_total
surface_role_row_counts
source_surface_row_counts
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
```

However, analyst-facing reports need an additional readability layer.

Large row counts are useful engineering evidence, but they are not pattern structure by themselves.

## Required Inputs

Preferred inputs:

```text
canonical_event_lite_audit_v1.json
team_binding_lite_audit_v1.json
fitness_tactical_bridge_lite_v1.json
```

Minimum input:

```text
canonical_event_lite_audit_v1.json
```

## Outputs

Flat phone output only:

```text
surface_inventory_interpretation_gate_lite_v1.json
surface_inventory_interpretation_gate_lite_v1.txt
```

## Output Sections

The output should include:

- module_id
- status
- claim_safety
- surface_inventory_summary
- analyst_safe_count_language
- pattern_structure_status
- count_risk_flags
- required_next_gates
- blocked_claims

## Analyst-Safe Count Language

Allowed language:

```text
multi-surface readable row inventory
visible surface rows
surface coverage evidence
identity binding surface
requires primary event surface gate
requires pattern structure gate
```

Blocked language:

```text
match event count
true event count
complete event stream
validated event total
team dominance from row count
possession from row count
pattern truth from row count
```

## Pattern Structure Separation

This gate must separate three layers:

### 1. Surface Inventory

Answers:

```text
which files are readable?
which rows expose event/team/coordinate columns?
which surface roles exist?
```

### 2. Identity Binding

Answers:

```text
which team labels and player labels can be bound?
which rows remain unresolved?
```

### 3. Pattern Structure

Not solved here.

Pattern structure requires later gates:

```text
primary event surface gate
time/phase lite
possession boundary lite
sequence candidate gate
claim router
```

## Count Risk Flags

The gate should flag:

```text
large_surface_inventory_count
multi_surface_overlap_risk
primary_event_surface_unresolved
deduplicated_event_count_unknown
event_count_claim_not_allowed
pattern_structure_not_yet_built
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH flat output is written;
4. raw surface counts are translated into analyst-safe language;
5. `event_count_claim_allowed=false` is preserved;
6. pattern structure is marked unresolved until later gates;
7. no blocked claim is emitted.

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
