# Field Semantic Reader Lite — V1 to V2 Contract Delta Audit

Status: `DISCOVERY_PASS_PLAN_ONLY`

Repository authority: `Hikmetpinarbas/hpfa`

Main SHA audited: `6cc540399d56e52c021a3a02e3f72b416d393184`

Runtime authority: `runtime/active_single_match/current`

Canonical event count: `UNKNOWN`

## Purpose

Determine whether current-main `Field Semantic Reader Lite V1` already satisfies the directive target `Field Semantic Reader Lite V2`, and identify the minimum HPFA-native extension path without duplicating an existing executable producer.

## Source roles

- current `hpfa` source, schema and tests: `GITHUB_PRODUCT_REPO`
- Google Drive semantic-gate material: `DRIVE_DONOR_LIBRARY / DRIVE_GOVERNANCE`
- Dropbox search result: no matching semantic-reader artifact resolved in this pass
- donor materials do not define product truth

Policy: `ADAPT_NOT_COPY`

## Current-main evidence

### Field Semantic Reader V1

`hpfa/modules/core/field_semantic_reader_lite/src/field_semantic_reader.py`

Current producer provides:

- column normalization;
- simple type inference;
- exact normalized-name hint lookup;
- semantic-family candidate;
- required-module seed list;
- missingness seed fixed to `PRESENT` for observed columns;
- authority seed fixed to `SURFACE_ONLY`;
- downstream fail action `ALLOW_CANDIDATE` or `AUDIT_ONLY`;
- claim boundary `surface_candidate`;
- `canonical_event_count=UNKNOWN`;
- unknown fields preserved as unmapped candidates.

Classification: `EXECUTABLE_V1`

### V1 contract

`docs/contracts/field_semantic_reader_lite_v1.md`

Current state: placeholder only.

Classification: `CONTRACT_ONLY_PLACEHOLDER`

### V1 schema

`hpfa/modules/core/field_semantic_reader_lite/contracts/field_semantic_reader_lite_v1.schema.json`

The schema validates the outer envelope, but `field_semantic_records` is not governed by a typed item contract.

Classification: `PARTIAL_SCHEMA`

### Existing adjacent alias producer

`hpfa/modules/core/provider_alias_registry_binding_lite/src/provider_alias_registry_binding.py`

Current capability:

- deterministic alias normalization;
- provider + normalized alias lookup;
- candidate canonical-key resolution;
- alias reliability;
- duplicate provider-alias detection;
- unknown alias abstention;
- donor-support claim boundary;
- no runtime verification claim.

Classification: `EXECUTABLE_ADJACENT_PRODUCER / NOT_RUNTIME_PROVEN`

### Existing adjacent source-policy producer

`hpfa/modules/core/source_mapping_contract_lite/src/source_mapping_contract.py`

Current capability:

- source surface kind;
- source role;
- source format;
- source field and normalized field;
- canonical-field mapping candidate;
- per-source missing required fields;
- required-field policy;
- aggregate-support distinction;
- per-source decision;
- unmapped-field preservation;
- `canonical_event_count=UNKNOWN`;
- flat output writer through the existing phone-root validator.

Classification: `EXECUTABLE_ADJACENT_PRODUCER / NOT_RUNTIME_PROVEN`

### Existing tests

V1 tests verify basic semantic visibility, unknown-field preservation, mapping-coverage arithmetic, type inference, downstream seeds and sample-identity leak protection.

They do not establish V2 integration with alias and source-policy producers, typed V2 schema conformance, conflict routing, confidence rules or ACTIVE_MATCH evidence.

Classification: `UNIT_TESTS_V1_ONLY`

## V2 required field delta

| V2 field | Current-main source | Status | Required action |
|---|---|---|---|
| `field_name` | V1 `normalized_column` | RENAMED/PARTIAL | Preserve compatibility alias |
| `raw_field_name` | V1 `source_column` | RENAMED/PARTIAL | Preserve raw name exactly |
| `detected_aliases` | provider alias binding | ADJACENT_CAPABILITY | Consume alias evidence; do not build a second registry |
| `semantic_family` | V1 broad family | PARTIAL | Add versioned V1→V2 family map |
| `source_surface` | source mapping contract | ADJACENT_CAPABILITY | Consume source mapping output |
| `data_type_candidate` | V1 `inferred_type` | RENAMED | Preserve deterministic inference |
| `required_for_modules` | V1 present | PARTIAL | Normalize consumer IDs |
| `missingness_status` | source mapping missing-required evidence | ADJACENT_CAPABILITY | Consume source-level required-field result |
| `authority_status` | source role/mapping evidence | PARTIAL | Derive bounded status through adapter |
| `conflict_status` | source-conflict/alias evidence | PARTIAL | Reuse existing conflict producers where available |
| `downstream_fail_action` | V1 seed + source decision | PARTIAL | Map to directive fail-action vocabulary |
| `claim_boundary` | V1 scalar | INCOMPATIBLE_SHAPE | Add versioned compatibility representation |
| `decision_state_seed` | V1 present | PARTIAL | Map to normalized decision-state registry |
| `confidence` | alias reliability + rule reasons | PARTIAL | Produce rule-based candidate, not probability truth |

## Semantic-family delta

V1 broad categories are not equivalent to V2 exact categories. A compatibility map is required; silent reinterpretation is forbidden.

V1:

```text
event
actor
time
space
action
outcome
context
metric
support
unknown
```

V2 target:

```text
match_identity
team_or_side
player_identity
period
timestamp
event_order
action_type
outcome
qualifier
start_coordinate
end_coordinate
possession_identity
sequence_identity
score_state
restart_type
unknown
```

## Downstream fail-action delta

V1:

```text
ALLOW_CANDIDATE
AUDIT_ONLY
```

V2 target:

```text
ALLOW
WARN
DOWNGRADE_SPATIAL_ANALYSIS
DOWNGRADE_CONSEQUENCE_ANALYSIS
DOWNGRADE_PLAYER_LAYER
BLOCK_TEAM_SPLIT
BLOCK_TEMPORAL_ANALYSIS
BLOCK_SEQUENCE_ANALYSIS
BLOCK_CANONICALIZATION
BLOCK_SOURCE_CLAIM
AUDIT_ONLY
```

This is not a cosmetic enum expansion. The V2 adapter must combine:

- V1 observed-field classification;
- provider alias candidate evidence;
- source mapping required-field decisions;
- source-role and conflict evidence;
- normalized downstream policy.

## Confirmed architectural gaps

1. The V1 Markdown contract is a placeholder.
2. V1 does not consume the existing provider alias binding producer.
3. V1 does not consume the existing source mapping contract output.
4. V1 cannot represent absent required fields by itself because it iterates observed columns only.
5. V1 does not expose a typed conflict status.
6. V1 schema does not validate each field record.
7. V1 broad semantic families are not equivalent to V2 exact families.
8. V1 scalar claim boundary is not V2-compatible.
9. V1 has no explicit confidence reason trace.
10. No integrated V2 execution or ACTIVE_MATCH evidence exists.

## Existing capability to preserve and reuse

### Preserve from Field Semantic Reader V1

- deterministic normalization;
- deterministic type inference;
- unknown-field visibility;
- raw source-column preservation;
- audit-only routing;
- `canonical_event_count=UNKNOWN`;
- standard-library-only implementation;
- match-agnostic behavior;
- sample identity leak test.

### Reuse from provider alias binding

- `normalize_alias`;
- registry validation;
- candidate alias lookup;
- alias reliability;
- unknown-alias abstention;
- duplicate provider-alias guard.

### Reuse from source mapping contract

- `source_surface_kind`;
- `source_role`;
- `missing_required_fields`;
- `required_field_policy`;
- per-source decision;
- unmapped-field preservation;
- phone-output validation path.

Do not create parallel alias, required-field or source-policy registries.

## Better architecture

```text
Field Semantic Reader V1 output
+ provider_alias_registry_binding_lite_v1 output
+ source_mapping_contract_lite_v1 output
+ existing source-role/conflict evidence
-> Field Semantic Reader V2 Compatibility Adapter
-> typed V2 field semantic records
-> missing-field records
-> normalized downstream eligibility seeds
```

The adapter must remain narrow. It must not absorb:

- alias registry ownership;
- source mapping ownership;
- source independence adjudication;
- row semantic nucleus construction;
- canonical event production;
- sequence construction;
- metric computation;
- claim generation.

## Minimum migration path

1. Replace the placeholder V1 Markdown with an explicit compatibility contract.
2. Add a typed V2 schema for `field_semantic_records.items`.
3. Define an adapter input contract that consumes `provider_alias_registry_binding_lite_v1` output.
4. Define an adapter input contract that consumes `source_mapping_contract_lite_v1` output for source surface, missing required fields and per-source decisions.
5. Reuse existing source-role and conflict producers; add only missing bridge logic.
6. Add a V1→V2 compatibility map for names, semantic families and decision states.
7. Add module-specific fail-action routing.
8. Add deterministic confidence candidate with reason codes derived from existing producer evidence.
9. Extend unit, negative, integration and regression tests before runtime wiring.
10. Execute on ACTIVE_MATCH only after adapter and integration tests pass.

## Required tests before implementation acceptance

- `test_required_field_surface_policy_consumes_source_mapping_contract`
- `test_unknown_fields_are_preserved`
- `test_aliases_do_not_overwrite_raw_names`
- `test_alias_candidate_consumes_provider_alias_binding`
- `test_missing_timestamp_blocks_sequence`
- `test_missing_team_blocks_team_split`
- `test_missing_location_downgrades_spatial_analysis`
- `test_source_provenance_missing_blocks_independent_claim`
- `test_conflicting_aliases_require_review`
- `test_v1_compatibility_fields_preserved`
- `test_v2_schema_validates_each_field_record`
- `test_no_parallel_alias_registry_created`
- `test_no_parallel_source_policy_contract_created`
- `test_no_sample_match_identity_leak`

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| second semantic reader | duplicate product truth | compatibility adapter over V1 |
| second alias registry | divergent mappings | consume provider alias binding |
| second source-policy contract | conflicting decisions | consume source mapping contract |
| alias match overwrites raw name | provenance loss | immutable raw field |
| missing field silently absent | false downstream readiness | source mapping missing-required evidence |
| broad family promoted to exact family | semantic inflation | compatibility map + review state |
| confidence treated as probability | false precision | rule-based candidate + reasons |
| V1 consumers break | regression | compatibility fields and tests |

## Google Drive donor support

Drive semantic-gate material supports semantic eligibility before stronger evidence use, context preservation and separation of observed event surface from analytical claims. It does not define executable product behavior.

## Dropbox donor support

No matching semantic-reader artifact was resolved in this pass. This means `NO_MATCH_RESOLVED`, not proof of absence.

## Engineering evidence

- current-main SHA pinned: yes
- V1 reader inspected: yes
- V1 contract/schema/tests inspected: yes
- provider alias binding inspected: yes
- source mapping contract inspected: yes
- Google Drive donor search: yes
- Dropbox donor search: yes
- tests executed: no
- runtime output written: no
- ACTIVE_MATCH execution: no

## Analyst evidence

No match surface was analyzed.

Analyst value:

- provider aliases remain auditable candidates;
- missing team/time/location evidence can block or downgrade the correct analytical layer;
- unknown fields remain visible;
- source-policy decisions are reused consistently instead of redefined;
- downstream language remains claim-safe.

## Claim boundary

```text
canonical_event_count = UNKNOWN
field meaning = candidate until integrated checks pass
canonical event truth = false
sequence truth = false
tactical truth = false
production release = false
```

## Release readiness

```text
CURRENT V1 PRODUCER = EXECUTABLE_V1
ADJACENT ALIAS PRODUCER = EXECUTABLE / NOT_RUNTIME_PROVEN
ADJACENT SOURCE-MAPPING PRODUCER = EXECUTABLE / NOT_RUNTIME_PROVEN
TARGET V2 CAPABILITY = PARTIAL
V2 COMPATIBILITY ADAPTER = NOT_IMPLEMENTED
V2 TESTS = NOT_IMPLEMENTED
ACTIVE_MATCH_PROVEN = NO
RELEASE_STATUS = DISCOVERY_PASS_PLAN_ONLY
```

## Next product action

Create the smallest `Field Semantic Reader Lite V2 Compatibility Adapter Contract and Test Pack` that consumes the existing alias and source-mapping producers.

The first implementation branch must contain contract/schema/tests before source behavior changes. No new alias registry or source-policy producer is permitted without a separate proven gap.
