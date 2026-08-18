# Row Nucleus Content Role Bridge Lite V1

## Purpose

Bind `content_source_role_resolver_lite_v1` source-role candidates into row-nucleus grouping before any downstream spatial/statistical use.

```text
content-resolved CSV/XML source roles
-> representation-preserving provider row IDs
-> same-role serialization lineage
-> role-resolved row-nucleus candidates
```

## Admission

- content source-role resolver must be `PASS`;
- every CSV/TSV/XML surface used by the bridge must have `ROLE_CANDIDATE_ADMITTED`;
- filename support never opens admission;
- PLAYER, TEAM and GOALKEEPER remain separate routes;
- CSV/XML reflections are not independent votes;
- XLSX remains excluded from row identity.

## Required output invariants

```text
filename_role_used_for_nucleus_grouping=false
row_nucleus_is_canonical_event=false
physical_action_identity_truth=false
validated_event_identity=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Failure / review behavior

- unresolved content role -> `REVIEW_REQUIRED`, no role-resolved nuclei published;
- resolver hard block -> `FAIL_CLOSED`;
- runtime drift between resolved role map and visible row surfaces -> `FAIL_CLOSED`;
- serialization discrepancy remains `REVIEW_REQUIRED` and propagates downstream.

## Claim boundary

The bridge produces source-role-corrected row-nucleus candidates only. It does not create physical actions, canonical events, validated player/team identity, possession, sequence, phase, progression, tactical or causal truth.
