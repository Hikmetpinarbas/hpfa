# HPFA Donor Modernization Intake V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product repo authority: hpfa
Source repos: HP-Motor-main, HP-Motor, HP-Engine, HP-PROJELERI

## Purpose

This document defines how capabilities from the other repositories are modernized and rebuilt inside hpfa.

The goal is not to copy donor code. The goal is to convert useful donor repository patterns into HPFA product modules with explicit contracts, tests, runtime evidence, claim boundaries, step gains, and release status.

## Non-negotiable rule

ADAPT_NOT_COPY.

No donor source file becomes product code by direct import or copy. Every capability must pass through:

1. source role identification
2. target HPFA module selection
3. contract definition
4. input and output schema definition
5. claim boundary definition
6. required test definition
7. ACTIVE_MATCH runtime evidence requirement
8. football output audit
9. step-gain ledger update
10. release status normalization

## Source authority

Only this path is runtime truth:

`runtime/active_single_match/current`

All other repositories and documents are donor or reference material.

## Repository roles

| Repository | Role | Correct HPFA use |
|---|---|---|
| HP-Motor-main | GITHUB_DONOR_REPO | canonical surface, source mapping, conflict registry, permission spine, no-silent-drop audit |
| HP-Engine | GITHUB_DONOR_REPO | metric registry, metric ontology, validator, report grammar, pattern candidate support |
| HP-Motor | GITHUB_DONOR_REPO | legacy phase candidate, tempo support signal, brief grammar patterns |
| HP-PROJELERI | GITHUB_DONOR_REPO | governance-support candidate after tree audit |
| hpfa | GITHUB_PRODUCT_REPO | executable product modules only |

## Step-gain ledger requirement

Every modernization step must state what HPFA gained.

Each step must produce two gain blocks:

### Engineering gain

What changed in the product system:
- new contract
- new schema
- new test
- new registry
- new runtime gate
- new validator
- new output file
- new blocker
- new status normalization

### Analyst gain

What became clearer for the football analyst:
- which surface evidence is now readable
- which rows or event-like actions are now categorized
- which context slices are now safer
- which claims are now allowed, candidate-only, or blocked
- which missing inputs are now visible
- which report sentences can now be written more safely

A step with no engineering gain and no analyst gain is not a product step.

## Gain record schema

Every issue, PR, or runtime handoff created from this intake must include this record:

```json
{
  "step_id": "string",
  "source_repo": "string",
  "target_hpfa_module": "string",
  "engineering_gain": ["string"],
  "analyst_gain": ["string"],
  "new_blockers": ["string"],
  "claim_boundary_change": "string",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Modernization lanes

### Lane A — Canonical Surface and Source Governance

Priority: P0

Target HPFA modules:
- Canonical Event Lite V1
- Source Mapping Contract Lite
- Source Conflict Registry Lite
- Permission Spine
- Runtime Evidence Chain Closure

Product outputs to build:
- no-silent-drop audit
- canonical surface schema refinement
- source mapping registry
- source conflict blocker model
- capability and permission matrix

Required tests:
- `test_no_silent_drop_surface_rows`
- `test_missing_required_fields_block`
- `test_unknown_source_mapping_is_review_required`
- `test_source_conflict_blocks_runtime_truth`
- `test_missing_tracking_video_input_blocks_forbidden_claims`

Step gain:
- Engineering: HPFA can track row preservation, source mapping status, source conflict status, and permission blocks.
- Analyst: the analyst can see which event-like rows are readable, missing, conflicted, or blocked before any football interpretation is written.

Allowed language:
- surface rows
- visible rows
- event-like rows
- row-level evidence
- candidate
- blocked
- review_required

Blocked language:
- canonical event count
- complete event truth
- full event stream truth

`canonical_event_count` remains UNKNOWN until a separate explicit HPFA Event Count Validation contract is created, tested, executed on ACTIVE_MATCH, and allowed by governance. Canonical Event Lite validation alone does not unlock canonical event-count claims.

### Lane B — Metric Registry and Claim-Safe Output

Priority: P1

Target HPFA modules:
- Metric Primitive Lite V1
- Metric Family Registry Lite
- Claim Eligibility Gate Lite V1
- Claim-Safe Report Grammar Gate V1
- Runtime Validator

Product outputs to build:
- metric primitive contract
- metric family ontology
- required input field policy
- allowed output level policy
- report grammar router
- runtime status validator

Every metric must define:
- `metric_id`
- `metric_family`
- `required_fields`
- `normalization_policy`
- `sample_policy`
- `role_context_policy`
- `allowed_claim_level`
- `blocked_claims`
- `lineage`
- `failure_mode`

Required tests:
- `test_metric_without_required_fields_blocks`
- `test_metric_label_does_not_create_tactical_truth`
- `test_claim_gate_blocks_forbidden_truth_claims`
- `test_report_grammar_separates_main_reading_from_limits`
- `test_runtime_validator_rejects_unknown_status`

Step gain:
- Engineering: HPFA metrics become contract-bound and cannot execute without declared fields, lineage, sample policy, and claim boundary.
- Analyst: metric output stops pretending to be tactical truth and becomes readable as observation, proxy, candidate, or blocked claim.

### Lane C — Context, Window, Phase, Tempo and Sequence Candidates

Priority: P2

Target HPFA modules:
- Match Context Slicer Lite V1
- Minimum Viable Context Lite V1
- Event Window Builder Lite V1
- Time Scale Router Lite V1
- Axis Integrity Tagger Lite V1
- Phase Lite Candidate Support
- Event-Only Rhythm Evidence Stack support channels

Product outputs to build:
- context slice contract
- window assignment integrity rule
- time context status
- spatial context status
- restart/open-play candidate field
- phase candidate field
- tempo support signal field

Required tests:
- `test_context_sample_truncation_blocks_complete_summary`
- `test_event_index_window_uses_context_ordinal_position`
- `test_period_half_unknown_when_source_missing`
- `test_score_state_unknown_without_goal_timeline`
- `test_card_state_unknown_without_card_timeline`
- `test_phase_candidate_not_phase_truth`
- `test_single_signal_cannot_assign_rhythm_state`

Step gain:
- Engineering: HPFA can slice row-level context by time, window, zone, channel, restart candidate, and phase/rhythm support candidates.
- Analyst: the analyst can distinguish surface context from tactical interpretation and can see when score, card, period, half, or window evidence is UNKNOWN.

Known blocker from PR #94:
- `context_candidates_sample` must not be summarized as complete match evidence when upstream `context_candidate_count` is larger.
- `event_index` windows must use context ordinal position, not source row index.

### Lane D — Analyst Report Grammar and Evidence Packaging

Priority: P1

Target HPFA modules:
- Active Match Analyst Report Lite V1
- Postmatch Analyst Report Lite V1
- Football Output Audit Lite V1
- Runtime Evidence Closure

Product outputs to build:
- L1 analyst reading
- L2 evidence-backed reading
- L3 technical limits block
- evidence reference index
- missing column report
- blocked claim report

Required tests:
- `test_report_contains_evidence_refs`
- `test_report_technical_limits_are_separate`
- `test_report_does_not_repeat_limit_language_as_main_reading`
- `test_report_blocks_forbidden_claims`

Step gain:
- Engineering: HPFA report output becomes evidence-indexed and grammar-gated.
- Analyst: the report can say what was visible, where it was visible, and why it matters without burying the main reading under repeated limitations.

### Lane E — Segmentation, Taxonomy, Classification, Differentiation and Diagnosis

Priority: P1

Purpose:
Create HPFA-native modules for segmentasyon, taksonomi, tasnif, tefrik and teşhis.

This lane does not create tactical truth. It creates structured analyst-facing separation, naming, grouping, contrast, and evidence-qualified diagnosis.

Target HPFA modules:
- Segmentasyon Lite V1
- Taxonomy Registry Lite V1
- Tasnif Classifier Lite V1
- Tefrik Differentiation Gate Lite V1
- Teşhis Diagnostic Gate Lite V1
- Football Output Audit Lite V1
- Claim Eligibility Gate Lite V1

Definitions:

| Term | HPFA meaning | Output status |
|---|---|---|
| Segmentasyon | splitting the event-like surface into bounded parts by time, window, action family, team, zone, or state candidate | segment_candidate |
| Taksonomi | controlled vocabulary and hierarchy for action families, contexts, zones, metric families, and report concepts | registry_entry |
| Tasnif | assigning rows or slices to declared categories using available fields | classified_candidate |
| Tefrik | distinguishing similar categories and preventing false merges | differentiation_decision |
| Teşhis | evidence-qualified diagnostic reading from multiple eligible signals | diagnostic_candidate |

Product outputs to build:
- segmentation contract
- taxonomy registry schema
- classification policy
- differentiation rule set
- diagnostic evidence ladder
- ambiguity and near-miss report
- false-merge blocker
- false-split blocker

Required fields by candidate type:

Segmentasyon candidate:
- `segment_id`
- `segment_axis`
- `start_ref`
- `end_ref`
- `row_count_surface`
- `segment_basis`
- `evidence_refs`

Taxonomy registry entry:
- `taxonomy_id`
- `parent_concept`
- `child_concept`
- `allowed_inputs`
- `forbidden_claims`
- `example_surface_signals`

Tasnif candidate:
- `classification_id`
- `class_label`
- `input_fields_used`
- `confidence_level`
- `ambiguous_with`
- `blocked_claims`

Tefrik decision:
- `differentiation_id`
- `candidate_a`
- `candidate_b`
- `separating_fields`
- `insufficient_fields`
- `decision_status`

Teşhis candidate:
- `diagnosis_id`
- `diagnosis_label`
- `supporting_signals`
- `contradicting_signals`
- `missing_signals`
- `diagnosis_status`
- `claim_boundary`

Required tests:
- `test_segmentation_does_not_drop_surface_rows`
- `test_taxonomy_registry_blocks_unknown_label`
- `test_classification_reports_ambiguous_rows`
- `test_tefrik_prevents_false_merge_without_separating_fields`
- `test_teshis_requires_multiple_eligible_signals`
- `test_teshis_blocks_tactical_truth_without_required_evidence`
- `test_diagnostic_candidate_keeps_claim_boundary`

Step gain:
- Engineering: HPFA gains a formal layer for splitting, naming, grouping, separating, and evidence-qualified diagnosis.
- Analyst: the analyst can see not only what category a row/slice belongs to, but also what it was confused with, why it was separated, and what evidence is still missing.

Claim boundary:
- Segmentasyon does not imply possession, phase, or tactic truth.
- Taksonomi does not imply analytic correctness.
- Tasnif does not imply intent.
- Tefrik does not imply causality.
- Teşhis does not become truth unless the required evidence ladder is met.

Allowed language:
- segment candidate
- taxonomy entry
- classified candidate
- differentiation decision
- diagnostic candidate
- ambiguity retained
- requires validation

Blocked language:
- confirmed tactic
- coach plan
- dominance
- intentional structure
- off-ball diagnosis
- fatigue diagnosis

## Forbidden HPFA claims without extra evidence

The following must remain blocked unless future product modules provide explicit eligible evidence:

- coach intention
- pitch control truth
- off-ball structure truth
- fatigue truth
- dominance truth
- clean tactical truth
- body orientation truth
- physical load truth

## Status vocabulary

Do not use PASS alone.

Allowed statuses:
- DISCOVERY_PASS_PLAN_ONLY
- SPEC_ONLY
- REVIEW_REQUIRED
- FAIL_CLOSED
- SMOKE_PASS
- ACTIVE_MATCH_EVIDENCE_PASS
- PRODUCTION_RELEASE

`SMOKE_PASS` is not `ACTIVE_MATCH_EVIDENCE_PASS`.
`ACTIVE_MATCH_EVIDENCE_PASS` is not automatically `PRODUCTION_RELEASE`.

## Intake checklist for every donor capability

Each imported idea must have this record:

```json
{
  "source_repo": "string",
  "source_role": "GITHUB_DONOR_REPO|DRIVE_GOVERNANCE|DRIVE_DONOR_LIBRARY|DROPBOX_ARCHIVE|DROPBOX_DONOR_LIBRARY|SIDER_ACADEMIC_BACKING",
  "source_path": "string",
  "capability": "string",
  "target_hpfa_module": "string",
  "adaptation_type": "CONTRACT|SCHEMA|VALIDATION|REGISTRY|RUNTIME|REPORT_GRAMMAR|TEST|SEGMENTATION|TAXONOMY|CLASSIFICATION|DIFFERENTIATION|DIAGNOSIS",
  "claim_boundary": "string",
  "engineering_gain": ["string"],
  "analyst_gain": ["string"],
  "required_tests": ["string"],
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Immediate build order

1. Close PR #94 blockers before treating Match Context Slicer as runtime-ready.
2. Build Lane A contract and tests.
3. Build Lane E taxonomy and segmentation contracts because later lanes need stable categories.
4. Build Lane B contract and tests.
5. Build Lane D grammar gate and evidence package.
6. Build Lane C candidate-support modules only after upstream gates are stable.
7. Audit HP-PROJELERI before using it as governance authority.

## Current conclusion

The other repositories are useful as capability donors. They must be modernized into HPFA through product contracts, not copied into the product repo. HPFA remains the only executable product authority.

Every step must now report what was gained, what remains blocked, and which claim boundary changed or stayed unchanged.
