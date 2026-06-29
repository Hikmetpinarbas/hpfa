# HPFA Pattern Candidate Engine Lite V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Source role: GITHUB_DONOR_REPO
Donor basis: HP-Engine pattern engine
Rule: ADAPT_NOT_COPY

This contract defines a HPFA-native pattern candidate layer. It turns context/sequence/graph-compatible surfaces into analyst-facing behaviour candidates. It does not create tactical truth, coach intention, dominance truth, possession truth, phase truth or sequence truth.

## Step gain record

```json
{
  "step_id": "PATTERN_CANDIDATE_ENGINE_LITE_V1",
  "source_repo": "HP-Engine",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "pattern_candidate_engine_lite",
  "engineering_gain": [
    "pattern candidate contract",
    "behaviour candidate output schema direction",
    "degraded pattern handling",
    "source metric lineage requirement",
    "analyst intelligence layer entry point"
  ],
  "analyst_gain": [
    "reports can move from action volume toward candidate behaviour reading",
    "directness, sustained build-up, transition, switching and instability can be surfaced as candidates",
    "partial or degraded patterns remain visible instead of becoming hidden failures"
  ],
  "new_blockers": [
    "executable module not implemented",
    "ACTIVE_MATCH runtime evidence required",
    "requires context/sequence candidate inputs before match-level use",
    "single pattern cannot create tactical truth"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Purpose

The module answers:

```text
Which behaviour pattern candidates are visible in the match surface, and how strong or degraded are they?
```

It is an analyst intelligence module, not a claim engine.

## Required upstream inputs

Future executable work must accept only HPFA product outputs, not donor runtime files:

- Match Context Slicer Lite V1 output
- Sequence Candidate Engine Lite V1 output when available
- Metric Dependency Graph Lite V1 output when available
- Evidence Ladder Lite V1 output when available

If sequence input is missing, the module may emit only context-pattern candidates and must block sequence-pattern candidates.

## Candidate pattern families

Initial pattern families:

- DIRECT_ATTACK_BIAS_CANDIDATE
- SUSTAINED_BUILD_UP_CANDIDATE
- TRANSITION_ATTACK_CANDIDATE
- CENTRAL_PROGRESSION_CANDIDATE
- SWITCH_TENDENCY_CANDIDATE
- SHOT_PRESSURE_CANDIDATE
- CONTESTED_INSTABILITY_CANDIDATE
- CHANNEL_CONCENTRATION_CANDIDATE
- RESTART_ATTACK_CANDIDATE
- TERMINAL_PRESSURE_CANDIDATE
- RECYCLE_BEHAVIOUR_CANDIDATE
- FAILURE_CASCADE_CANDIDATE

Unknown pattern families must be REVIEW_REQUIRED.

## Required output files

When implemented, user-visible outputs must be flat under the HPFA phone output root:

- pattern_candidate_engine_lite_v1.json
- pattern_candidate_engine_lite_v1.txt

## Required output fields

- module_id
- status
- decision
- claim_safety
- input_artifacts
- pattern_candidate_count
- degraded_pattern_candidate_count
- pattern_candidates
- degraded_pattern_candidates
- blocked_pattern_candidates
- pattern_summary
- missing_inputs
- evidence_refs
- claim_boundary
- release_status

## Required pattern candidate fields

- pattern_id
- pattern_family
- label
- evidence_level
- strength_candidate
- confidence_candidate
- degraded_flag
- evidence_count
- source_metric_ids
- source_context_refs
- source_sequence_refs
- supporting_signals
- contradicting_signals
- missing_inputs
- allowed_language
- blocked_language
- claim_allowed

## Decisions

- PATTERN_CANDIDATES_ONLY
- REVIEW_REQUIRED_MISSING_SEQUENCE_INPUT
- REVIEW_REQUIRED_DEGRADED_PATTERN_ONLY
- FAIL_CLOSED_MISSING_REQUIRED_CONTEXT

## Allowed language

- pattern candidate detected
- degraded pattern candidate
- sequence surface indicates
- context evidence suggests
- transition attack candidate
- switch tendency candidate
- contested instability candidate
- requires validation

## Blocked language

- confirmed tactic
- team deliberately
- coach planned
- dominance
- control of the pitch
- off-ball structure
- intent
- causality

## Required tests

- test_missing_context_input_fail_closed
- test_missing_sequence_blocks_sequence_patterns
- test_unknown_pattern_family_review_required
- test_degraded_pattern_remains_candidate
- test_single_pattern_does_not_create_tactical_truth
- test_pattern_candidate_contains_evidence_refs
- test_pattern_candidate_blocks_dominance_language
- test_no_sample_match_identity_leak

## Claim boundary

Pattern candidates do not create:

- tactical truth
- coach intention
- dominance truth
- pitch control truth
- off-ball truth
- phase truth
- possession truth
- sequence truth
- causal truth

## Release rule

This contract is SPEC_ONLY. It requires executable code, schema validation, tests, ACTIVE_MATCH runtime evidence and football output audit before any stronger status is allowed.
