# HPFA Support Report Concept Surface Gate Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
Support Report Concept Surface Gate Lite V1
```

## Purpose

Extract analyst-safe concept surfaces from ACTIVE_MATCH-adjacent PDF reports such as fitness reports and FIFA technical/reference reports.

This node keeps PDF reports outside event counting and duplicate-risk resolution.

## Source Boundary

Fitness and FIFA reports are:

```text
ACTIVE_MATCH_ADJACENT_SUPPORT_DOCUMENT
REFERENCE_DOCUMENT_SUPPORT
```

They are not:

```text
runtime event surface
primary event surface
metric counting surface
deduplicated event source
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

Minimum input:

```text
reference_document_extraction_audit_v1.json
```

## Outputs

Flat phone output only:

```text
support_report_concept_surface_gate_lite_v1.json
support_report_concept_surface_gate_lite_v1.txt
```

## Concept Families

The gate may identify concept families:

```text
FITNESS_LOAD_SUPPORT
PHYSICAL_OUTPUT_SUPPORT
PLAYER_AVAILABILITY_CONTEXT
FIFA_TECHNICAL_REPORT_SUPPORT
FIFA_MATCH_CONTEXT_SUPPORT
OFFICIATING_OR_TECHNOLOGY_CONTEXT
TACTICAL_REPORT_LANGUAGE_REVIEW
UNCLASSIFIED_SUPPORT_TEXT
```

## Allowed Analyst Use

Allowed:

```text
support report mentions physical/load context
support report text is available for review
FIFA/reference report may provide tournament or technical context
concept requires claim router before football claim
```

## Blocked Language Families

Blocked language families:

```text
support_to_physical_truth_language
support_to_medical_truth_language
support_to_tactical_causality_language
support_to_intention_language
support_overrides_event_evidence_language
support_to_event_truth_language
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH flat outputs are written;
4. PDF/report concepts are grouped by support family;
5. page-level provenance is preserved when available;
6. runtime_event_truth remains false;
7. event_count_claim_allowed remains false;
8. metric_count_allowed remains false;
9. no blocked language family is emitted as a football claim.

## Downstream Rule

This node may feed:

```text
claim router
reference concept extractor
analyst report support section
fitness-event bridge review
```

This node must not feed:

```text
event identity resolution as event rows
primary event surface selection as event source
metric primitive count
possession or phase assertion
```

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
