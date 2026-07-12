# Triplex Source Alignment Adapter Lite V1

Status: `IMPLEMENTED_NOT_RUNTIME_PROVEN`

## Purpose

Adapt existing HPFA source-mapping and source-conflict outputs into one narrow, fail-closed source-alignment decision without creating a parallel conflict registry.

## Source role

- Product source: current `Hikmetpinarbas/hpfa` main and this branch.
- Required upstream producers:
  - `source_mapping_contract_lite_v1`
  - `source_conflict_registry_lite_v1`
- Donor rule: `ADAPT_NOT_COPY`.
- Open PRs and donor repositories do not define current-main runtime truth.

## Inputs

The adapter reads, when present:

- `source_mapping_contract_v1.json` or `source_mapping_audit_v1.json`
- `source_conflict_registry_lite_v1.json`

Event-like source records may expose:

- `upstream_origin_id`
- `independence_group`
- `lineage_role`
- `canonical_event_identity_compatible`
- `time_window_state`
- `unit_compatibility`
- `scope_compatibility`
- `denominator_compatibility`

## Decisions

The adapter detects:

- missing upstream-origin lineage;
- missing independence-group assignment;
- multiple files derived from the same upstream origin;
- dependent source groups incorrectly presented as independent evidence;
- derived outputs re-entering as primary sources;
- canonical-event identity incompatibility;
- ambiguous time windows;
- incompatible or unresolved unit, scope and denominator states;
- inherited conflicts from the existing source-conflict registry.

## Claim boundary

A `PASS` means only that the visible inputs satisfy this adapter's deterministic alignment checks and the inherited conflict count is zero.

A `PASS` does **not** establish:

- canonical event truth;
- complete event-stream truth;
- deduplicated event count;
- tactical truth;
- production readiness;
- ACTIVE_MATCH runtime proof;
- release eligibility.

The adapter always keeps:

- `canonical_event_count=UNKNOWN`
- `production_binding_allowed=false`

When alignment passes, `claim_capacity=SOURCE_ALIGNMENT_ONLY`.

## Output policy

Outputs are flat files under the existing validated phone output root:

- `triplex_source_alignment_adapter_lite_v1.json`
- `triplex_source_alignment_adapter_lite_v1.txt`

Nested phone-output directories remain rejected by the existing spine validator.

## Test requirement

Deterministic tests cover:

- missing lineage fields;
- duplicate upstream origin;
- dependent source groups;
- derived-output fail-closed behavior;
- compatible independent sources;
- inherited conflict blocking;
- flat phone outputs;
- nested output rejection;
- sample-match identity leak prevention.

## Runtime and release status

No ACTIVE_MATCH execution is claimed by this contract. Test presence is engineering evidence only until tests are executed successfully. PASS must not be equated with release.
