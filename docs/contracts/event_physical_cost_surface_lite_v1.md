# HPFA Event Physical Cost Surface Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
P2D Event Physical Cost Surface Lite V1
```

## Core Invariant

```text
physical_cost_surface != event_surface
physical_cost_row_count != event_count
physical_cost_metric_value != event_count
physical_cost_metric_value != tactical_truth
```

## Purpose

Classify ACTIVE_MATCH-adjacent fitness files, fitness reports, form reports, FIFA reports and match reports into non-event support surfaces.

The node extracts physical-cost and report-context metric names when visible in extracted reference text.

It does not produce event truth, event count, possession truth, phase truth, sequence truth or tactical causality.

## Surface Ontology

HPFA currently separates four surface classes:

```text
EVENT_SURFACE
PHYSICAL_COST_SURFACE
REPORT_METRIC_SURFACE
CLAIM_SURFACE
```

### EVENT_SURFACE

Examples:

```text
Players CSV/XML
Teams CSV/XML
Goalkeepers CSV/XML
```

Boundary:

```text
multi-surface rows are not event count
```

### PHYSICAL_COST_SURFACE

Examples:

```text
fitness PDFs
fitness reports
player physical sheets
load or physical output reports
```

Meaning:

```text
physical-cost context around player/team/event/role/time surfaces
```

### REPORT_METRIC_SURFACE

Examples:

```text
FIFA report
form report
match report
official metric report
technical report
```

Meaning:

```text
reference/report metric context
```

### CLAIM_SURFACE

Examples:

```text
claim router output
report grammar gate output
football output audit
```

Meaning:

```text
allowed / downgraded / blocked claim decisions
```

## Required Inputs

Preferred inputs:

```text
reference_document_manifest_v1.json
reference_document_pages_v1.jsonl
reference_document_extraction_audit_v1.json
fitness_signal_pdf_index_v1.json
fitness_tactical_bridge_lite_v1.json
```

## Outputs

Flat phone output only:

```text
physical_cost_surface_manifest_v1.json
physical_cost_metric_extract_v1.tsv
physical_cost_surface_audit_v1.json
physical_cost_surface_audit_v1.txt
```

## Metric Families

Initial physical-cost metric family set:

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
UNKNOWN_PHYSICAL
```

Initial report/metric surface family set:

```text
FIFA_TECHNICAL_CONTEXT
MATCH_REPORT_CONTEXT
FORM_REPORT_CONTEXT
OFFICIAL_METRIC_CONTEXT
UNCLASSIFIED_REPORT_CONTEXT
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

Default:

```text
UNBOUND
```

Event binding cannot become event truth inside this node.

## Allowed Analyst Language

Allowed:

```text
physical-cost metric is present
physical-cost surface is available
report/metric surface is available
this can be reviewed beside event evidence
this requires later claim routing
```

## Blocked Language Families

Blocked:

```text
physical_cost_as_event_count
physical_cost_as_event_truth
physical_cost_as_tactical_truth
physical_cost_as_medical_truth
report_surface_as_event_truth
report_surface_overrides_active_match_evidence
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH flat outputs are written;
4. physical-cost and report/metric surfaces are classified separately;
5. metric names are extracted when visible;
6. page/file provenance is preserved;
7. runtime_event_truth=false;
8. event_count_claim_allowed=false;
9. metric_count_allowed=false for event metrics;
10. no blocked language family is emitted as a football claim.

## Downstream Rule

This node may feed:

```text
claim router
reference concept extractor
postmatch physical cost context bridge
analyst support section
```

This node must not feed:

```text
event identity resolution as event rows
primary event surface selection as event source
metric primitive event count
phase or possession assertion
```

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_PENDING
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
