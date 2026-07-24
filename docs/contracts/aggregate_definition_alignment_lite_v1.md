# Aggregate Definition Alignment Lite V1

## Purpose

This node decides whether an observed XLSX aggregate label has a reviewed,
provider-version-bound definition candidate and the required row-level semantic
support. It does not compare values and does not treat count parity as definition
equivalence.

## Inputs

- `xlsx_surface_reader_lite_v1`
- `provider_label_value_semantics_lite_v1`
- `metric_definition_policy_lite_v1`
- a versioned aggregate-definition candidate registry

## Decisions

- `DEFINITION_ALIGNMENT_CANDIDATE`
- `REVIEW_REQUIRED_DEFINITION_ALIGNMENT`
- `BLOCKED_INVALID_DEFINITION`

An exact aggregate label is insufficient by itself. Provider definition evidence,
metric-policy readiness, required occurrence semantics, source role and derivation
dependency are evaluated separately.

## Claim boundary

The node never produces metric values, quality, aggregate equivalence, independent
confirmation, comparison permission, canonical event count or analyst claims.

```text
same label != same definition
count parity != definition equivalence
same-provider XLSX != independent confirmation
aggregate_definition_candidate != metric truth
canonical_event_count=UNKNOWN
production_release=false
```

The bundled SportsBase rule intentionally remains `REVIEW_REQUIRED` until a reviewed
provider definition and derivation lineage are available.
