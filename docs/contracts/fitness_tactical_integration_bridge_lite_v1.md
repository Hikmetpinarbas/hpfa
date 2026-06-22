# HPFA Fitness-Tactical Integration Bridge Lite V1 Contract

Date: 2026-06-22

Status: SUPPORT_SPEC

## Product Node

```text
Fitness-Tactical Integration Bridge Lite V1
```

## Purpose

Join ACTIVE_MATCH event evidence with extracted fitness/reference PDF support evidence in a claim-safe analyst report layer.

This bridge does not convert fitness PDF text into tactical truth. It creates cross-surface reading prompts and evidence windows for analyst review.

## Inputs

Required upstream outputs:

```text
canonical_event_lite_v1.json
canonical_event_lite_audit_v1.json
reference_document_manifest_v1.json
reference_document_pages_v1.jsonl
reference_document_extraction_audit_v1.json
fitness_signal_pdf_index_v1.json
```

Optional later inputs:

```text
team_binding_lite_v1.json
phase_lite_v1.json
possession_boundary_lite_v1.json
rhythm_evidence_stack_v12.json
```

## Outputs

Flat phone output only:

```text
fitness_tactical_bridge_lite_v1.json
fitness_tactical_bridge_lite_v1.txt
```

## Evidence Roles

### ACTIVE_MATCH event evidence

Primary football surface:

- event_family_volume
- zone/channel distribution
- team row-volume
- coordinate coverage
- time windows when available later
- sequence candidates when available later

### Fitness / reference PDF evidence

Support surface only:

- PDF presence
- SHA identity
- page-level extracted text
- support-signal type
- physical/load vocabulary hits
- extraction quality

PDF evidence cannot override event evidence.

## Bridge Logic

The bridge may produce cross-surface observations only when both sides are present:

1. Event surface signal exists.
2. Fitness/reference support evidence exists.
3. Claim language stays conditional.
4. Any tactical or fatigue interpretation is routed to analyst review.

## Safe Analyst Output Patterns

Allowed:

```text
Fitness PDF support evidence is available beside the ACTIVE_MATCH event surface.
```

```text
The report may support a review of whether high-duel or high-transition windows coincide with physical-load notes, but it does not prove fatigue or tactical intent.
```

```text
Event evidence shows visible row-level action-family volume; fitness PDF evidence provides external context for analyst review.
```

Blocked:

```text
The fitness PDF proves the team was tired.
```

```text
The physical report explains the tactical collapse.
```

```text
GPS load caused the pressing pattern.
```

```text
Fitness data overrides ACTIVE_MATCH evidence.
```

## Recommended Report Sections

- support document inventory
- PDF extraction quality
- physical vocabulary hits
- event evidence summary
- cross-surface analyst review prompts
- safe claim candidates
- blocked claim warnings
- technical limits

## Research Guardrail

External-load interpretation in professional football must be context-aware. Important confounders include:

- playing position
- match context
- starting status
- session content
- opponent quality
- match period
- device technology
- internal load / response measures

Therefore, the bridge must not treat external load as direct tactical causality.

## Acceptance Criteria

The bridge can reach SUPPORT_EVIDENCE_PASS only if:

1. P2 Canonical Event Lite is ACTIVE_MATCH_EVIDENCE_PASS;
2. PDF index or reference document ingest has evidence outputs;
3. bridge outputs are flat under allowed phone root;
4. no tactical/fatigue causality claim is emitted;
5. blocked claim scan passes;
6. analyst review prompts are generated.

## Current Status

```text
SUPPORT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
```
