# HPFA Action Value Cost Fusion Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN_WAITING_READINESS

## Product Node

```text
Action Value Cost Fusion Lite V1
```

## Purpose

Create claim-safe candidate packs that connect admitted action-benefit evidence, spatial/time candidates and physical-cost families without making ACTION/EVENT the product-wide observation ceiling.

Canonical doctrine:

```text
EVENT ⊂ ZFGV
ZFGV != EVENT
```

This node is downstream of construct-specific observation admission and ZFGV metric/evidence relation layers.

## Core Rule

```text
action_value_cost_fusion != football truth
benefit_candidate != performance truth
cost_candidate != fatigue truth
efficiency_candidate != causality
aggregate_support != action identity
coordinate != tracking
```

## Observation Requirements

Each component declares its own required capabilities.

ACTION_BENEFIT_CANDIDATE may require admitted ACTION/EVENT evidence and identity/time semantics.

PHYSICAL_COST candidates require their own admitted source/semantic authority and must not be treated as event counts.

SPATIAL/TEMPORAL candidates require their own semantics and admission.

AGGREGATE/TABULAR support may be used when admitted, but it does not create action identity or an independent support vote by itself.

No global event-surface gate may veto a construct that does not require ACTION/EVENT evidence.

## Required Upstream Inputs

Required inputs are construct-specific and may include:

```text
metric/construct registry admission
observation capability manifest
provenance/dependency lineage
physical_cost_surface_audit_v1.json when physical-cost evidence is used
ACTION/EVENT identity/surface admission only when an action-benefit construct requires it
metric/evidence support graph when available
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
benefit_candidate = admitted progression/access/threat/retention evidence
cost_candidate = admitted physical-cost evidence only
risk_candidate = admitted turnover/failed-action/reset context when available
efficiency_candidate = benefit_candidate / cost_candidate only when numerator and denominator are semantically bound and denominator policy is admitted
```

## Binding Status

Allowed binding statuses:

```text
UNBOUND
TEAM_BOUND
PLAYER_BOUND
TIME_BOUND
ACTION_BOUND_CANDIDATE_ONLY
OBSERVATION_BOUND_CANDIDATE_ONLY
```

Forbidden:

```text
EVENT_BOUND_TRUTH
PHYSICAL_COST_TRUTH_WITHOUT_AUTHORITY
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
canonical event truth
causality
```

## Current Product Status

```text
SPEC_WRITTEN_WAITING_READINESS
IMPLEMENTATION_WAIT
PRODUCTION_RELEASE_NOT_GRANTED
```

## Correct Predecessor

```text
Construct-specific ZFGV observation admission + Metric Family Registry Lite V1
```
