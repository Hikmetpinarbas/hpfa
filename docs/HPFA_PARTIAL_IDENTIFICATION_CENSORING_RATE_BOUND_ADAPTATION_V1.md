# HPFA Partial Identification / Censoring Rate Bound Adaptation V1

NODE: hpfa_partial_identification_censoring_rate_bound_adaptation_v1
STATUS: IMPLEMENTED_ON_EXISTING_OWNER_PENDING_EXACT_HEAD_CI_AND_PHYSICAL_ACCEPTANCE

## Product question

When eligible process-family members have unresolved visible outcomes, what match-local rate statement remains defensible without coding unknown as failure or success?

## Source basis

Primary handoff: Google Drive `HPFA_OPERATOR_READY_NEW_RESEARCH_DELTA_2026-09-18_v1`, ADAY 024.

The living Drive ledgers require rehabilitation of:
`safe_finding_occurrence_consequence_burden_adapter.py`

No separate statistics engine is created.

Dropbox research archive search did not surface a stronger current product-bound partial-identification donor in this pass. Existing Dropbox counter-evidence doctrine remains SUPPORT only.

Context7 current pytest documentation supports deterministic parametrized/table-driven regression patterns and `pytest.approx` for floating-bound assertions.

Hugging Face paper search was requested for research support, but the current connector paper-search endpoint was unavailable during this implementation pass; no HF result is treated as product authority.

## Contract

For a binary visible-outcome construct with already-admitted eligible denominator membership:

- s = resolved visible success
- f = resolved visible failure
- u = eligible but visible-outcome unresolved
- N = s + f + u
- lower = s / N
- upper = (s + u) / N

States:

- denominator membership unresolved => `BOUND_UNRESOLVED`, no numeric interval
- target outcome semantics unresolved => `BOUND_UNRESOLVED`, no numeric interval
- N = 0 => `NO_OPPORTUNITY`
- u = 0 => `POINT_IDENTIFIED_OBSERVED_RATE`
- u > 0 => `PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE`

The interval is an identification interval, NOT a confidence interval.

## Denominator integrity

The runtime adapter uses unique observable-process-family member `sequence_ref` values. Repeated family/projection rows with the same sequence ref cannot duplicate N.

Current admitted process-family membership is the only denominator basis used here. Absence, latent playability, off-ball availability, or an inferred passing lane cannot create eligibility.

## Claim ceiling

`MATCH_LOCAL_VISIBLE_OUTCOME_RATE_BOUND_ONLY`

Forbidden inference:

- true success probability
- population rate
- causal effect
- tactical quality
- confidence/uncertainty interval interpretation
- unknown = failure
- unknown = success
- denominator membership from absence

The adapter cannot authorize EMIT, strengthen an existing claim ceiling, or create evidence.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
