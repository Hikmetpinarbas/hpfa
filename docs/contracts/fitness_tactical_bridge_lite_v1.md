# HPFA Fitness-Tactical Integration Bridge Lite V1 Contract

Date: 2026-06-22

Status: SUPPORT_BRIDGE_CONTRACT_SPEC

## Product Node

```text
Fitness-Tactical Integration Bridge Lite V1
```

## Purpose

Create a claim-safe bridge between ACTIVE_MATCH event evidence and ACTIVE_MATCH-adjacent fitness/reference PDF support evidence.

This bridge is an analyst-facing comparison layer. It does not create tactical truth, fatigue truth, load truth, injury truth or causal explanation.

## Required Inputs

Preferred flat-output inputs:

```text
canonical_event_lite_audit_v1.json
fitness_signal_pdf_index_v1.json
reference_document_extraction_audit_v1.json
```

Minimum viable inputs:

```text
canonical_event_lite_audit_v1.json
fitness_signal_pdf_index_v1.json
```

## Outputs

Flat phone output only:

```text
fitness_tactical_bridge_lite_v1.json
fitness_tactical_bridge_lite_v1.txt
```

## Bridge Logic

The bridge may compare:

- event-family volume
- zone distribution
- channel distribution
- coordinate coverage
- team row-volume
- PDF support availability
- PDF document count
- PDF extraction readiness
- reference text availability if page extraction is present

The bridge must not infer:

- tactical causality
- fatigue causality
- injury risk truth
- load truth
- coach intention
- dominance
- off-ball truth
- phase or possession truth

## Safe Analyst Language

Allowed:

```text
support evidence is available beside event evidence
cross-surface review candidate
requires analyst validation
requires claim gate
visible event evidence and PDF support evidence can be reviewed together
```

Blocked:

```text
fitness caused tactical drop
fatigue caused the pattern
the PDF proves tactical intent
load explains match behaviour
```

## Bridge Output Sections

JSON/TXT outputs should include:

- module_id
- status
- claim_safety
- event_evidence_summary
- fitness_pdf_support_summary
- reference_document_summary
- cross_surface_review_candidates
- blocked_claims
- required_next_gates

## Cross-Surface Candidate Rule

A candidate may be generated only when both sides exist:

1. event-side evidence from Canonical Event Lite;
2. support-side PDF availability or extracted reference text.

Candidate phrasing must remain non-causal.

Example:

```text
High event-family volume and available fitness PDF support evidence create a cross-surface review candidate. This is not a fatigue or tactical causality claim.
```

## Acceptance Criteria

The bridge can reach REVIEW_REQUIRED or ACTIVE_MATCH_EVIDENCE_PASS only under registered HPFA status vocabulary.

Evidence-pass requires:

1. module compiles;
2. tests pass;
3. bridge reads event audit and PDF support index;
4. flat phone outputs are written;
5. no blocked claim is emitted;
6. runtime_event_truth remains false for PDF support;
7. canonical_event_count remains UNKNOWN unless upstream policy changes.

## Current Status

```text
SUPPORT_BRIDGE_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
```
