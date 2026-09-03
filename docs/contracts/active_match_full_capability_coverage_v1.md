# ACTIVE_MATCH Full Capability Coverage V1

## Purpose

Make a real-match full-spine run disclose repository-wide capability coverage instead of allowing `FULL_SPINE_COMPLETED` to be read as “every product capability was exercised.”

## Product Node

`active_match_spine_runner`

Rehabilitates the existing `capability_closure_guard_lite` discovery vocabulary and current producer-ledger artifacts. No parallel football engine is created.

## Question

For every top-level module family under `hpfa/modules/*/*`, did the current ACTIVE_MATCH invocation produce execution evidence, contribute match-analysis evidence, operate only as a control, or remain outside the run for an explicit reason?

## Coverage States

- `EXECUTED_CONTRIBUTED`
- `EXECUTED_CONTROL_ONLY`
- `SUPERSEDED_NOT_CURRENT`
- `INTENTIONAL_WAIT_CLAIM_GATE`
- `SUPPORT_ONLY_NOT_EVENT_TRUTH`
- `NOT_EVIDENCED_REQUIRES_REVIEW`
- `UNWIRED_CURRENT_CAPABILITY`

V1 is producer-evidence based. Module existence or static import is not runtime proof.

## Outputs

Directly under the allowed phone output root:

- `HPFA_ACTIVE_MATCH_CAPABILITY_COVERAGE.json`
- `HPFA_ACTIVE_MATCH_CAPABILITY_COVERAGE.txt`

Both outputs must be included in the standard `HPFA_ACTIVE_MATCH_BUNDLE.zip` through the existing producer-declared current-invocation artifact ledger.

## Acceptance Invariants

1. Every top-level module family receives exactly one coverage state.
2. An eligible module without current-invocation execution evidence is visible as review debt; it is never silently counted as executed.
3. Support/reference capabilities remain outside event truth.
4. Superseded and intentional-wait capabilities are not forced into runtime football truth.
5. Coverage evidence is match-agnostic; `test_no_sample_match_identity_leak` is mandatory.
6. Coverage cannot promote canonical-event, true-action, phase, possession, sequence, tactical, causal or production truth.
7. `FULL_SPINE_COMPLETED` remains distinct from repository-wide capability coverage and from `ACTIVE_MATCH_EVIDENCE_PASS`.
8. A later tranche may instrument presently unproven capabilities, but V1 must first make those gaps explicit.

## Claim Ceiling

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `phase_truth=false`
- `possession_truth=false`
- `sequence_truth=false`
- `tactical_truth=false`
- `production_release=false`

## Release State

`SPEC_CORRECTION_ACCEPTED / IMPLEMENTATION_IN_PR / REVIEW_REQUIRED / ACTIVE_MATCH_REQUIRED / NOT_PRODUCTION`
