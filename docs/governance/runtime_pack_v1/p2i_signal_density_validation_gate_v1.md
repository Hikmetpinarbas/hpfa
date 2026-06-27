# P2I Signal Density Validation Gate V1

Status: SPEC_ONLY / REVIEW_REQUIRED

Linked PR: #92

## Purpose

Define the minimum validation logic before a P2I ontology or style signal can be promoted from LOW_SIGNAL to CANDIDATE_SIGNAL or SUPPORTED_CANDIDATE.

This is not an implementation. It is a guard for future validators.

## Runtime authority

Only ACTIVE_MATCH runtime outputs are executable truth.

Google Drive, Dropbox, Scholar Gateway, Sider Scholar and Consensus remain support or donor sources.

## External support summary

### Dropbox

Dropbox contains tactical ontology donor material:

- TACTICAL_ONTOLOGY_CLAIM_GUARDS_V1.md
- TACTICAL_ONTOLOGY_RUNTIME_USE_V1.md
- TACTICAL_ONTOLOGY_PACK_V1.csv
- TACTICAL_ONTOLOGY_SEED_B01.csv

Use: donor vocabulary and claim-guard support only.

### Google Drive

Google Drive contains HPFA event ontology and behaviour classification material, metric literacy material, and ontology-first failure/audit material.

Use: methodology, vocabulary and safe interpretation support only.

### Scholar Gateway

Scholar Gateway support indicates that tactical behaviour analysis depends on feature construction, spatial aggregation and temporal aggregation, and that event-based time windows are important for making spatial signals interpretable.

Use: academic support for multi-signal and event-window requirements.

### Sider Scholar

Sider Scholar retrieved Goes et al. 2020 and related soccer tactical behaviour material, but broad queries also produced noisy non-football results.

Use: secondary recall only unless a result is clearly relevant and individually reviewed.

### Consensus

Consensus quota was exhausted during this run.

Use: no new evidence from Consensus in this iteration.

## Gate logic

A P2I signal must not be promoted from LOW_SIGNAL unless it has at least:

1. source layer support
2. time or window support
3. space or zone support
4. action-family support
5. claim boundary record

A P2I signal must not be promoted to SUPPORTED_CANDIDATE unless it has at least:

1. repeated evidence cluster
2. proof bundle
3. falsifier or counter-scenario
4. missing evidence report
5. claim safety table entry

## Style candidate logic

Single-match style outputs remain match-surface candidates.

Season or multi-match style truth requires a later explicit validation contract.

## Recommendation logic

A recommendation candidate requires:

- evidence bundle id
- human review required flag
- blocked instruction check
- claim gate pending or passed status

A recommendation candidate must not be rendered as treatment instruction.

## Required future tests

- test_p2i_low_signal_requires_minimum_layers
- test_p2i_supported_candidate_requires_proof_bundle
- test_p2i_supported_candidate_requires_falsifier
- test_p2i_style_truth_blocked_for_single_match
- test_p2i_recommendation_requires_human_review
- test_p2i_sider_noisy_results_are_not_authority
- test_p2i_external_sources_do_not_override_active_match

## Status

SPEC_ONLY / REVIEW_REQUIRED.
No production release claim.
