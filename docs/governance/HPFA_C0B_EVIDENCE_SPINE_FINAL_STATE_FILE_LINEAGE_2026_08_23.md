# HPFA C0B — Evidence Spine Final-State File Lineage — 2026-08-23

Status: `C0B_EVIDENCE_SPINE_LINEAGE_CLOSED / FINAL_CAPABILITY_SNAPSHOT_EXTRACTION_READY / NOT_PRODUCTION / NOT_MERGED`

## Purpose

Fix the current final-state extraction lineage for the C2 Evidence Spine landing:

```text
Row Nucleus
→ Evidence Atom
→ Match-Local Identity
→ Semantic Role / Action Bundle
→ Multi-Family Taxonomy
→ Cross-Role Relation
```

This map prevents stale historical implementations from being replayed as product authority.

## Current coherent Evidence Spine extraction snapshot

Preferred snapshot:

```text
PR #263
head=d75b5881d6fee0d9153978cd81b3e0c4ed4a9b5a
branch=work/reconstruct-cross-role-relation-current-v1
```

Reason:
- #263 descends directly through the current #262→#261→#260→#259 chain;
- it inherits the current #254 Row Nucleus contract;
- all five current Evidence/Identity/Semantic/Relation migrations are present together;
- each node has current-head CI and ACTIVE_MATCH evidence on its own accepted head;
- the snapshot preserves candidate-only/claim-safe boundaries.

This is an extraction snapshot, not permission to merge PR #263 itself.

## Provenance anchors

```text
Evidence Atom
  PR #259
  head=a570b4429df98742b2ef041c4dec4848aa97e7af
  historical donor=#188

Match-Local Identity
  PR #260
  head=788f3aa114d4e296ec212d3fa7d95f4f3bc44584
  historical donor=#190

Semantic Role / Action Bundle
  PR #261
  head=5b549a9dd78ae481e0ec85200566ac204abf1cd8
  historical donor=#192

Multi-Family Review Taxonomy
  PR #262
  head=c7219069d8ba55b8537a6c86aa7e7585860167b2
  historical donor=#194

Cross-Role Relation Resolver
  PR #263
  head=d75b5881d6fee0d9153978cd81b3e0c4ed4a9b5a
  historical donor=#196
```

Historical donors remain `DONOR_SUPPORT / ADAPT_NOT_COPY`; they are not C2 landing blobs.

## E01 — Evidence Atom

Final extraction content:
`#263 snapshot`, with #259 current migration behaviour preserved.

Include:

```text
.github/workflows/evidence-atom-inventory-current-v1.yml
docs/contracts/evidence_atom_inventory_lite_v1.md
evidence_atom_inventory_lite.py
hpfa/modules/core/evidence_atom_inventory_lite/contract/evidence_atom_inventory_lite_v1.json
hpfa/modules/core/evidence_atom_inventory_lite/src/evidence_atom_inventory.py
hpfa/modules/core/evidence_atom_inventory_lite/tests/test_current_row_nucleus_migration.py
tools/bootstrap_termux_evidence_atom_inventory_current_v1.sh
```

Required retained behaviour:
- one current Row Nucleus candidate → one Evidence Atom candidate conservation;
- current `row_nucleus_candidate_id` is the identity seed;
- source provenance rebuilt from current runtime/source refs;
- dependent CSV/XML reflections add zero independent support vote;
- XLSX cannot create row/action identity;
- provider-row representation is preserved;
- source row index is provenance only;
- same-time ordering is not admitted;
- administrative/boundary atoms remain explicit and non-action eligible;
- semantic review is preserved rather than guessed away.

Claim boundary:

```text
event_instance_allowed=false
cross_role_fusion_allowed=false
physical_action_identity_truth=false
validated_event_identity=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

### PR #243 Evidence Atom change

Decision:

```text
DO_NOT_REPLAY_#243_EVIDENCE_ATOM_IMPLEMENTATION
CURRENT_#259_MIGRATION_WINS
```

Reason: #259 migrated the capability onto the current #254 Row Nucleus contract and current provider semantics. #243 remains useful historical collision-test provenance only.

## E02 — Match-Local Identity

Final extraction content:
`#263 snapshot`, with #260 current migration behaviour preserved.

Include:

```text
.github/workflows/match-local-identity-current-v1.yml
docs/contracts/match_local_identity_candidates_lite_v1.md
match_local_identity_candidates_lite.py
hpfa/modules/core/match_local_identity_candidates_lite/contract/match_local_identity_candidates_lite_v1.json
hpfa/modules/core/match_local_identity_candidates_lite/src/match_local_identity_candidates.py
hpfa/modules/core/match_local_identity_candidates_lite/tests/test_current_evidence_atom_migration.py
hpfa/modules/core/match_local_identity_candidates_lite/tests/test_current_team_surface_identity_bridge.py
tools/bootstrap_termux_match_local_identity_current_v1.sh
```

Required retained behaviour:
- identity remains match-local candidate only;
- TEAM subject binding may use exact visible subject evidence only;
- no fuzzy/global roster identity;
- administrative atoms may be identity-not-applicable;
- upstream Evidence Atom review state survives separately;
- bound Evidence Atom volume is not physical-action/event count.

Claim boundary:

```text
identity_truth_admitted=false
global_roster_identity_admitted=false
cross_match_identity_admitted=false
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## E03 — Semantic Role / Action Bundle

Final extraction content:
`#263 snapshot`, preserving #261 current migration behaviour.

Include:

```text
.github/workflows/semantic-role-action-bundle-current-v1.yml
semantic_role_action_bundle_candidates_lite.py
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/contract/semantic_role_action_bundle_candidates_lite_v1.json
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/src/semantic_role_action_bundle_candidates.py
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_semantic_role_action_bundle_current_v1.sh
```

Required retained behaviour:
- structured source lineage is authority;
- historical positional path/SHA assumptions are rejected;
- PLAYER / TEAM / GOALKEEPER remain separate semantic routes;
- TEAM reflections are not fused into PLAYER/GK action identity;
- administrative atoms remain ADMINISTRATIVE_ROUTE and non-bundle eligible;
- semantic-review action anchors remain REVIEW_REQUIRED_ROUTE;
- same timestamp/source-row order creates no temporal order;
- cross-role exact overlap is relation candidate only.

Claim boundary:

```text
action_bundle_is_canonical_event=false
physical_action_identity_truth=false
event_instance_count=0
cross_role_fusion_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## E04 — Multi-Family Review Taxonomy

Final extraction content:
`#263 snapshot`, preserving #262 current migration behaviour.

Include:

```text
.github/workflows/action-bundle-multi-family-review-taxonomy-current-v1.yml
action_bundle_multi_family_review_taxonomy_current_v1.py
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/contract/action_bundle_multi_family_review_taxonomy_lite_v1.json
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/src/action_bundle_multi_family_review_taxonomy.py
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_action_bundle_multi_family_review_taxonomy_current_v1.sh
```

Required retained behaviour:
- registered exact family sets may become candidate classifications only;
- hierarchical subtype/restart coupling does not create event fusion;
- compound/same-time/complex/unregistered family sets remain REVIEW_REQUIRED;
- timestamp equality and source-row order do not establish football ordering truth;
- every source review bundle must be covered exactly once.

Claim boundary:

```text
classification_is_event_truth=false
family_parent_is_validated_action=false
subtype_is_validated_action=false
restart_coupling_is_event_fusion=false
same_time_order_truth_admitted=false
source_row_order_is_temporal_truth=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## E05 — Cross-Role Relation Resolver

Final extraction content:
`#263 @ d75b5881d6fee0d9153978cd81b3e0c4ed4a9b5a`.

Include:

```text
.github/workflows/cross-role-relation-current-v1.yml
cross_role_relation_candidate_resolver_current_v1.py
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/contract/cross_role_relation_candidate_resolver_lite_v1.json
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/src/cross_role_relation_candidate_resolver.py
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/tests/test_current_contract_migration.py
tools/bootstrap_termux_cross_role_relation_current_v1.sh
```

Required retained behaviour:
- relation requires exact compatible bundle evidence;
- PLAYER+TEAM and GOALKEEPER+TEAM remain role-separated relation candidates;
- taxonomy unresolved context stays REVIEW_REQUIRED;
- relation-bundle reuse is forbidden;
- TEAM reflection is not deleted;
- double-count suppression remains candidate-only until later admission;
- no count value is emitted;
- same-time-only link is not allowed;
- source row order is not temporal truth.

Claim boundary:

```text
relation_candidate_is_event_truth=false
reflection_equivalence_truth=false
double_count_suppression_is_final=false
count_value_output_allowed=false
cross_role_fusion_allowed=false
event_instance_count=0
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Cross-slice decision — PR #228 G07 coordinate exemption

C1 deliberately did not fold #228 into current Row Nucleus because that implementation expects explicit semantic-role/downstream-eligibility evidence not available at the Row Nucleus layer itself.

C2 now supplies explicit semantic-role/admin routing downstream. Decision remains:

```text
DO_NOT_MUTATE_ROW_NUCLEUS_DURING_C2_EXTRACTION
PRESERVE_#228_AS_DONOR_BEHAVIOUR_FOR_LATER_GATE_OR_ADAPTER_REVIEW
```

If coordinate eligibility later needs an administrative exemption, implement it where the current semantic-role evidence is actually available, or through a thin downstream adapter. Do not back-inject semantic truth into Row Nucleus.

## Current C2 extraction rule

The C2 landing must be extracted as one final Evidence Spine capability snapshot from the current #263 tree, not as five historical merges.

Before landing:

1. compare each selected file blob against the #263 snapshot;
2. retain current contracts/tests/workflows only;
3. exclude stale historical implementations and positional lineage assumptions;
4. preserve `REVIEW_REQUIRED` continuity;
5. preserve all no-truth/no-count locks;
6. retain operator wrapper rule: interactive parent wrapper must not terminate the operator shell;
7. after C2 assembly, run current-head CI and fresh applicable ACTIVE_MATCH on the coherent integrated head.

## C2 analyst evidence boundary

Allowed analyst meaning:
- visible Row Nucleus evidence is conserved into Evidence Atoms;
- match-local identity candidates may bind where exact visible evidence supports them;
- semantic/action-family candidates may be grouped without creating physical action truth;
- unresolved multi-family combinations remain visible review evidence;
- exact cross-role relationships may be surfaced as relation candidates.

Not admitted:

```text
canonical event truth
physical action truth
validated global identity
possession truth
sequence truth
phase truth
tactical truth
coach intention
dominance
```

## C0B progress

```text
C0A authority + open-PR classification = CLOSED
C0B Foundation final-state file lineage = CLOSED
C0B Evidence Spine final-state file lineage = CLOSED
C0B Reconstruction + Intelligence final-state file lineage = NEXT
```

No merge, auto-merge, release or production binding is authorized by this record.
