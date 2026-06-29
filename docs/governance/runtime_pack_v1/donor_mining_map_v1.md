# HPFA Donor Mining Map V1

Status: DISCOVERY_PASS_PLAN_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Rule: ADAPT_NOT_COPY

This document records donor capabilities found in HP-Motor-main, HP-Motor, HP-Engine and HP-PROJELERI. It is a mining map, not executable product code.

## Source role registry compliance

This document only uses roles already defined by `source_role_registry_v1`.

Allowed GitHub donor role for non-product repositories:

```text
GITHUB_DONOR_REPO
```

Do not introduce unregistered source roles such as `LEGACY_DONOR_REPO` or `GOVERNANCE_DONOR_CANDIDATE` inside product governance artifacts unless the source role registry is updated in the same change.

Legacy status, governance-candidate status, or audit-needed status must be expressed in the use boundary, not in the source role field.

## Step gain record

```json
{
  "step_id": "DONOR_MINING_MAP_V1",
  "source_repo": "HP-Motor-main|HP-Motor|HP-Engine|HP-PROJELERI",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "governance_runtime_pack",
  "engineering_gain": [
    "donor capability map",
    "lane-to-module modernization plan",
    "claim boundary preservation",
    "ADAPT_NOT_COPY intake queue",
    "source role registry compliance"
  ],
  "analyst_gain": [
    "clearer view of which football evidence layers can become HPFA-native modules",
    "separation between source governance, taxonomy, metrics, sequence, rhythm and report claims",
    "blocked claims remain visible before analyst-facing text is written"
  ],
  "new_blockers": [
    "PR #94 blockers must close before Match Context Slicer is runtime-ready",
    "HP-PROJELERI requires tree audit before governance use",
    "canonical_event_count remains UNKNOWN without separate Event Count Validation contract"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Donor source roles

| Source | Registered source role | Use boundary |
|---|---|---|
| HP-Motor-main | GITHUB_DONOR_REPO | canonical schema, gate policy, canon index, ontology and registry ideas only |
| HP-Motor | GITHUB_DONOR_REPO | legacy donor repository; metric registry, validator and vendor normalizer ideas only |
| HP-Engine | GITHUB_DONOR_REPO | claim runtime, sequence candidate and temporal signal ideas only |
| HP-PROJELERI | GITHUB_DONOR_REPO | governance-support candidate only; tree audit required before any governance use |

## Highest-value donor findings

### HP-Motor-main

Useful donor capabilities:

- canonical event schema discipline
- deterministic / fail-closed / provider-agnostic principles
- time model and period boundary model
- coordinate bounds and key-zone model
- event type taxonomy
- gate policy G01-G07
- canon index / registry loader idea
- platform mapping registry idea

Target HPFA modules:

- Canonical Surface Schema Refinement Lite
- Data Quality Gate Lite
- No Silent Drop Audit Lite
- Source Mapping Registry Lite
- Duplicate Risk Gate Lite
- Coordinate Boundary Gate Lite
- Temporal Consistency Gate Lite
- Half Candidate Validation Gate Lite
- Action Family Taxonomy Registry Lite

Claim boundary:

- no canonical event count truth
- no complete event truth
- no possession truth from donor schema alone
- no attacking-direction truth while possession gate is closed

### HP-Motor

Useful donor capabilities:

- metric registry with id, layer, mechanisms, raw formula, required columns and status policy
- metric validator using required-column availability
- vendor normalizer and field aliasing idea
- report schema and narrative generator require later scan

Target HPFA modules:

- Metric Primitive Lite
- Metric Family Registry Lite
- Metric Required Fields Gate
- Metric Runtime Validator Lite
- Vendor Metric Mapping Registry Lite
- Source Mapping Contract V2

Claim boundary:

- metric label does not create tactical truth
- required-column OK does not equal ACTIVE_MATCH_EVIDENCE_PASS
- sequence-dependent metrics remain blocked unless sequence candidate/truth gates allow them

### HP-Engine

Useful donor capabilities:

- observation / mechanism / diagnosis / claim consolidation pipeline
- sequence builder using same-team continuity and time-gap heuristic
- temporal signals: event density, attack burst and turnover-pressure proxy
- temporal metrics: event rate, attack rate, spectral entropy, rhythm stability, phase-transition proxy, temporal-state entropy

Target HPFA modules:

- Observation Evidence Pack Lite
- Mechanism Candidate Registry Lite
- Diagnostic Candidate Gate Lite
- Claim Consolidation Gate Lite
- Sequence Candidate Builder Lite
- Temporal Signal Primitive Lite
- Rhythm Support Signal Lite
- Phase Transition Proxy Candidate Lite

Claim boundary:

- diagnosis remains diagnostic_candidate, not truth
- sequence output remains sequence_candidate, not possession truth
- temporal/rhythm signal is support evidence only
- single signal cannot assign rhythm state
- phase-transition metric does not create phase truth

### HP-PROJELERI

Current finding:

- repository exists and is accessible
- code search did not surface usable governance files in the first pass
- small private repo footprint suggests tree audit is required before use

Target HPFA step:

- HP-PROJELERI Governance Tree Audit Lite

Claim boundary:

- HP-PROJELERI remains `GITHUB_DONOR_REPO` until audited and mapped into hpfa contracts
- HP-PROJELERI is not governance authority until an explicit governance audit maps files into registered governance semantics

## Lane mapping

### Lane A — Canonical Surface and Source Governance

Priority: P0

Build candidates:

- Data Quality Gate Lite V1
- No Silent Drop Audit Lite V1
- Source Mapping Registry Lite V1
- Duplicate Risk Gate Lite V1
- Coordinate Boundary Gate Lite V1
- Temporal Consistency Gate Lite V1
- Team Identity Gate Lite V1

Required tests:

- test_no_silent_drop_surface_rows
- test_required_columns_missing_blocks_truth
- test_duplicate_risk_blocks_event_count_truth
- test_coordinate_out_of_bounds_blocks_spatial_truth
- test_temporal_backward_jump_blocks_time_truth
- test_team_identity_conflict_blocks_runtime_truth

### Lane E — Segmentation, Taxonomy, Classification, Differentiation and Diagnosis

Priority: P1

Build candidates:

- Football Ontology Registry Lite V1
- Action Family Taxonomy Registry Lite V1
- Segmentasyon Lite V1
- Tasnif Classifier Lite V1
- Tefrik Differentiation Gate Lite V1
- Teshis Diagnostic Candidate Gate Lite V1

Required tests:

- test_taxonomy_registry_blocks_unknown_label
- test_segmentation_does_not_drop_surface_rows
- test_classification_reports_ambiguous_rows
- test_tefrik_prevents_false_merge_without_separating_fields
- test_teshis_requires_multiple_eligible_signals
- test_diagnostic_candidate_keeps_claim_boundary

### Lane B — Metric Registry and Claim-Safe Output

Priority: P1 after Lane E

Build candidates:

- Metric Primitive Lite V1
- Metric Family Registry Lite V1
- Metric Required Fields Gate Lite V1
- Metric Status Normalizer Lite V1
- Vendor Metric Mapping Registry Lite V1

Required tests:

- test_metric_without_required_fields_blocks
- test_metric_status_normalizer_maps_unknown_to_review_required
- test_metric_label_does_not_create_tactical_truth
- test_sequence_metric_blocks_without_sequence_gate

### Lane C — Context, Window, Phase, Tempo and Sequence Candidates

Priority: P2 after PR #94 blocker closure

Build candidates:

- Match Context Slicer Lite V1 blocker fix
- Sequence Candidate Builder Lite V1
- Half Candidate Gate Lite V1
- Tempo Support Signal Lite V1
- Rhythm Support Signal Lite V1
- Phase Transition Proxy Candidate Lite V1

Required tests:

- test_context_sample_truncation_blocks_complete_summary
- test_event_index_window_uses_context_ordinal_position
- test_sequence_candidate_not_possession_truth
- test_single_signal_cannot_assign_rhythm_state
- test_phase_transition_proxy_not_phase_truth

### Lane D — Analyst Report Grammar and Evidence Packaging

Priority: P1 after Lane E

Build candidates:

- Observation Evidence Pack Lite V1
- Mechanism Candidate Pack Lite V1
- Diagnostic Candidate Pack Lite V1
- Claim Consolidation Gate Lite V1
- Report Surface Evidence Index Lite V1

Required tests:

- test_observation_does_not_become_claim_truth
- test_diagnosis_remains_candidate
- test_claim_consolidation_blocks_forbidden_claims
- test_report_surface_contains_evidence_refs

## Immediate build order

1. Close PR #94 blockers.
2. Merge or retain PR #98 as donor modernization intake governance.
3. Build Lane A contract/test pack.
4. Build Lane E ontology/taxonomy/segmentation contract pack.
5. Build Lane B metric registry contract pack.
6. Build Lane D evidence/report package.
7. Build Lane C sequence/rhythm/context candidate support only after upstream blockers are stable.
8. Audit HP-PROJELERI before governance use.

## Release rule

This map is not a production release. It is a donor modernization planning artifact. Every downstream module must provide its own contract, schema, tests, ACTIVE_MATCH runtime evidence and claim boundary before any release claim.
