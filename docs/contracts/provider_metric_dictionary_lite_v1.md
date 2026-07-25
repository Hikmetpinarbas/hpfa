# Provider Metric Dictionary Lite V1

## Purpose

This control plane keeps provider labels, HPFA domain contracts, observed arithmetic
relations and unresolved proprietary definitions separate. It does not calculate
football performance or promote an aggregate label into event truth.

## First clearance batch

The first batch contains 25 runtime-critical pass, progression, final-third,
penalty-area, action, chance and challenge records.

Definitions may be:

- reviewed provider definitions;
- analyst-owned HPFA domain contracts;
- data-confirmed or data-inferred candidates;
- provider-definition-required records.

Only reviewed provider definitions and explicit HPFA domain contracts are eligible
to become later runtime contracts. Data fit alone is never provider-definition
evidence.

Definition identity is provider-specific:

```text
provider_id + provider_version + metric_id
```

The same semantic metric id may therefore have multiple provider definitions, while
the same provider/version definition key may not occur twice.

## Required separations

```text
forward != progressive
progressive != progressive_open
progressive_open reception != longer-horizon consequence
final_third_boundary_entry != final_third_access_established
chances_successful != chances_created
same label != same definition
observed arithmetic fit != provider definition
```

## Claim boundary

This node emits no metric value, comparison, quality, tactical truth or analyst
claim. It preserves:

```text
canonical_event_count=UNKNOWN
production_release=false
```
