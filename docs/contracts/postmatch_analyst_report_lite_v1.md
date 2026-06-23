# HPFA Postmatch Analyst Report Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
Postmatch Analyst Report Lite V1
```

## Purpose

Generate a numeric, claim-safe, analyst-facing postmatch report from ACTIVE_MATCH runtime outputs.

This module turns existing HPFA runtime evidence into a structured report. It does not create new event truth, metric truth, phase truth, possession truth or tactical truth.

## Inputs

Preferred flat phone outputs:

```text
team_binding_lite_audit_v1.json
primary_event_surface_gate_lite_v1.json
metric_family_registry_lite_v1.json
physical_cost_surface_audit_v1.json
event_identity_resolution_gate_lite_v1.json
```

Optional:

```text
canonical_event_lite_audit_v1.json
surface_inventory_interpretation_gate_lite_v1.json
```

## Outputs

Flat phone output only:

```text
postmatch_analyst_report_lite_v1.json
postmatch_analyst_report_lite_v1.txt
```

## Required Report Blocks

The report must include:

```text
match surface status
team row-volume comparison
action-family comparison
zone comparison
channel comparison
ratio table
physical/report surface summary
metric family registry summary
claim boundary
analyst conclusion
```

## Allowed Calculations

Allowed derived quantities:

```text
visible row shares
team-vs-team differences
team-vs-team ratios
action-family differences
action-family ratios
zone/channel share differences
surface-family counts
```

## Blocked Calculations

Blocked:

```text
canonical event count
validated event count
possession truth
phase truth
sequence truth
metric value truth
efficiency truth
physical causality
fatigue truth
tactical dominance truth
coach intention
```

## Claim Boundary

Allowed language:

```text
visible row-volume shows
row-level evidence indicates
action-family volume suggests
coordinate evidence is concentrated in
physical-cost family is available but not causally bound
metric family is registered but calculation remains closed
```

Blocked language:

```text
dominated
controlled the match
coach planned
fatigue caused
physical superiority caused
tactical truth
validated performance truth
```

## Acceptance Criteria

This node reaches ACTIVE_MATCH_EVIDENCE_PASS if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH flat outputs are written;
4. numeric comparison blocks are emitted;
5. metric values and efficiency values remain blocked;
6. primary unresolved state is preserved;
7. no nested phone output is created;
8. sample match identity is not hardcoded in product code.

## Product Status

```text
SPEC_WRITTEN
IMPLEMENTATION_PENDING
PRODUCTION_RELEASE_NOT_GRANTED
```
