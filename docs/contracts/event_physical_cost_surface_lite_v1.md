# HPFA Event Physical Cost / Exposure Surface Lite V1 Contract

Date: 2026-08-15

Status: SPEC_CORRECTION_ACCEPTED

## Core invariants

```text
physical_cost_surface != event_surface
physical_cost_row_count != event_count
physical_cost_metric_value != event_count
physical_cost_metric_value != tactical_truth
minutes_played != physical_cost
exposure_candidate != validated_on_pitch_time
```

## Purpose

Classify ACTIVE_MATCH-adjacent fitness/reference material into non-event support surfaces while keeping physical load, report context and playing-time exposure semantically separate.

The node does not produce event truth, event count, possession, phase, sequence, tactical causality, fatigue truth or validated playing-time truth.

## Surface ontology

```text
EVENT_SURFACE
PHYSICAL_COST_SURFACE
EXPOSURE_NORMALIZATION_SURFACE
REPORT_METRIC_SURFACE
CLAIM_SURFACE
```

`PHYSICAL_COST_SURFACE` contains physical-load candidates such as distance, speed, acceleration/deceleration, metabolic/player load and recovery-time references.

`EXPOSURE_NORMALIZATION_SURFACE` contains playing-time/exposure candidates. `MINUTES_PLAYED` belongs here and carries `exposure_authority_status=UNKNOWN` until an explicit ExposureAuthority contract admits the operational definition and on-pitch interval evidence.

`REPORT_METRIC_SURFACE` contains FIFA/form/match/official/technical report context. None of these reference surfaces override ACTIVE_MATCH evidence.

## Required inputs

Preferred inputs:

```text
reference_document_manifest_v1.json
reference_document_pages_v1.jsonl
reference_document_extraction_audit_v1.json
fitness_signal_pdf_index_v1.json
fitness_tactical_bridge_lite_v1.json
```

## Flat outputs

```text
physical_cost_surface_manifest_v1.json
physical_cost_metric_extract_v1.tsv
physical_cost_surface_audit_v1.json
physical_cost_surface_audit_v1.txt
```

## Physical-cost families

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
RECOVERY_TIME
UNKNOWN_PHYSICAL
```

## Exposure-normalization families

```text
MINUTES_PLAYED
```

`MINUTES_PLAYED` must not enter `metric_family_counts` for physical cost. It is emitted through `exposure_family_counts` and `EXPOSURE_NORMALIZATION_SURFACE`.

Rejected exposure proxies include first-to-last observed action span, raw event timeline interval, and provider numeric minutes without admitted operational semantics.

## Report/context families

```text
FIFA_TECHNICAL_CONTEXT
MATCH_REPORT_CONTEXT
FORM_REPORT_CONTEXT
OFFICIAL_METRIC_CONTEXT
UNCLASSIFIED_REPORT_CONTEXT
```

## Default binding and authority

```text
event_binding_status=UNBOUND
exposure_authority_status=UNKNOWN
runtime_event_truth=false
event_count_claim_allowed=false
metric_count_allowed=false
exposure_authority_truth=false
```

## Allowed analyst language

```text
physical-cost surface evidence is present
exposure/playing-time candidate is present
reported minutes require ExposureAuthority validation
report context can be reviewed beside ACTIVE_MATCH evidence
```

## Blocked language

```text
physical_cost_as_event_count
physical_cost_as_event_truth
physical_cost_as_tactical_truth
physical_cost_as_medical_truth
minutes_played_as_physical_cost
exposure_candidate_as_validated_playing_time
report_surface_as_event_truth
report_surface_overrides_active_match_evidence
```

## Downstream rule

This node may feed metric-family registry, ExposureAuthority, claim routing, reference concept extraction and analyst support sections. It must not promote event identity, canonical event count, phase/possession/sequence truth, fatigue truth, or per-90 admission.

Per-90 remains blocked until both the R22 ExposureAuthority gate and the R19 denominator-closure gate are admitted.

`canonical_event_count=UNKNOWN`
`production_release=false`
