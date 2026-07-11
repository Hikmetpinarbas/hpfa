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

### Contract

`docs/contracts/field_semantic_reader_lite_v1.md`

Current state: placeholder only.

Observed content:

```text
# Field Semantic Reader Lite V1

PLACEHOLDER
```

Classification: `CONTRACT_ONLY_PLACEHOLDER`

### Executable producer

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

### Schema

`hpfa/modules/core/field_semantic_reader_lite/contracts/field_semantic_reader_lite_v1.schema.json`

Current schema validates only the outer output envelope. `field_semantic_records` is an untyped array and the downstream eligibility definition is not attached as an item contract.

Classification: `PARTIAL_SCHEMA`

### Tests

Current tests verify:

- every visible column gets a semantic status;
- unknown columns remain visible;
- mapping coverage arithmetic;
- canonical event count remains unknown;
- basic type inference;
- normalization;
- known/unknown downstream seeds;
- sample identity leak guard.

Current tests do not establish:

- alias preservation;
- provider-agnostic alias resolution;
- source-surface provenance;
- authority conflict handling;
- actual missing-required-field detection;
- module-specific downgrade/block actions;
- confidence calculation;
- V2 schema conformance;
- ACTIVE_MATCH execution.

Classification: `UNIT_TESTS_V1_ONLY`

## V2 required field delta

Directive target record:

```json
{
  "field_name": "",
  "raw_field_name": "",
  "detected_aliases": [],
  "semantic_family": "",
  "source_surface": "",
  "data_type_candidate": "",
  "required_for_modules": [],
  "missingness_status": "",
  "authority_status": "",
  "conflict_status": "",
  "downstream_fail_action": "",
  "claim_boundary": [],
  "decision_state_seed": "",
  "confidence": null
}
```

| V2 field | V1 equivalent | Status | Required action |
|---|---|---|---|
| `field_name` | `normalized_column` | RENAMED/PARTIAL | Preserve compatibility alias or versioned adapter |
| `raw_field_name` | `source_column` | RENAMED/PARTIAL | Preserve raw name exactly |
| `detected_aliases` | none | NOT_FOUND | Add alias evidence without replacing raw name |
| `semantic_family` | present | PARTIAL | Replace broad family vocabulary with V2 canonical families |
| `source_surface` | evidence ref only | PARTIAL | Add explicit source-surface identity/provenance |
| `data_type_candidate` | `inferred_type` | RENAMED | Keep deterministic inference and expose candidate naming |
| `required_for_modules` | present | PARTIAL | Normalize module IDs and consumer contract |
| `missingness_status` | fixed `PRESENT` | INSUFFICIENT | Add required-field absence audit at surface level |
| `authority_status` | fixed `SURFACE_ONLY` | INSUFFICIENT | Route from source-role/admission evidence |
| `conflict_status` | none | NOT_FOUND | Add cross-surface/alias conflict state |
| `downstream_fail_action` | present | INSUFFICIENT | Replace `ALLOW_CANDIDATE` with directive action vocabulary |
| `claim_boundary` | scalar string | INCOMPATIBLE_SHAPE | Version as array or explicit structured boundary |
| `decision_state_seed` | present | PARTIAL | Map to Module Decision State Registry vocabulary |
| `confidence` | none | NOT_FOUND | Add explainable rule-based confidence candidate |

## Semantic-family delta

### V1 families

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

### V2 required families

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

Decision:

V1 broad categories must not be silently reinterpreted as V2 exact categories. A versioned semantic-family resolver or compatibility map is required.

## Downstream fail-action delta

### V1

```text
ALLOW_CANDIDATE
AUDIT_ONLY
```

### V2

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

Decision:

This is not a cosmetic enum expansion. V2 requires surface-level required-field policy and downstream consumer effects. Missing columns cannot be detected by iterating only observed columns; a required-field expectation contract is necessary.

## Confirmed architectural gaps

1. The Markdown V1 contract is a placeholder and cannot govern the executable producer.
2. V1 uses exact normalized-name lookup rather than provider-agnostic alias evidence.
3. V1 does not receive source-surface metadata as an explicit input.
4. V1 cannot distinguish missing required fields because it only emits records for observed columns.
5. V1 does not expose conflict status.
6. V1 schema does not validate individual field records.
7. V1 broad semantic families are not equivalent to V2 exact canonical families.
8. V1 uses a scalar claim boundary while V2 requires an explicit boundary collection.
9. V1 has no confidence rule or explanation trace.
10. V1 is not ACTIVE_MATCH proven.

## Existing capability to preserve

Do not create a second unrelated reader. Preserve and extend:

- deterministic column normalization;
- deterministic type inference;
- unknown-field visibility;
- raw source-column preservation;
- audit-only routing for unresolved fields;
- `canonical_event_count=UNKNOWN`;
- standard-library-only implementation;
- match-agnostic behavior;
- `test_no_sample_match_identity_leak`.

## Google Drive donor support

Drive search resolved semantic-gate material describing event coding, semantic event gates and the event→context→pattern→inference chain. This supports:

- explicit semantic eligibility before stronger evidence use;
- preservation of context and source meaning;
- separation of observed event surface from analytical claim.

It does not provide runtime truth or justify copying an implementation.

## Dropbox donor support

Searches for `field semantic reader mapping eligibility semantic gate` and `semantic gate` returned no matching active file in this pass.

Interpretation: `NO_MATCH_RESOLVED`, not proof of absolute absence.

## Better architecture

Recommended architecture:

```text
surface descriptor
+ observed columns
+ provider-agnostic alias registry
+ required-field policy
+ source-role/admission evidence
-> Field Semantic Reader V2
-> field semantic records
-> surface missing-field records
-> downstream eligibility seeds
```

The reader should remain a semantic router. It must not absorb:

- row semantic nucleus construction;
- canonical event production;
- source independence adjudication;
- sequence construction;
- metric computation;
- claim generation.

## Minimum migration path

1. Replace placeholder V1 Markdown with a real compatibility contract.
2. Add a versioned V2 schema with typed `field_semantic_records.items`.
3. Introduce a small provider-agnostic alias registry input.
4. Introduce explicit `source_surface` and source-role/admission inputs.
5. Add a required-field expectation contract so absent fields produce auditable missing-field records.
6. Add V1→V2 compatibility mapping for names and semantic families.
7. Add module-specific fail-action routing.
8. Add deterministic confidence candidate with reason codes.
9. Extend tests before modifying runtime wiring.
10. Execute on ACTIVE_MATCH only after contract and integration tests pass.

## Required tests before implementation acceptance

- `test_required_field_surface_policy`
- `test_unknown_fields_are_preserved`
- `test_aliases_do_not_overwrite_raw_names`
- `test_missing_timestamp_blocks_sequence`
- `test_missing_team_blocks_team_split`
- `test_missing_location_downgrades_spatial_analysis`
- `test_source_provenance_missing_blocks_independent_claim`
- `test_field_reader_is_provider_agnostic`
- `test_v1_compatibility_fields_preserved`
- `test_v2_schema_validates_each_field_record`
- `test_conflicting_aliases_require_review`
- `test_no_sample_match_identity_leak`

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| V2 implemented as a second reader | duplicate product truth | extend current producer behind versioned contract |
| alias match overwrites raw name | provenance loss | immutable `raw_field_name` |
| missing field silently absent | false downstream readiness | explicit missing-field records |
| broad V1 family promoted to exact V2 family | semantic inflation | compatibility map + review state |
| confidence treated as probability truth | false precision | rule-based candidate + reason codes |
| source role inferred from filename alone | authority leakage | consume admission/source-role evidence |
| V1 consumers break | compatibility regression | adapter and regression tests |

## Engineering evidence

- current-main SHA pinned: yes
- V1 contract inspected: yes
- V1 source inspected: yes
- V1 schema inspected: yes
- V1 tests inspected: yes
- Google Drive donor search performed: yes
- Dropbox donor search performed: yes
- tests executed: no
- output written to runtime: no
- ACTIVE_MATCH execution: no

## Analyst evidence

No match surface was analyzed.

Analyst value of this audit:

- prevents provider column names from being mistaken for stable football meaning;
- makes missing temporal, team, player or coordinate evidence visible before downstream interpretation;
- prevents spatial, sequence and consequence language from surviving when required evidence is absent;
- preserves unknown fields for later audit rather than silently dropping them.

## Claim boundary

```text
canonical_event_count = UNKNOWN
field meaning = candidate until contract and authority checks pass
canonical event truth = false
sequence truth = false
tactical truth = false
production release = false
```

## Release readiness

```text
CURRENT V1 PRODUCER = EXECUTABLE_V1
TARGET V2 CAPABILITY = PARTIAL
V2 CONTRACT = NOT_IMPLEMENTED
V2 TESTS = NOT_IMPLEMENTED
ACTIVE_MATCH_PROVEN = NO
RELEASE_STATUS = DISCOVERY_PASS_PLAN_ONLY
```

## Next product action

Create `Field Semantic Reader Lite V2 Compatibility and Contract Pack` on a new implementation branch only after PR #152 inventory evidence is accepted.

The first implementation commit must contain contract/schema/tests before source behavior changes.
