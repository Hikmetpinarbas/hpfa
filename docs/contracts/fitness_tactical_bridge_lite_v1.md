# HPFA Fitness-Tactical Integration Bridge Lite V1 Contract

Date: 2026-06-22

Status: ACTIVE_MATCH_EVIDENCE_PASS

## Product Node

```text
Fitness-Tactical Integration Bridge Lite V1
```

## Purpose

Create a claim-safe bridge between ACTIVE_MATCH event evidence and ACTIVE_MATCH-adjacent reference support evidence.

This bridge is an analyst-facing comparison layer. It is evidence-only and non-causal.

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

The bridge must not infer causal football truth or override ACTIVE_MATCH event evidence.

## Safe Analyst Language

Allowed language:

```text
support evidence is available beside event evidence
cross-surface review candidate
requires analyst validation
requires claim gate
visible event evidence and PDF support evidence can be reviewed together
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

## Acceptance Criteria

The bridge can reach ACTIVE_MATCH_EVIDENCE_PASS only under registered HPFA status vocabulary.

Evidence-pass requires:

1. module compiles;
2. tests pass;
3. bridge reads event audit and PDF support index;
4. flat phone outputs are written;
5. no blocked claim is emitted;
6. support documents remain non-event-truth;
7. canonical_event_count remains UNKNOWN unless upstream policy changes;
8. module_governance_matrix.tsv is synchronized.

## Current Evidence

Operator-reported Termux evidence:

```text
py_compile=PASS
pytest=3 passed in 0.04s
runtime status=PASS
claim_safety=SUPPORT_BRIDGE_ONLY_NO_CAUSALITY
candidate_count=2
```

Observed outputs:

```text
/storage/emulated/0/Download/HPFA/fitness_tactical_bridge_lite_v1.json
/storage/emulated/0/Download/HPFA/fitness_tactical_bridge_lite_v1.txt
```

Runtime evidence summary read by bridge:

```text
canonical_event_count=UNKNOWN
canonical_lite_row_count=15516
coordinate_rows=7713
event_type_rows=7725
team_rows=3680
fitness_pdf_count=5
reference_pdf_count=5
reference_page_count=141
reference_chars_total=284238
reference_texty_pages=134
runtime_event_truth=False
```

Cross-surface candidates produced:

```text
event_surface_plus_fitness_pdf_support
event_surface_plus_reference_text_support
```

## Donor / Reference Guardrail Notes

Google Drive HPFA theory/support materials preserve event-data primacy and restrict claims to what event data can support.

Dropbox external library bridge audit preserves read-only/reference-only usage and blocks runtime authority, event generation and production binding.

Academic external-load support is treated as methodological context only. It does not create football truth inside HPFA.

## Current Status

```text
ACTIVE_MATCH_EVIDENCE_PASS
PRODUCTION_RELEASE_NOT_GRANTED
```

Reason:

- Compile and tests passed.
- ACTIVE_MATCH flat-output runtime run passed.
- Event evidence and PDF/reference support evidence were both available.
- Two cross-surface review candidates were produced.
- All candidates remained non-causal.
- The canonical governance matrix row is synchronized to `ACTIVE_MATCH_EVIDENCE_PASS` in this update.

Not production release:

- Claim router integration is still required before tactical language.
- Reference Concept Extractor Lite is still missing.
- Team Binding Lite is still the next product node for identity binding.
