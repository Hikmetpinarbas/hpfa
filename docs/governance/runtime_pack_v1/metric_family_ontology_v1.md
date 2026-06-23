# HPFA Metric Family Ontology V1

Date: 2026-06-23

Status: METRIC_FAMILY_ONTOLOGY_ACTIVE

## Purpose

Group HPFA metrics into claim-safe families before metric production, efficiency scoring or event-physical fusion.

This prevents raw metrics from being interpreted as tactical truth, possession truth, phase truth, player quality truth or physical truth.

## Core Rule

```text
metric_family != metric_truth
metric_value != football claim
metric_efficiency != causality
metric_fusion_candidate != validated explanation
```

## Metric Family Classes

Initial HPFA metric families:

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

## PROGRESSION_FAMILY

Purpose:

```text
Measure visible ball/progression-related event evidence without converting it into tactical truth.
```

Candidate metrics:

```text
progressive pass surface volume
progressive carry surface volume
forward coordinate delta
territory gain candidate
zone advancement candidate
channel advancement candidate
```

Required upstream gates:

```text
primary surface review resolution
time/phase field check for temporal versions
claim router before analyst claim
```

Allowed analyst language:

```text
progression-family surface evidence is visible
coordinate evidence indicates forward/zone movement candidate
progression action-family volume is concentrated in...
```

Blocked analyst language:

```text
validated progression truth
tactical dominance
coach plan
possession control
complete progression count
```

## EFFICIENCY_FAMILY

Purpose:

```text
Express ratio/cost/return candidates only after numerator and denominator surfaces are eligible.
```

Candidate metrics:

```text
progression per physical-cost unit
shot threat per physical-cost unit
box access per physical-cost unit
recovery action per physical-cost unit
```

Required upstream gates:

```text
metric family registry
physical-cost surface
primary/event review state
time binding where required
claim router
```

Allowed analyst language:

```text
efficiency candidate
surface-level return/cost candidate
requires later validation
```

Blocked analyst language:

```text
true efficiency
fatigue causality
fitness caused event outcome
player superiority truth
```

## PHYSICAL_COST_FAMILY

Source:

```text
Event Physical Cost Surface Lite V1
```

Candidate metrics:

```text
DISTANCE_TOTAL
DISTANCE_HIGH_INTENSITY
DISTANCE_SPRINT
SPEED_MAX
SPEED_AVERAGE
ACCELERATION
DECELERATION
METABOLIC_LOAD
PLAYER_LOAD
WORK_RATE
MINUTES_PLAYED
RECOVERY_TIME
```

Boundary:

```text
physical-cost metric is not event count
physical-cost metric is not tactical truth
physical-cost metric can support cost-side analysis after binding gates
```

## FUSION_READINESS_FAMILY

Purpose:

```text
Check whether event, physical-cost and report-context metrics can be safely reviewed together.
```

No fused metric may be emitted unless readiness is explicit.

## Product Status

```text
METRIC_FAMILY_ONTOLOGY_ACTIVE
IMPLEMENTATION_NEXT: Metric Family Registry Lite V1
PRODUCTION_RELEASE_NOT_GRANTED
```
