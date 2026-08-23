# HPFA C2 Evidence Spine — Final Capability Snapshot V1

## Role

This record defines the controlled C2 Evidence Spine landing unit assembled on top of the merged C1 Foundation snapshot.

```text
C1 Row Nucleus
→ Evidence Atom
→ Match-Local Identity Candidates
→ Semantic Role / Action Bundle Candidates
→ Multi-Family Review Taxonomy
→ Cross-Role Relation Candidates
```

## Mainline base

```text
base_branch=main
base_head=f3dc7b44d6bb899033a605a690f6cc51fb0199a4
c1_foundation_landed=true
```

## Source final state

```text
source_final_state_pr=263
source_final_state_head=d75b5881d6fee0d9153978cd81b3e0c4ed4a9b5a
source_role=FINAL_STATE_EXTRACTION_SOURCE
historical_pr_merge_train=false
adapt_not_copy=true
```

The selected product delta is the current Evidence Spine state after #254 and before Trackable Action Trace. Historical commits are not replayed into main.

## Included capability families

1. Evidence Atom Inventory Lite
2. Match-Local Identity Candidates Lite
3. Semantic Role / Action Bundle Candidates Lite
4. Action Bundle Multi-Family Review Taxonomy Lite
5. Cross-Role Relation Candidate Resolver Lite

The selected root runtime adapters are included because they compose the current Foundation output into this Evidence Spine.

## Deliberate simplification

Historical stacked-branch workflows and five branch-specific Termux bootstrap scripts are not copied into the landing. They encoded obsolete `work/reconstruct-*` branch authority.

C2 instead uses:

```text
one exact-head integration CI gate
one operator-selected branch + exact-head Termux runtime bootstrap
```

The runtime bootstrap executes the top-level Cross-Role adapter, whose dependency chain invokes Taxonomy → Semantic Bundle → Match-Local Identity → Evidence Atom → Row Nucleus.

## Explicit exclusions

C2 does not land:

- Trackable Action Trace
- Trackable Action Consequence
- Visible Action Sequence
- Partial-Order hardening
- Context / episode intelligence
- Evidence reasoning / argument routing
- production release state

Those belong to later controlled landings.

## Claim boundary

C2 provides candidate structure and traceability, not event or tactical truth.

```text
identity_truth_admitted=false
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
physical_action_identity_truth=false
action_bundle_is_canonical_event=false
classification_is_event_truth=false
relation_candidate_is_event_truth=false
reflection_equivalence_truth=false
double_count_suppression_is_final=false
count_value_output_allowed=false
cross_role_fusion_allowed=false
event_instance_count=0
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Runtime evidence policy

The source #263 head has historical ACTIVE_MATCH evidence. That evidence demonstrates donor/source-head behaviour only.

It does **not** promote the integrated C2 head.

Fresh execution against:

```text
runtime/active_single_match/current
```

is required before an integrated head may receive ACTIVE_MATCH promotion.

## Acceptance sequence

```text
final-state extraction
→ exact-head C2 CI
→ review/thread audit
→ mergeability/current-main audit
→ controlled main landing
→ fresh ACTIVE_MATCH revalidation when operator runtime is available
```

## Initial status

`C2_EVIDENCE_SPINE_SNAPSHOT_ASSEMBLED / EXACT_HEAD_CI_PENDING / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`
