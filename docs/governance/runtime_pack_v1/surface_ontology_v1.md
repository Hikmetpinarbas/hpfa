# HPFA Surface Ontology V1

Date: 2026-06-23

Status: SURFACE_ONTOLOGY_ACTIVE

## Purpose

Prevent surface contamination across event evidence, physical-cost evidence, report evidence and claim decisions.

## Core Classes

```text
EVENT_SURFACE
PHYSICAL_COST_SURFACE
REPORT_METRIC_SURFACE
CLAIM_SURFACE
```

## EVENT_SURFACE

Examples:

```text
Players CSV/XML
Teams CSV/XML
Goalkeepers CSV/XML
```

Allowed evidence:

```text
row-level event-family evidence
coordinate evidence
team/player binding evidence
duplicate-risk candidate evidence
```

Blocked readings:

```text
multi-surface rows as event count
surface rows as possession truth
surface rows as pattern truth
```

## PHYSICAL_COST_SURFACE

Examples:

```text
fitness report
fitness players report
physical output report
load support report
```

Allowed evidence:

```text
physical metric names
visible physical values when extracted
player/team/time support binding candidates
physical-cost context beside event evidence
```

Blocked readings:

```text
physical metric as event count
physical metric as event truth
physical metric as tactical claim by itself
physical metric as medical claim by itself
```

## REPORT_METRIC_SURFACE

Examples:

```text
FIFA report
form report
match report
technical report
official metric report
```

Allowed evidence:

```text
report context
metric label context
technical reference context
page-level provenance
```

Blocked readings:

```text
report text as runtime event truth
report text overriding ACTIVE_MATCH surface evidence
report text as primary event stream
```

## CLAIM_SURFACE

Examples:

```text
claim router
claim-safe report grammar gate
football output audit
```

Allowed evidence:

```text
allowed claim
downgraded claim
blocked claim
required next gate
```

## Binding Rule

Surfaces can be joined only through explicit gates.

```text
EVENT_SURFACE + PHYSICAL_COST_SURFACE -> physical cost context candidate
EVENT_SURFACE + REPORT_METRIC_SURFACE -> report context candidate
Any candidate -> CLAIM_SURFACE before analyst claim
```

## System Invariants

```text
physical_cost_surface != event_surface
report_metric_surface != event_surface
claim_surface != source evidence
physical_cost_row_count != event_count
report_page_count != event_count
support evidence cannot override ACTIVE_MATCH runtime evidence
```

## Current Product Implication

Primary Event Surface Gate must wait until event identity risk and support/report boundaries are explicit.

```text
Event Identity Resolution Gate = ACTIVE_MATCH_EVIDENCE_PASS
Event Physical Cost Surface Lite = NEXT_SUPPORT_NODE
Primary Event Surface Gate = WAITING_EVENT_IDENTITY_AND_SUPPORT_BOUNDARY
```
