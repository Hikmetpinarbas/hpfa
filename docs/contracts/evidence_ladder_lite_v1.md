# HPFA Evidence Ladder Lite V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Claim safety: EVIDENCE_LADDER_ONLY
Rule: ADAPT_NOT_COPY

This document defines the first HPFA evidence-level contract. It prevents surface observations, context candidates, classifications, mechanisms and diagnostics from becoming truth claims too early.

## Step gain record

```json
{
  "step_id": "EVIDENCE_LADDER_LITE_V1",
  "source_repo": "HP-Engine|HP-Motor-main|HP-Motor",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "evidence_ladder_lite",
  "engineering_gain": [
    "evidence level contract",
    "claim eligibility boundary",
    "diagnostic candidate guard",
    "single-signal truth blocker",
    "report grammar support"
  ],
  "analyst_gain": [
    "analyst can see whether a sentence rests on surface observation, candidate context, classification, mechanism or diagnostic candidate",
    "candidate labels cannot silently become football truth",
    "blocked claims remain visible before report text is written"
  ],
  "new_blockers": [
    "executable gate not implemented",
    "runtime evidence required",
    "Football Ontology Registry Lite must define stable labels"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Purpose

Evidence Ladder Lite defines the permitted evidence levels used by future modules and reports.

It answers one question:

```text
What can HPFA safely say from this evidence level?
```

## Evidence levels

### L0_SOURCE_PRESENT

Meaning:

Source file or upstream output exists and is readable.

Allowed language:

- source available
- file readable
- upstream output found

Blocked language:

- football evidence shows
- action pattern detected
- diagnostic candidate

### L1_SURFACE_OBSERVATION

Meaning:

Row-level visible surface evidence is readable after source governance checks.

Allowed language:

- row-level evidence shows
- visible surface evidence indicates
- action-family volume suggests

Blocked language:

- tactical truth
- dominance truth
- coach intention
- possession truth
- phase truth

### L2_CONTEXT_CANDIDATE

Meaning:

A row or slice has candidate context such as team, period, minute, zone, channel, score state candidate, card state candidate, restart candidate or window candidate.

Allowed language:

- context candidate detected
- zone candidate present
- window candidate assigned
- requires validation

Blocked language:

- clean phase truth
- possession truth
- off-ball structure truth

### L3_CLASSIFICATION_CANDIDATE

Meaning:

A row, slice or segment is assigned to a controlled taxonomy class, while ambiguity is preserved.

Allowed language:

- classified candidate
- ambiguity retained
- differentiated from nearby candidate

Blocked language:

- intent
- causality
- confirmed tactic

### L4_MECHANISM_CANDIDATE

Meaning:

Multiple eligible observations support a possible mechanism, but not a truth claim.

Allowed language:

- mechanism candidate
- supporting signals indicate
- contradicting signals remain

Blocked language:

- the team deliberately
- the coach planned
- tactical mechanism confirmed

### L5_DIAGNOSTIC_CANDIDATE

Meaning:

A diagnostic reading is supported by multiple eligible signals and routed through claim safety, but remains candidate-only unless a later product gate allows stronger wording.

Allowed language:

- diagnostic candidate
- evidence-qualified reading
- requires later validation

Blocked language:

- diagnosis truth
- dominance truth
- fatigue truth
- off-ball truth
- pitch-control truth

### L6_CLAIM_ELIGIBLE

Meaning:

A future claim gate may allow a narrow, explicitly scoped analyst sentence.

Allowed language:

- claim eligible within stated boundary
- evidence-backed reading

Blocked language:

- any claim outside the explicit boundary
- production release claim without release status

### L7_CLAIM_BLOCKED

Meaning:

The signal, field, module or output is insufficient for the requested claim.

Allowed language:

- blocked by missing input
- blocked by claim boundary
- blocked by unresolved source conflict

Blocked language:

- softened truth claim
- implied dominance
- implied intent

## Ladder promotion rules

A module may promote evidence by one level only when all required conditions are met:

- required upstream modules exist
- required fields are present
- source conflicts are resolved or explicitly blocked
- ambiguity is retained
- forbidden claims are listed
- runtime status is REVIEW_REQUIRED or stronger
- output contains evidence references

No module may promote evidence directly from L1_SURFACE_OBSERVATION to L5_DIAGNOSTIC_CANDIDATE.

No single signal can create L4_MECHANISM_CANDIDATE or L5_DIAGNOSTIC_CANDIDATE.

## Required output fields for future executable module

- module_id
- status
- decision
- input_artifacts
- evidence_items
- evidence_level_counts
- promoted_items
- blocked_items
- blocked_claims
- missing_inputs
- ambiguity_report
- claim_boundary
- release_status

## Required evidence item fields

- evidence_id
- source_module
- source_file
- source_ref
- evidence_level
- label
- allowed_language
- blocked_language
- required_fields_used
- missing_fields
- supporting_signals
- contradicting_signals
- claim_boundary

## Integration points

This contract supports:

- Football Ontology Registry Lite
- Claim Eligibility Gate Lite
- Claim-Safe Report Grammar Gate V1
- Football Output Audit Lite
- Diagnostic Candidate Gate Lite
- Metric Dependency Graph Lite
- Module Dependency Graph Lite

## Required tests

- test_single_signal_cannot_create_mechanism_candidate
- test_surface_observation_cannot_become_diagnostic_candidate_directly
- test_diagnostic_candidate_blocks_truth_language
- test_blocked_claims_are_reported
- test_ambiguity_report_required_for_classification_candidate
- test_claim_eligible_requires_boundary
- test_no_canonical_event_count_claim
- test_no_sample_match_identity_leak

## Claim boundary

This ladder does not create:

- canonical event count
- complete event truth
- tactical truth
- coach intention
- pitch control truth
- off-ball structure truth
- fatigue truth
- dominance truth
- possession truth
- phase truth
- sequence truth

## Release rule

This contract is SPEC_ONLY. It requires executable code, schema validation, tests, ACTIVE_MATCH runtime evidence and football output audit before any stronger status is allowed.
