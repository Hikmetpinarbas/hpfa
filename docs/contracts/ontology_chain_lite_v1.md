# P2I Ontology Chain Lite V1

Status: SPEC_ONLY / REVIEW_REQUIRED

Linked issue: #91

## Purpose

P2I defines the HPFA ontology chain for game-surface reading and style-candidate detection.

It is downstream of R1 permission closure, P2C Event-Time-Space Binder, sequence/phase/value/player-role gates, Claim Eligibility Gate and Football Output Audit.

It does not create production release and does not create tactical truth.

## Core Chain

```text
Detection -> Evidence -> Recommendation
```

Turkish analyst wording:

```text
Tespit -> Ispat -> Oneri
```

## Operating Principle

The system must read available rows and columns through the following layers:

```text
source -> time -> space -> action -> context -> sequence -> value -> player -> opponent -> claim
```

The match is decomposed first into evidence objects, then recombined into ontology and style candidates.

## Required Objects

- game_ontology_registry_lite_v1
- style_signal_registry_lite_v1
- detection_evidence_table
- proof_bundle_table
- recommendation_candidate_table
- ontology_claim_safety_table

## Detection Layer

A detection is not a conclusion. It is a repeated surface signal.

Example fields:

- detection_id
- signal_family
- source_layers_used
- evidence_object_ids
- repetition_count
- zone_support
- time_support
- opponent_correspondence_support
- uncertainty_penalty
- status

Allowed status values:

- LOW_SIGNAL
- CANDIDATE_SIGNAL
- SUPPORTED_CANDIDATE
- CLAIM_GATE_REQUIRED
- BLOCKED

## Evidence Layer

Every detection must carry a proof bundle.

Minimum fields:

- direct_rows_or_atoms
- supporting_windows
- supporting_sequences_if_available
- aggregate_support_if_available
- falsifier
- counter_scenario
- missing_evidence
- blocked_interpretations

## Recommendation Layer

A recommendation is not a treatment instruction.

Allowed output:

- recommendation_candidate
- analyst_note_candidate
- review_required_suggestion

Blocked output:

- treatment instruction
- coach intent statement
- guaranteed fix
- causal prescription without gate

## Ontology Families

P2I may define ontology families as registry labels only:

- build_up_surface
- progression_surface
- final_third_surface
- transition_surface
- restart_surface
- recovery_surface
- loss_surface
- pressure_exposure_surface
- corridor_surface
- player_role_surface
- opponent_response_surface
- consequence_surface

These are not truth labels.

## Style Candidate Families

P2I may emit style candidates only after enough evidence objects exist:

- direct_progression_candidate
- circulation_candidate
- wide_access_candidate
- central_progression_candidate
- transition_candidate
- restart_dependency_candidate
- high_value_moment_candidate
- pressure_exposure_candidate
- territory_bias_candidate
- player_role_dependency_candidate

Single-match style outputs must remain match-surface candidates. Multi-match or season style truth requires a later explicit validation gate.

## Claim Boundary

Allowed wording:

- ontology surface
- style candidate
- repeated evidence cluster
- evidence-supported suggestion
- recommendation candidate
- requires later validation

Blocked wording:

- tactical truth
- coach intention
- dominance/control truth
- style truth without multi-match validation
- treatment instruction without human review
- causality without design evidence

## Required Tests

- test_detection_requires_evidence_bundle
- test_recommendation_cannot_be_treatment_instruction
- test_single_match_style_remains_candidate
- test_ontology_family_is_registry_label_only
- test_claim_gate_required_before_final_style_judgement
- test_no_control_dominance_or_intent_language
- test_no_sample_match_identity_leak

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.

P2I is not production release.
