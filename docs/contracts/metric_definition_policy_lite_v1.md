# Metric Definition Policy Lite V1

## Purpose

This node turns metric labels into versioned **definition candidates** with explicit numerators, denominators, scope, context, aggregation algebra, construct limits, exposure authority, calibration requirements, misuse warnings and claim ceilings.

It does not compute metric values and does not validate provider equivalence, construct validity, playing-time truth or aggregate equivalence.

## Position

`cross-format reconciliation → metric definition policy → aggregate-definition alignment → row/event eligibility`

The node is upstream of metric comparison and downstream of source provenance. It does not authorize consequence, value, quality, possession, phase, spatial or tactical claims.

## Research-hardening admission

### R07 — Definition fingerprint

Every metric definition candidate receives a deterministic SHA-256 fingerprint over its semantic definition fields. A shared label or header is never enough for semantic equivalence. Fingerprint equality is definition-candidate evidence only; it is not construct or provider-equivalence truth.

### R17 — Construct validity

`definition correctness != construct validity`.

A complete metric definition remains `UNVALIDATED_CONSTRUCT_CANDIDATE` until external/declared validation admits what the measure can represent. Definition completeness cannot promote quality, intent, causal or tactical claims.

### R18 — Aggregation algebra

Every metric declares one aggregation class:

- `SUMMABLE_COUNT`
- `DENOMINATOR_RECOMPUTABLE_RATE`
- `EQUAL_STRATUM_MEAN_ONLY`
- `STANDARDIZATION_REQUIRED`
- `HIERARCHICAL_MODEL_REQUIRED`
- `AGGREGATION_UNKNOWN`
- `AGGREGATION_REJECTED`

Rate-like values are not made summable by label similarity and are not averaged across unequal strata by default.

### R19 — Denominator set closure

Denominator policy carries explicit set semantics including `denominator_set_id`, numerator-subset status, component relation, exclusivity, exhaustiveness, uncovered-opportunity state and denominator nucleus count. A rate can be policy-defined while calculation remains blocked when denominator-set closure is unknown. `VIOLATED` subset status fails closed.

### R22 — Exposure authority / per-90

Clock-time exposure is a separate `EXPOSURE_NORMALIZATION` construct. `MINUTES_PLAYED` is not physical-cost truth. First-to-last observed action span, raw event interval or provider numeric minutes without an admitted operational definition cannot authorize per-90. `per_90` requires an explicit exposure policy and `VALIDATED` exposure authority before calculation admission.

## Inputs

- `configs/metrics/metric_registry_v1.json`
- `configs/metrics/metric_denominator_policy_v1.json`
- `configs/metrics/metric_context_schema_v1.json`
- `configs/metrics/metric_confidence_rules_v1.json`
- `configs/metrics/metric_misuse_warnings_v1.json`
- `configs/metrics/metric_exposure_policy_v1.json`

All policy references and versions must resolve. Rate-like metrics require a declared denominator and explicit zero/missing denominator behavior.

## Outputs

- normalized metric-definition candidates
- deterministic definition fingerprints
- definition-correctness vs construct-validity separation
- aggregation-class declaration
- denominator-set closure status
- exposure-authority/per-90 admission status
- policy reference resolution
- comparison eligibility
- misuse warnings and claim ceilings
- fail-closed gaps

## Hard blocks

- missing or duplicate metric ID
- missing metric family, construct target, aggregation class, value type, unit, numerator, scope or observation window
- invalid aggregation class
- rate/percentage without a denominator definition
- unresolved denominator, context, confidence, misuse or required exposure policy
- unhandled zero/missing denominator
- missing R19 denominator-set fields
- violated numerator-subset relation
- per-90 without explicit exposure policy
- exposure policy that treats playing time as physical-cost semantics
- missing `does_not_measure` or `forbidden_claims`
- comparison requested without explicit aggregate-definition and construct-validity admission
- policy-version mismatch

## Claim boundary

Allowed language:

- “metric-definition candidate”
- “definition fingerprint candidate”
- “provider-bound descriptive rate candidate”
- “denominator closure unresolved”
- “per-90 blocked pending exposure authority”
- “comparison blocked until definition/construct admission”

Forbidden promotion:

- metric label → complete definition
- same label → same construct
- complete definition → construct validity
- raw component rates → safely pooled rate
- provider minutes → validated on-pitch exposure
- first/last observed action → minutes played
- descriptive metric → quality or tactical truth
- surface count → canonical event count
- calibrated score → causal confidence

`canonical_event_count=UNKNOWN`, `production_release=false`.

## Release status

Unit-test success is `SMOKE_PASS` only. This policy node does not inherit ACTIVE_MATCH evidence from an upstream head. Current #248 exact-head ACTIVE_MATCH revalidation remains an upstream dependency before downstream Foundation acceptance. PASS is not release.
