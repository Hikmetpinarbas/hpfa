# Metric Definition Policy Lite V1

## Purpose

This node turns metric labels into versioned **definition candidates** with explicit
numerators, denominators, scope, context, calibration requirements, misuse warnings
and claim ceilings.

It does not compute metric values and does not validate provider equivalence.

## Position

`cross-format reconciliation → metric definition policy → aggregate-definition alignment → row/event eligibility`

The node is upstream of metric comparison and downstream of source provenance. It
does not authorize consequence, value, quality, possession or tactical claims.

## Inputs

- `configs/metrics/metric_registry_v1.json`
- `configs/metrics/metric_denominator_policy_v1.json`
- `configs/metrics/metric_context_schema_v1.json`
- `configs/metrics/metric_confidence_rules_v1.json`
- `configs/metrics/metric_misuse_warnings_v1.json`

All policy references and versions must resolve. Rate-like metrics require a declared
denominator and explicit zero/missing denominator behavior.

## Outputs

- normalized metric-definition candidates
- policy reference resolution
- comparison eligibility
- misuse warnings and claim ceilings
- fail-closed gaps

## Hard blocks

- missing or duplicate metric ID
- missing metric family, value type, unit, numerator, scope or observation window
- rate/percentage without a denominator definition
- unresolved denominator, context, confidence or misuse policy
- unhandled zero/missing denominator
- missing `does_not_measure` or `forbidden_claims`
- comparison requested without explicit aggregate-definition alignment
- policy-version mismatch

## Claim boundary

Allowed language:

- “metric-definition candidate”
- “provider-bound descriptive rate candidate”
- “comparison blocked until definition alignment”

Forbidden promotion:

- metric label → complete definition
- same label → same construct
- descriptive metric → quality or tactical truth
- surface count → canonical event count
- calibrated score → causal confidence

`canonical_event_count=UNKNOWN`, `production_release=false`.

## Release status

Unit-test success is `SMOKE_PASS` only. Fresh execution under
`runtime/active_single_match/current` and integration evidence are still required.
