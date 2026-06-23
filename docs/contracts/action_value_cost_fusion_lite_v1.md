# HPFA Action Value Cost Fusion Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN_WAITING_READINESS

## Product Node

```text
Action Value Cost Fusion Lite V1
```

## Purpose

Create claim-safe candidate packs that connect event-benefit families, spatial/time candidates and physical-cost families.

This node is downstream of Metric Family Registry Lite V1 and the existing Event-Only Metric Fusion Engine V1.

It is not allowed to run as production-bound while primary event surface remains unresolved.

## Core Rule

```text
action_value_cost_fusion != football truth
benefit_candidate != performance truth
cost_candidate != fatigue truth
efficiency_candidate != causality
```

## Required Upstream Inputs

Required before candidate calculation:

```text
metric_family_registry_lite_v1.json
primary_event_surface_gate_lite_v1.json
physical_cost_surface_audit_v1.json
event_identity_resolution_gate_lite_v1.json
metric_support_graph_v1 output when available
```

## Candidate Families

```text
ACTION_BENEFIT_CANDIDATE
ACTION_COST_CANDIDATE
ACTION_RISK_CONTEXT_CANDIDATE
ACTION_EFFICIENCY_CANDIDATE
FUSION_RELATION_CANDIDATE
```

## Candidate Formula Skeleton

No calibrated formula is accepted yet. Initial deterministic skeleton:

```text
benefit_candidate = progression_family + access_family + threat_family + retention_context
cost_candidate = physical_distance + high_intensity + sprint + acceleration + deceleration + time_cost
risk_candidate = turnover_context + failed_action_context + reset_context
efficiency_candidate = benefit_candidate / cost_candidate only when numerator and denominator are bound
```

## Binding Status

Allowed binding statuses:

```text
UNBOUND
TEAM_BOUND
PLAYER_BOUND
TIME_BOUND
EVENT_BOUND_CANDIDATE_ONLY
```

Forbidden:

```text
EVENT_BOUND_TRUTH
```

## Allowed Output

Allowed:

```text
candidate pack
relation candidate
support/context/contradiction relation
readiness state
blocked claim family
```

Blocked:

```text
validated player value
tactical truth
fatigue truth
medical truth
dominance truth
coach intention
primary event truth
```

## Current Product Status

```text
SPEC_WRITTEN_WAITING_READINESS
IMPLEMENTATION_WAIT
PRODUCTION_RELEASE_NOT_GRANTED
```

## Correct Predecessor

```text
Metric Family Registry Lite V1
```
