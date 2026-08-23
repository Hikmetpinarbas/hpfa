# Provider Metric Dictionary Lite V1 — Research-Hardened Reconstruction

## Purpose
Reconstruct historical PR #183 as the current Landing 1B provider-definition registry without copying its older trust assumptions.

## Authority and dependency
- current product base: research-hardened Aggregate Definition Alignment (#181 reconstruction)
- upstream metric semantics: `configs/metrics/metric_registry_v1.json`
- upstream denominator policy: `configs/metrics/metric_denominator_policy_v1.json`
- upstream aggregate fingerprint: `sportsbase_aggregate_definition_candidates_v1.json`
- historical #183 is DONOR_SUPPORT only (`ADAPT_NOT_COPY`)
- HP-Engine metric registry schema contributes lineage/aggregation/evidence-policy ideas only; it is not runtime truth

## DefinitionFingerprint
Every dictionary record MUST carry and hash the equality-critical fields declared by AR-GE R07:
`provider_id/version, source_role, metric_id, construct, unit/semantic_type, numerator, denominator, eligibility_scope, success/outcome rule, spatial rule, temporal window, aggregation level, missing/zero-denominator policy, derivation lineage, definition source/status, claim ceiling`.

A label, arithmetic reproduction or correlation never substitutes for this fingerprint.

## Provider admission
`provider_candidate != validated_provider_identity`.
A provider metric can enter `provider_definition_ready_metric_ids` only when all are true:
1. `definition_evidence_status=REVIEWED_PROVIDER_DEFINITION`
2. provider identity/version are explicit and not placeholder/UNKNOWN
3. `provider_binding_admitted=true`
4. source role is authoritative for that binding
5. upstream fingerprint/denominator bindings, when declared, are exact.

Current SportsBase rows deliberately remain provider-definition candidates. This reconstruction does not invent SportsBase version or proprietary formula truth.

## HPFA domain contracts
HPFA analyst contracts are stored under `provider_id=hpfa`, `source_role=HPFA_DOMAIN_CONTRACT`, and `domain_contract_admitted=true`.
They may define an HPFA construct but cannot validate an external provider label. In particular:
- provider-labelled `Progressive open passes` is separated from HPFA `progressive_open_pass` one-action continuation contract;
- provider-labelled `Final third entries` is separated from HPFA `final_third_boundary_entry` and `final_third_access_established`.

## Reference-only definitions
External glossary/convention material can remain `REFERENCE_ONLY_REVIEWED_DEFINITION`; reference status never opens ACTIVE_MATCH provider binding.

## Claim boundary
- no metric values
- no comparison
- no provider-invariant equivalence
- no canonical event count
- no tracking/off-ball/pressure/pitch-control truth
- no production release

Expected current state is structurally valid but `REVIEW_REQUIRED` until provider identity/version and provider definitions are actually admitted.
