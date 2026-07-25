# Row Nucleus Inventory Lite V1

## Purpose

This node assembles same-role visible CSV/XML row candidates into deterministic row-nucleus candidates. It preserves source lineage, provider-row identifiers, field candidates, semantic-label candidates and cross-format support status.

A row nucleus is not a canonical event, physical-action truth, action bundle or validated identity.

## Inputs

- multiformat inventory
- CSV and XML reader audits
- field-path semantics
- provider label-value semantics
- cross-format reconciliation
- aggregate definition alignment
- provider metric dictionary
- candidate-only XML group registry
- `runtime/active_single_match/current`

## Non-duplication rules

- same timestamp does not merge rows;
- provider row ID is not event identity;
- same signature under different IDs becomes a collision candidate, not an auto-merge;
- exact duplicate file reflections remain lineage and are not recounted;
- CSV/XML support is same-provider conformance, not independent confirmation;
- team, player and goalkeeper roles are never auto-fused;
- XLSX aggregates do not create row occurrences.

## G01–G18 rollup

```text
G01 upstream_contract_integrity
G02 runtime_authority_and_sha_binding
G03 source_role_and_reference_exclusion
G04 field_path_semantics_readiness
G05 required_row_candidate_fields
G06 temporal_surface_integrity
G07 coordinate_surface_integrity
G08 provider_row_id_surface_integrity
G09 same_role_cross_format_reconciliation
G10 duplicate_reflection_lineage
G11 cross_id_signature_collision
G12 provider_label_semantic_readiness
G13 action_family_conflict_and_ambiguity
G14 identity_non_promotion_and_candidate_scope
G15 missingness_zero_and_null_preservation
G16 aggregate_definition_and_derivation_dependency
G17 degraded_mode_and_claim_boundary
G18 output_traceability_and_release_invariants
```

Each gate emits `PASS`, `REVIEW_REQUIRED`, `FAIL_CLOSED` or `NOT_APPLICABLE`. A rollup PASS is module evidence only. It never opens event admission, identity, metric, comparison, claim, sequence, phase, possession or tactical truth.

## Outputs

```text
row_nucleus_inventory_lite_v1.json
row_nucleus_inventory_lite_v1.txt
row_nucleus_inventory_analyst_audit_v1.txt
g01_g18_data_quality_rollup_v1.json
g01_g18_data_quality_rollup_v1.txt
```

Phone outputs must be written directly to `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`. Nested HPFA output paths are rejected.

## Claim boundary

```text
row_nucleus_count != canonical_event_count
canonical_event_count=UNKNOWN
validated_event_identity=false
validated_team_identity=false
validated_player_identity=false
validated_cross_role_equivalence=false
base_event_admission_allowed=false
metric_value_output_allowed=false
comparison_allowed=false
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
production_release=false
```

## Status

`SMOKE_CANDIDATE / ACTIVE_MATCH_EVIDENCE_REQUIRED / NOT_PRODUCTION`
