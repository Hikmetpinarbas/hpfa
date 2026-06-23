# HPFA Metric Family Registry Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
Metric Family Registry Lite V1
```

## Purpose

Create a claim-safe registry that maps visible metric names, action families and support metric families into HPFA metric-family classes.

This node does not compute performance metrics. It only classifies metric candidates and declares required gates before calculation.

## Required Inputs

Preferred inputs:

```text
canonical_event_lite_audit_v1.json
team_binding_lite_audit_v1.json
event_identity_resolution_gate_lite_v1.json
physical_cost_surface_audit_v1.json
primary_event_surface_gate_lite_v1.json
```

## Outputs

Flat phone output only:

```text
metric_family_registry_lite_v1.json
metric_family_registry_lite_v1.txt
```

## Metric Families

Allowed initial families:

```text
PROGRESSION_FAMILY
FINAL_THIRD_ACCESS_FAMILY
BOX_ACCESS_FAMILY
SHOT_THREAT_FAMILY
POSSESSION_SUPPORT_FAMILY
BALL_RETENTION_FAMILY
PRESSURE_DUEL_FAMILY
RECOVERY_DEFENSIVE_ACTION_FAMILY
GOALKEEPER_RESTART_FAMILY
PHYSICAL_COST_FAMILY
REPORT_CONTEXT_FAMILY
EFFICIENCY_FAMILY
FUSION_READINESS_FAMILY
UNKNOWN_METRIC_FAMILY
```

## Registry Record Fields

Each registry record must include:

```text
metric_family
metric_name
source_surface_class
source_module
required_upstream_gates
calculation_status
claim_safety
allowed_language
blocked_language_families
```

## Calculation Status Values

Allowed values:

```text
REGISTRY_ONLY
READY_FOR_CANDIDATE_CALCULATION
WAIT_PRIMARY_SURFACE_REVIEW
WAIT_TEMPORAL_BINDING
WAIT_PHYSICAL_COST_BINDING
WAIT_CLAIM_ROUTER
FAIL_CLOSED
```

## Initial Family Rules

Progression family:

```text
requires primary surface review resolution before event-level calculation
requires coordinate evidence
requires temporal binding for rate/speed versions
```

Efficiency family:

```text
requires numerator metric family
requires denominator physical-cost family
requires binding status
requires claim router
```

Physical-cost family:

```text
uses physical-cost surface only
cannot become event count
```

Report-context family:

```text
uses report/metric surface only
cannot override ACTIVE_MATCH evidence
```

## Claim Boundary

Allowed:

```text
metric family registered
metric candidate waiting for gate
efficiency candidate requires numerator/denominator binding
```

Blocked:

```text
metric value as validated performance truth
metric family as tactical truth
physical-cost value as event count
efficiency candidate as causality
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH flat outputs are written;
4. progression family is registered;
5. physical-cost family is registered from existing physical-cost audit;
6. efficiency family is registered but calculation stays gated;
7. primary surface unresolved state is respected;
8. no metric count or football claim is unlocked.

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_PENDING
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
