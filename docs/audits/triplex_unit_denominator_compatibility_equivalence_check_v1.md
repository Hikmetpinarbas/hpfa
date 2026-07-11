# Triplex Unit and Denominator Compatibility Equivalence Check V1

## Scope

Bounded current-main and donor/reference audit for the Triplex Source Alignment Guard dependency:

```text
unit compatibility + denominator compatibility
```

Current-main baseline:

```text
6cc540399d56e52c021a3a02e3f72b416d393184
```

Truth boundary:

```text
canonical_event_count=UNKNOWN
ACTIVE_MATCH_PROVEN=false
production_release=false
```

## Current-main executable evidence

Repository search did not resolve an executable producer that jointly emits:

```text
measurement_unit
canonical_unit
dimensional_family
conversion_rule
denominator_type
denominator_value
denominator_scope
compatibility_decision
```

No current-main executable equivalent was resolved for cross-surface unit conversion, dimensional compatibility, denominator identity, or fail-closed fusion decisions.

## Adjacent evidence

Current-main ingest and mapping surfaces preserve visible values and selected field mappings, but they do not prove that two metrics share the same unit, denominator, or observation basis.

Examples of unresolved distinctions include:

```text
count vs percentage
per_match vs per_90
per_possession vs raw count
attempts vs successful actions
team denominator vs player denominator
minutes played vs match duration
meters vs normalized pitch coordinates
rate over full match vs rate over filtered window
```

## Donor/reference search

Dropbox search for an exact HPFA donor package covering unit, denominator, and observation-window compatibility returned no resolved match in this pass.

Google Drive returned HPFA theoretical material reinforcing that derived metrics require explicit validity boundaries and that sparse or mismatched windows invalidate some comparisons. This is theory/reference evidence only, not executable product evidence.

## Academic support boundary

Cross-domain literature consistently treats safe harmonization as conditional on:

```text
explicit canonical units
dimensional compatibility
validated conversion rules
stable semantic definitions
compatible observation/reference populations
metadata completeness
```

The literature also supports a fail-closed position when dimensional mismatch or missing metadata prevents valid conversion. Academic sources are used only to justify the validation pattern. They do not raise current-main capability status.

## Capability result

```text
unit parser                              = NOT_FOUND
canonical unit registry                  = NOT_FOUND
dimensional family classifier            = NOT_FOUND
validated conversion rule registry       = NOT_FOUND
denominator parser                        = NOT_FOUND
denominator semantic classifier           = NOT_FOUND
cross-surface compatibility adjudicator  = NOT_FOUND
typed downgrade/block decision            = NOT_FOUND
```

## Product classification

```text
capability_group = UNIT_DENOMINATOR_COMPATIBILITY
primary_status = NOT_FOUND
runtime_status = NOT_RUNTIME_PROVEN
ACTIVE_MATCH_PROVEN = NO
```

`NOT_FOUND` means no executable current-main equivalence was resolved in this bounded pass. It is not proof of absolute repository absence.

## Minimum future contract boundary

A later HPFA-native producer should require:

```text
metric_id
raw_unit
canonical_unit
dimensional_family
conversion_rule_id
raw_denominator
denominator_type
denominator_scope
observation_window_id
source_surface_id
compatibility_state
decision_reasons
```

Candidate decisions:

```text
ALLOW_DIRECT_COMPARISON
ALLOW_AFTER_CONVERSION
DOWNGRADE_DENOMINATOR_MISMATCH
BLOCK_DIMENSION_MISMATCH
BLOCK_UNKNOWN_UNIT
BLOCK_UNKNOWN_DENOMINATOR
BLOCK_WINDOW_MISMATCH
```

## Required deterministic tests

```text
same unit + same denominator -> allow
convertible unit + same denominator -> allow after conversion
incompatible dimensions -> block
same numeric value + different denominator -> downgrade/block
missing unit -> fail closed
missing denominator -> fail closed
per90 vs raw count -> block direct comparison
per possession vs per match -> block direct comparison
full match vs filtered window -> block direct comparison
no sample match identity leakage
```

## Tests

```text
tests_executed = false
tests_passed = NOT_CLAIMED
```

## Claim boundary

This audit does not establish metric equivalence, conversion correctness, football truth, ACTIVE_MATCH evidence, or production readiness.

## Release status

```text
DISCOVERY_PASS_PLAN_ONLY
```
