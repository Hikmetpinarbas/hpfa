# HPFA Football Ontology Registry Lite V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Claim safety: ONTOLOGY_REGISTRY_ONLY
Rule: ADAPT_NOT_COPY

This document defines a controlled HPFA vocabulary layer for football concepts. It does not create tactical truth, event-count truth, possession truth, phase truth, sequence truth or diagnosis truth.

## Step gain record

```json
{
  "step_id": "FOOTBALL_ONTOLOGY_REGISTRY_LITE_V1",
  "source_repo": "HP-Motor-main|HP-Motor|HP-Engine",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "football_ontology_registry_lite",
  "engineering_gain": [
    "controlled football vocabulary contract",
    "action-family registry contract",
    "metric-family registry contract",
    "context-concept registry contract",
    "claim-boundary fields for ontology entries"
  ],
  "analyst_gain": [
    "football terms become consistent across reports, metrics and gates",
    "action families can be read without converting labels into tactical truth",
    "ambiguous concepts can be marked before report language is written"
  ],
  "new_blockers": [
    "executable registry builder not implemented",
    "taxonomy validation tests not implemented",
    "ACTIVE_MATCH runtime evidence required before stronger status"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Purpose

Create one HPFA-native ontology registry contract used by:

- action family taxonomy
- metric family taxonomy
- goalkeeper taxonomy
- context concepts
- segmentation labels
- classification labels
- report grammar concepts

## Required ontology entry fields

Every registry entry must include:

- ontology_id
- label_en
- label_tr
- concept_family
- parent_concept
- allowed_inputs
- required_fields
- optional_fields
- forbidden_claims
- allowed_language
- blocked_language
- ambiguity_policy
- evidence_level
- source_lineage
- release_status

## Concept families

Allowed concept families:

- ACTION_FAMILY
- METRIC_FAMILY
- CONTEXT_CONCEPT
- SEGMENT_CONCEPT
- CLASSIFICATION_CONCEPT
- DIAGNOSTIC_CONCEPT
- REPORT_CONCEPT
- GOALKEEPER_CONCEPT
- RESTART_CONCEPT
- TEMPORAL_CONCEPT
- SPATIAL_CONCEPT

Unknown concept families must be rejected or marked REVIEW_REQUIRED.

## Initial action-family candidates

These are candidate registry labels only:

- PASS
- CARRY
- SHOT
- DUEL_PRESSURE
- BALL_LOSS
- RECOVERY
- FOUL
- RESTART
- GOALKEEPER_ACTION
- POSITIONAL_ATTACK_SIGNAL
- CARD_SIGNAL
- GOAL_SIGNAL
- PERIOD_MARKER

## Initial metric-family candidates

These are candidate registry labels only:

- VOLUME
- PROGRESSION
- RISK
- CONSEQUENCE
- PRESSURE
- RECOVERY
- TEMPORAL
- SPATIAL
- GOALKEEPER
- RHYTHM_SUPPORT

## Initial context concepts

These are candidate registry labels only:

- TEAM_CANDIDATE
- PLAYER_CANDIDATE
- PERIOD_CANDIDATE
- HALF_CANDIDATE
- MINUTE_BUCKET
- ZONE_CANDIDATE
- CHANNEL_CANDIDATE
- WINDOW_CANDIDATE
- SCORE_STATE_CANDIDATE
- CARD_STATE_CANDIDATE
- RESTART_CANDIDATE
- OPEN_PLAY_CANDIDATE

## Evidence levels

Allowed evidence levels:

- SURFACE_OBSERVATION
- CONTEXT_CANDIDATE
- CLASSIFICATION_CANDIDATE
- MECHANISM_CANDIDATE
- DIAGNOSTIC_CANDIDATE
- CLAIM_BLOCKED
- CLAIM_ELIGIBLE

Lite ontology entries must default to SURFACE_OBSERVATION or CONTEXT_CANDIDATE unless another product gate explicitly allows a higher level.

## Claim boundary

Ontology labels do not create:

- tactical truth
- coach intention
- pitch control truth
- off-ball structure truth
- fatigue truth
- dominance truth
- canonical event count
- complete event truth
- phase truth
- possession truth
- sequence truth

## Output files for future executable module

When implemented, the module should emit flat phone-safe outputs:

- football_ontology_registry_lite_v1.json
- football_ontology_registry_lite_v1.txt

## Required tests

- test_ontology_entry_requires_claim_boundary
- test_unknown_concept_family_is_review_required
- test_action_family_label_does_not_create_tactical_truth
- test_metric_family_label_does_not_create_metric_truth
- test_diagnostic_concept_remains_candidate
- test_forbidden_claims_present_for_each_entry
- test_no_canonical_event_count_claim
- test_no_sample_match_identity_leak

## Release rule

This contract is SPEC_ONLY. It requires executable code, schema validation, tests, ACTIVE_MATCH runtime evidence and football output audit before any stronger status is allowed.
