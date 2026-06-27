# P2I Signal Promotion Matrix Notes V1

Status: SPEC_ONLY / REVIEW_REQUIRED

Linked PR: #92

## Purpose

This note explains the P2I signal promotion matrix.

P2I must not promote ontology or style signals by language strength. Promotion must depend on source-layer coverage, time-space-action support, proof bundle, falsifier, counter-scenario, missing evidence and claim safety.

## Promotion Ladder

LOW_SIGNAL -> CANDIDATE_SIGNAL -> SUPPORTED_CANDIDATE -> CLAIM_GATE_REQUIRED -> BLOCKED

## LOW_SIGNAL

LOW_SIGNAL can be produced when a surface cue exists but is not yet supported enough for a candidate.

Allowed output: low_signal_note.

Blocked output: style_candidate, recommendation_candidate, final_judgement.

## CANDIDATE_SIGNAL

CANDIDATE_SIGNAL requires source, time or window, space or zone, action and claim layers.

Allowed output: ontology_candidate.

Blocked output: style truth, final judgement, tactical truth.

## SUPPORTED_CANDIDATE

SUPPORTED_CANDIDATE requires a repeated evidence cluster and a proof bundle.

Allowed output: style_candidate.

Blocked output: style truth, tactical truth, coach intention, dominance or control claim.

## CLAIM_GATE_REQUIRED

CLAIM_GATE_REQUIRED is the maximum pre-audit status before analyst-facing judgement.

Allowed output: recommendation_candidate and analyst_note_candidate.

Blocked output: instruction, guaranteed fix and causal prescription.

## BLOCKED

BLOCKED is fail-closed.

Allowed output: blocked_claim_record.

Blocked output: all analyst-facing outputs.

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.

No production release claim.
