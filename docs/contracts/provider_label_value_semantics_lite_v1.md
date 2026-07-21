# HPFA Provider Label Value Semantics Lite V1

Status: `SPEC_ONLY / IMPLEMENTATION_START_AUTHORIZED / ACTIVE_MATCH_EVIDENCE_REQUIRED / NOT_PRODUCTION`

Product authority: `Hikmetpinarbas/hpfa`

Runtime authority: `runtime/active_single_match/current`

Linked issue: `#174`

## 1. Purpose

Convert visible SportsBase provider label values into claim-safe semantic candidate records without treating surface rows as canonical events.

This module is downstream of field-name/path classification and upstream of annotation fusion, row-nucleus construction, metric admission, possession, sequence and phase logic.

```text
field-path candidates
+ raw CSV/XML provider label values
+ provider/source provenance
→ provider label-value inventory
→ deterministic candidate semantic mapping
→ unknown/conflict reports
```

## 2. Non-goals

The module does not establish:

- canonical event identity or count;
- validated team/player identity;
- validated cross-format equivalence;
- XLSX event-level semantics;
- aggregate metric definitions;
- possession, sequence, phase, pattern or tactical truth;
- coach intention, dominance, pitch control, off-ball or body-orientation truth.

`canonical_event_count=UNKNOWN` is mandatory.

## 3. Upstream dependencies

Required upstream artifacts:

1. Multiformat File Inventory Lite V1
2. CSV Surface Reader Lite V1
3. XLSX Surface Reader Lite V1
4. XML Surface Reader Lite V1
5. Field Path Classification output from PR #172

Any upstream hard block fails this module closed.

## 4. Source roles

Current hpfa producers are product authority.

The following are `DONOR_SUPPORT / REFERENCE_ONLY` under `ADAPT_NOT_COPY`:

- HP-Motor SportsBase XML parser and no-drop/schema-drift patterns;
- HP-Engine registry and semantic-gate patterns;
- HP-PROJELERI conflict/gate-policy patterns;
- Dropbox provider normalization and canonical action-family maps;
- Google Drive action vocabulary, provider dictionary and crosswalk candidates;
- verified local Termux fusion donor pack.

No donor may override ACTIVE_MATCH evidence.

## 4.1 Minimal donor adaptation rule

Donor material supplies a capability hypothesis, failure mode, boundary or test idea. It is not a package to import into the product repository.

Mandatory rules:

- start from the current hpfa producer and current executable blocker;
- adapt only the smallest donor idea that closes that blocker or creates measurable analyst value;
- write HPFA-native code and contracts; do not copy donor modules, folder trees or framework structure;
- do not import donor inventories, roadmaps, research packs, ontology bundles or broad registries into product code unless a current runtime contract requires a specific record;
- do not create a second orchestrator, parallel semantic framework, duplicate registry or speculative abstraction;
- one accepted capability must have one narrow contract, one deterministic responsibility and explicit outputs;
- reject ideas that add more dependencies, state, branches or configuration than the current problem requires;
- reject code added only because it may be useful later;
- preserve donor attribution in engineering notes, not as runtime authority;
- the first implementation must be the smallest portable executable slice that can be tested on ACTIVE_MATCH.

A donor idea is admissible only when all answers are explicit:

```text
current_product_problem
current_hpfa_producer
accepted_donor_idea
rejected_donor_scope
target_contract
runtime_input
runtime_output
claim_boundary
focused_test
ACTIVE_MATCH_need
```

Failure to justify these fields means `DONOR_IDEA_REJECTED_NOT_CURRENTLY_NEEDED`.

## 5. Required semantic roles

Every provider label value resolves to exactly one primary semantic role candidate:

```text
ACTION_ANCHOR
OUTCOME_QUALIFIER
DIRECTION_QUALIFIER
DISTANCE_QUALIFIER
ZONE_QUALIFIER
CONTEXT_INTERVAL
PARTICIPATION_INTERVAL
PERIOD_OR_META
AGGREGATE_METRIC_LABEL
UNKNOWN_PRESERVED
```

A record may carry additional compatible qualifier candidates, but it may not silently promote itself to a canonical event.

## 6. Initial action-family candidates

```text
PASS
CARRY
SHOT
RECOVERY
TURNOVER
CLEARANCE
DUEL
FOUL
INTERCEPTION
BLOCK
CROSS
SET_PIECE
GOALKEEPER_ACTION
UNKNOWN
```

These are candidate families, not validated football truth.

## 7. Deterministic mapping order

```text
1. exact normalized registry match
2. approved exact alias match
3. approved compositional anchor + qualifier rule
4. explicit conflict candidate
5. UNKNOWN_PRESERVED
```

Probabilistic or language-model mapping is not allowed in Lite V1.

## 8. Required record fields

```text
record_id
source_format
source_role
source_relative_path
source_sha256
provider_row_id_candidate
raw_label
normalized_label
semantic_role_candidate
action_family_candidate
outcome_candidate
direction_candidate
distance_candidate
zone_candidate
context_candidate
mapping_status
rule_id
registry_version
confidence_tier
provenance_refs
hard_block_hits
review_hits
claim_ceiling
```

Raw labels must be preserved verbatim.

## 9. Mapping statuses

```text
EXACT_REGISTRY_CANDIDATE
EXACT_ALIAS_CANDIDATE
COMPOSITIONAL_RULE_CANDIDATE
CONFLICT_REVIEW_REQUIRED
UNKNOWN_PRESERVED
BLOCKED
```

## 10. Cross-format behavior

- CSV and XML matching rows are parallel serializations of one provider annotation candidate, not two event votes.
- Paired raw labels may support mapping consistency evidence.
- Cross-format agreement does not validate canonical event identity.
- XML label bundles must remain intact in provenance.
- XLSX labels remain aggregate metric-label candidates and cannot create event-level action anchors in this module.

## 11. Unknown and conflict policy

Unknown provider labels are preserved with raw provenance and block any downstream metric or action-bundle logic that requires resolved action semantics.

Conflicting exact mappings produce `CONFLICT_REVIEW_REQUIRED`; the module must not choose silently.

## 12. Duplicate policy

Exact duplicate file reflections are retained in lineage but not recounted as independent label volume.

Upstream inventory duplicate reflection count and local payload reflection count must be reported separately.

## 13. Outputs

All phone-visible outputs must be flat under:

- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Required files:

```text
provider_label_value_inventory_v1.json
provider_label_value_semantics_lite_v1.json
provider_label_unknown_report_v1.json
provider_label_conflict_report_v1.json
provider_label_value_semantics_analyst_audit_v1.txt
```

Nested output must fail with `nested_phone_output_directory_rejected`.

## 14. Hard blocks

```text
input_root_missing
runtime_authority_mismatch
runtime_authority_path_invalid
upstream_failed_closed
upstream_hard_block_present
required_field_path_semantics_missing
source_hash_mismatch
registry_unreadable
registry_duplicate_conflict
canonical_event_count_claimed
nested_phone_output_directory_rejected
```

## 15. Review conditions

```text
unknown_provider_label_values_present
conflicting_alias_candidates_present
paired_csv_xml_label_mismatch
unsupported_compositional_rule
aggregate_label_role_ambiguous
```

Unknown labels may produce `REVIEW_REQUIRED`; they must never be guessed.

## 16. Mandatory tests

- exact pass/action mapping;
- outcome qualifier separation;
- direction and distance qualifier separation;
- context and participation interval separation;
- period/meta exclusion from action volume;
- unknown label preservation and downstream block;
- raw label and provenance preservation;
- CSV/XML paired-label consistency;
- XLSX no-event-semantics guard;
- conflicting alias review;
- duplicate reflection no recount;
- source hash binding;
- upstream hard-block propagation;
- canonical event count guard;
- nested phone output rejection;
- donor scope rejection for non-current capability;
- no parallel framework or duplicate registry;
- `test_no_sample_match_identity_leak`.

## 17. ACTIVE_MATCH evidence rule

Atölye tests may produce only `SMOKE_PASS`.

`ACTIVE_MATCH_EVIDENCE_PASS` requires:

- exact repository, branch and head verification;
- exact runtime authority path equality;
- execution against `runtime/active_single_match/current`;
- engineering evidence;
- analyst evidence;
- no hard blocks;
- explicit status `PASS`.

## 18. Claim boundary

```text
canonical_event_count=UNKNOWN
validated_provider_semantics=false
validated_event_identity=false
validated_team_identity=false
validated_player_identity=false
validated_cross_format_equivalence=false
aggregate_definition_truth=false
sequence_truth=false
phase_truth=false
tactical_truth=false
production_release=false
```

## 19. Downstream gate

Only resolved label candidates may feed SportsBase Annotation Atom Fusion. Unknown/conflicting labels remain preserved but must not open action-family metrics, row nuclei, possession, sequence or tactical claims.

## 20. Release status

```text
SPEC_ONLY
IMPLEMENTATION_START_AUTHORIZED
ACTIVE_MATCH_EVIDENCE_REQUIRED
NOT_PRODUCTION
NOT_MERGED
```
