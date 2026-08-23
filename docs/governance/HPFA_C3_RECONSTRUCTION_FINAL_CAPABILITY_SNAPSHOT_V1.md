# HPFA C3 Reconstruction — Final Capability Snapshot V1

## Role

C3 lands the current reconstruction surface on top of merged C1 Foundation + C2 Evidence Spine.

```text
C2 Cross-Role Relation Candidates
→ Trackable Action Trace Candidates
→ Trackable Action Consequence Candidates
→ Visible Action Sequence Candidates
→ Partial-Order Hardening
```

Partial-Order is not a fourth event/action producer. It is the current Visible Sequence contract/regression boundary that prevents unsupported total ordering.

## Mainline base

```text
base_branch=main
base_head=871cd3c4948dd72b80aaa2983268811d7a22b39b
c1_foundation_landed=true
c2_evidence_spine_landed=true
```

## Source final state

```text
source_final_state_pr=267
source_final_state_head=a8b5d84ff40982b4ed20ddd673a93b0c87ffd55f
source_role=FINAL_STATE_EXTRACTION_SOURCE
historical_pr_merge_train=false
adapt_not_copy=true
```

The selected delta is the final #263→#267 Reconstruction surface. Historical stacked commits are not replayed into main.

## Included product capabilities

1. Trackable Action Trace Candidates Lite
2. Trackable Action Consequence Candidates Lite
3. Visible Action Sequence Candidates Lite
4. Visible Sequence partial-order contract + same-time regressions

## Partial-order invariants

Allowed audit states:

```text
BEFORE_CONFIRMED
AFTER_CONFIRMED
SAME_TIME_UNORDERED
ORDER_INDETERMINATE
PROVENANCE_ORDER_ONLY
```

Rules:

- ordering evidence scope = `VISIBLE_TIMESTAMP_ONLY`
- same timestamp default = `SAME_TIME_UNORDERED`
- missing/ambiguous order = `ORDER_INDETERMINATE`
- source row index = `PROVENANCE_ORDER_ONLY`
- same-timestamp internal ordering is forbidden
- source row order is not temporal truth
- relation records cannot create action volume
- relation records cannot create possession truth
- relation records cannot create sequence truth

## Simplified integration surface

Historical Trace / Consequence / Visible Sequence / Partial-Order workflows and branch-specific Termux bootstraps are not copied because they bind obsolete `work/reconstruct-*` branches.

C3 uses:

```text
one exact-head C3 integration CI gate
one operator-selected branch + exact-head C3 Termux runtime bootstrap
```

The runtime bootstrap executes `visible_action_sequence_candidates_current_v1.py`. The adapter composes the entire reconstruction chain through Consequence → Trace → C2 Cross-Role → upstream C2/C1 layers.

## Explicit exclusions

C3 does not land or promote:

- Match Context Slicer / context re-binding
- Analyst Episode Locator
- recurrence / pattern intelligence
- Evidence Graph / argument routing
- tactical truth
- possession truth
- production release

Those are downstream controlled landings.

## Claim boundary

```text
trackable_action_candidate_is_event_truth=false
physical_action_identity_truth=false
trace_count_is_physical_action_count=false
consequence_candidate_is_causal_truth=false
continuation_candidate_is_possession_truth=false
window_is_sequence_truth=false
same_timestamp_internal_ordering_allowed=false
source_row_order_is_temporal_truth=false
visible_sequence_candidate_is_sequence_truth=false
visible_sequence_candidate_is_possession_truth=false
single_team_continuity_is_control_truth=false
sequence_duration_is_physical_action_duration=false
phase_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
event_instance_count=0
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Runtime evidence policy

#267 has verified physical ACTIVE_MATCH evidence on source head `a8b5d84...`. That evidence remains source-head evidence only.

It does not automatically promote the integrated C3 head.

Fresh execution against:

```text
runtime/active_single_match/current
```

is required before integrated ACTIVE_MATCH promotion.

## Acceptance sequence

```text
final-state extraction
→ C1 regression
→ C2 regression
→ exact-head C3 CI
→ review/thread audit
→ mergeability/current-main audit
→ controlled main landing
→ fresh ACTIVE_MATCH revalidation when operator runtime is available
```

## Initial status

`C3_RECONSTRUCTION_SNAPSHOT_ASSEMBLED / EXACT_HEAD_CI_PENDING / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`
