# HPFA Provider Label Value Semantics Lite V1

Status: `IMPLEMENTATION_UPDATED / SEMANTIC_GRAMMAR_V2 / ARTIFACT_REPLAY_PASS / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`

Product authority: `Hikmetpinarbas/hpfa`

Runtime authority: `runtime/active_single_match/current`

Linked issue: `#174`

## 1. Purpose

Convert visible SportsBase provider label values into deterministic, claim-safe semantic candidate records without treating provider rows, label volumes or parallel CSV/XML serializations as canonical football events.

```text
field-path candidates
+ CSV label/value volume surface
+ XML example-label support surface
+ XLSX aggregate-label surface
+ source role and SHA provenance
→ reviewed provider label grammar
→ action / context / relation / consequence / meta separation
→ unknown, token-fallback and conflict reports
```

This node is upstream of annotation atoms, CSV/XML fusion, row nuclei, match-local identity, aggregate reconciliation, possession, sequence, phase, metrics and analyst narrative.

## 2. What this node proves

It may prove only that a visible provider label has been assigned a deterministic semantic candidate decision under a versioned registry.

It does not prove:

- canonical event identity or count;
- physical action count;
- validated team or player identity;
- CSV/XML source independence;
- aggregate metric definitions;
- possession, sequence, phase, pattern, intent or tactical truth.

`canonical_event_count=UNKNOWN` is mandatory.

## 3. Upstream dependencies

Required artifacts:

1. Multiformat File Inventory Lite V1
2. CSV Surface Reader Lite V1
3. XLSX Surface Reader Lite V1
4. XML Surface Reader Lite V1
5. Field Path Classification from PR #172

Any upstream `FAIL_CLOSED`, hard block, unexpected production claim, canonical-event-count claim, invalid source SHA reference or unresolved required CSV/XML field path fails this node closed.

## 4. Source roles and donor policy

Current hpfa producers are product authority.

HP-Motor, HP-Engine, HP-PROJELERI, Drive, Dropbox and academic materials are `DONOR_SUPPORT / REFERENCE_ONLY` under `ADAPT_NOT_COPY`.

Accepted donor ideas:

- exact provider alias review;
- qualifier and relation separation;
- unknown preservation;
- downstream eligibility and claim ceilings;
- provenance-first pipeline records;
- correlation is not causation or event identity.

Rejected donor scope:

- donor module imports;
- broad ontology packages;
- a parallel orchestrator or semantic framework;
- probabilistic/LLM label guessing;
- tracking-dependent or tactical truth.

## 5. Semantic Grammar V2

### 5.1 Primary roles

Every provider label resolves to one primary role candidate:

```text
ACTION_ANCHOR
CONTEXT_INTERVAL
PARTICIPATION_INTERVAL
OPPONENT_ACTION_REFERENCE
RECEIVED_ACTION_REFERENCE
DERIVED_CONSEQUENCE_CANDIDATE
TERMINAL_OUTCOME_CANDIDATE
ADMINISTRATIVE_MARKER
PERIOD_OR_META
AGGREGATE_METRIC_LABEL
UNKNOWN_REVIEWED_PRESERVED
UNKNOWN_UNREVIEWED
```

A label assigned to context, participation, reference, derived, terminal, administrative or aggregate roles must not increase physical-action volume.

### 5.2 Action-family candidates

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
RESTART
GOALKEEPER_ACTION
TACKLE
DRIBBLE
CONTROL_ERROR
OFFSIDE
CARD
ERROR
UNKNOWN
```

These remain candidate families.

### 5.3 Additional semantic dimensions

```text
outcome_candidate
direction_candidate
distance_candidate
zone_candidate
context_candidate
relation_candidate
restart_type_candidate
shot_result_candidate
action_subtype_candidate
object_action_family_candidate
progression_candidate
key_action_candidate
terminal_outcome_candidate
card_type_candidate
downstream_eligibility
semantics_decision
review_status
```

Examples:

- `Goal kicks long (40+ m)` → `RESTART + GOAL_KICK + LONG`.
- `Fouls suffered` → `RECEIVED_ACTION_REFERENCE`, not an own foul action.
- `Opponent fouls` → `OPPONENT_ACTION_REFERENCE`, not an own foul action.
- goalkeeper-surface `Shots on target` → opponent shot reference faced by the goalkeeper.
- team/player-surface `Shots on target` → shot action candidate.
- `Shots saved` → goalkeeper save action with shot-object relation.
- `Successful cross and pass interception attempts` → interception action; `pass` and `cross` are intercepted object families.
- `Positional attacks with shots` → context interval with a shot-present terminal marker, not a shot action.

## 6. Deterministic decision order

```text
1. source-role-aware reviewed exact rule
2. reviewed context/participation prefix rule
3. explicit multi-anchor conflict
4. token fallback suggestion requiring review
5. reviewed meta alias
6. UNKNOWN_UNREVIEWED with raw-label preservation
```

Token fallback is never accepted as reviewed semantics and is downstream-blocked.

Probabilistic or language-model mapping is prohibited in this node.

## 7. Mapping statuses

```text
EXACT_REVIEWED_CANDIDATE
PREFIX_RULE_REVIEWED_CANDIDATE
XLSX_AGGREGATE_LABEL_CANDIDATE
TOKEN_FALLBACK_REVIEW_REQUIRED
CONFLICT_REVIEW_REQUIRED
EXACT_ALIAS_CANDIDATE
UNKNOWN_UNREVIEWED
BLOCKED
```

## 8. Required record fields

```text
record_id
source_format
source_role
source_relative_path
source_sha256
raw_label
normalized_label
surface_row_volume
evidence_scope
semantic_role_candidate
action_family_candidate
all compatible semantic dimensions
mapping_status
rule_id
registry_version
confidence_tier
downstream_eligibility
semantics_decision
review_status
provenance_refs
hard_block_hits
review_hits
validated_semantics
claim_ceiling
```

Raw labels and source provenance are retained verbatim.

## 9. Coverage accounting

The node reports separate volumes for:

```text
reviewed semantic decisions
token fallback requiring review
unknown unreviewed labels
conflicts
action-anchor candidates
context/participation surfaces
opponent/received/derived/terminal references
administrative/meta surfaces
```

`reviewed_semantic_surface_row_volume_ratio` measures registry decision coverage only.

It does not measure semantic truth, physical-action count, canonical-event count or independent multi-source confirmation.

Backward-compatible `mapped_*` fields are aliases for reviewed decision coverage and must be interpreted under the same boundary.

## 10. Cross-format behavior

- CSV and XML may be parallel serializations of one provider annotation candidate.
- Matching labels provide mapping-consistency support only.
- XML support in this version is limited to the reader's example-label surface; it is not a full XML label inventory.
- XLSX labels remain aggregate-only and cannot create event semantics.
- Cross-format agreement never validates canonical event identity.

## 11. Unknown and conflict policy

- `UNKNOWN_UNREVIEWED` preserves raw evidence and blocks required downstream semantics.
- token fallback remains a suggestion and triggers `REVIEW_REQUIRED`.
- multiple action-family token hits create `CONFLICT_REVIEW_REQUIRED`; the classifier does not select the first token.
- a deliberately reviewed non-action label may be retained as a safe context, reference, derived, terminal or administrative candidate rather than forced into an action family.

## 12. Duplicate and hash policy

- exact duplicate file reflections with the same source role and SHA are not recounted;
- lineage remains upstream responsibility;
- every reader file contributing label evidence must carry a valid SHA-256 reference;
- this node binds records to declared reader SHA references but does not re-hash runtime bytes;
- runtime-byte re-hashing remains a reconciliation/inventory hardening responsibility.

## 13. Outputs

Flat phone output only:

```text
provider_label_value_inventory_v1.json
provider_label_value_semantics_lite_v1.json
provider_label_unknown_report_v1.json
provider_label_conflict_report_v1.json
provider_label_value_semantics_analyst_audit_v1.txt
```

Allowed directories:

- `/sdcard/Download/HPFA`
- `/storage/emulated/0/Download/HPFA`

Nested output fails with `nested_phone_output_directory_rejected`.

## 14. Mandatory gates

Hard blocks include:

```text
input_root_missing
runtime_authority_mismatch
upstream_fail_closed
upstream_hard_block
required_field_path_semantics_missing
source_hash_missing_or_invalid
registry_version_mismatch
registry_duplicate_conflict
canonical_event_count_claimed
nested_phone_output_directory_rejected
```

Review conditions include:

```text
unknown_unreviewed_provider_label_values_present
token_fallback_semantics_review_required
conflicting_label_semantics_present
paired_csv_xml_label_conflict
upstream_not_pass
```

## 15. Tests

Mandatory tests cover:

- reviewed pass and qualifier mapping;
- incomplete/progressive pass outcomes;
- context and participation exclusion from action volume;
- period/meta variants;
- goal-kick restart semantics;
- goalkeeper/opponent shot direction;
- source-role-specific shot interpretation;
- save and compound interception semantics;
- foul relation direction;
- XLSX no-event guard;
- unknown preservation;
- token fallback review;
- multi-anchor conflict;
- coverage accounting;
- upstream fail-closed propagation;
- field-path gate;
- source SHA reference guard;
- duplicate-reflection no recount;
- canonical-event-count guard;
- exact runtime authority equality;
- suffix-only authority rejection;
- nested phone-output rejection;
- donor-scope guard;
- `test_no_sample_match_identity_leak`.

## 16. Evidence statuses

Atölye tests and an offline replay of previously captured ACTIVE_MATCH artifacts may produce:

```text
SMOKE_PASS
ARTIFACT_REPLAY_PASS
```

They do not replace execution against the exact current branch head and exact runtime authority.

`ACTIVE_MATCH_EVIDENCE_PASS` requires:

- exact repository, branch and current head;
- exact resolved runtime-authority path equality;
- execution against `runtime/active_single_match/current`;
- explicit `status=PASS`;
- no hard blocks or review hits;
- engineering and analyst evidence.

## 17. Claim boundary

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

## 18. Downstream gate

Only reviewed action candidates may enter SportsBase Annotation Atom Fusion.

Context, participation, opponent/received references, consequences, terminal outcomes and administrative/meta records remain separate evidence types. Unknown, conflict and token-fallback records cannot open action-family metrics, row nuclei, possession, sequence or tactical claims.

## 19. Current release state

```text
IMPLEMENTATION_UPDATED
SEMANTIC_GRAMMAR_V2
LOCAL_FOCUSED_TESTS_PASS
ACTIVE_MATCH_ARTIFACT_REPLAY_PASS
ACTIVE_MATCH_REVALIDATION_REQUIRED
NOT_PRODUCTION
NOT_MERGED
```
