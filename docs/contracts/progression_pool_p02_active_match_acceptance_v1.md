# P02 Progression Pool — ACTIVE_MATCH Acceptance V1

Status: contract-only acceptance specification.

Purpose: validate that the P02 layered refinery produces additional defensible progression intelligence on one real admitted match package without evidence inflation or claim-ceiling promotion.

## Authority

Repository/test/CI evidence is not physical ACTIVE_MATCH acceptance.

Physical acceptance must execute the exact tested head against:

```text
$HOME/hpfa_claim_integrity/hpfa/runtime/active_single_match/current
```

or the exact current physical authority resolved from that pointer.

## Required identity

Record:
- tested_commit_sha
- active_match_authority_path
- active_match_surface_snapshot_id
- match_surface_binding_id
- execution_timestamp
- output_root

No filename/team/player identity may be hard-coded into product logic.

## Required P02 counters

- p02_pool_item_count
- p02_team_pool_item_count
- p02_process_unit_candidate_count
- p02_partial_order_signature_group_count
- p02_repeated_signature_group_count
- p02_process_unit_comparison_population_count
- p02_eligible_process_unit_comparison_population_count
- p02_pairwise_comparison_candidate_count
- p02_opposite_outcome_comparison_candidate_count
- p02_independence_admitted_comparison_count
- p02_independence_not_admitted_comparison_count
- p02_c4_packet_candidate_count
- p02_semantic_zone_complete_process_unit_count
- p02_semantic_zone_unresolved_process_unit_count
- p02_advanced_access_visible_count
- p02_no_advanced_access_visible_count
- p02_advanced_access_unresolved_count
- p02_invented_semantics_count
- p02_lost_atom_count

## C4 downstream counters

For P02-origin comparison packets:
- packet_count
- admitted_counterevidence_count
- dependency_challenge_count
- non_support_count
- unresolved_counterevidence_count
- contradiction_signal_count
- review_required_chain_count
- fail_closed_chain_count

## Hard acceptance invariants

1. invented_semantics_count == 0.
2. Same dependency/evidence root must not multiply an independent vote.
3. Same timestamp must not create internal total order.
4. Coordinate path must not become tracking or metric-distance truth.
5. Provider-coordinate directness remains proxy.
6. Outcome difference alone must not imply OPPOSITE.
7. OPPOSITE comparison requires explicit outcome_relation.
8. COUNTEREVIDENCE requires exact-context admission + resolved OPPOSITE outcome + distinct dependency roots + admitted evidence-unit independence.
9. Evidence-unit independence is not statistical independence.
10. Shared trace roots or overlapping admitted intervals must block independence admission.
11. No-visible-follow-up remains unresolved, not failure.
12. Aggregate XLSX context cannot create occurrence identity.
13. Pool routing cannot create new evidence votes.
14. production_release == false.
15. canonical_event_count == UNKNOWN.
16. true_action_count == UNKNOWN.

## Acceptance states

### PASS

May be declared only when:
- exact-head runtime completes,
- all hard invariants hold,
- P02 output is present,
- no P02-origin FAIL_CLOSED chain is produced,
- invented_semantics_count == 0,
- physical output is reproducible from the declared input authority.

PASS does not require counterevidence to exist.
Zero admitted counterevidence is valid if no eligible opposite comparison exists.

### DEGRADED

Use when:
- P02 executes but required optional dimensions are missing,
- route/zone/opponent/game-state coverage is incomplete,
- comparison population is too small,
- no physical contradiction exists,
- some constructs are NOT_EVALUATED.

DEGRADED is not FAIL.

### REVIEW_REQUIRED

Use when:
- dependency/independence is unresolved,
- comparison context is unresolved,
- grid/zone semantics conflict,
- information reconciliation cannot be fully established,
- P02 packet reaches C4 but stays review-bounded.

### FAIL_CLOSED

Use when:
- invented semantics are detected,
- evidence identity is multiplied,
- aggregate creates occurrence identity,
- same-time total order is forced,
- physical/tracking/tactical truth is promoted without observation support,
- exact runtime authority cannot be established.

## Football information-gain acceptance

Report separately, without one composite score:
- typed process-unit visibility
- recurrence visibility
- semantic-zone path coverage
- advanced-access resolution
- route/variant visibility
- branch-divergence visibility
- exact-context comparison coverage
- admitted counterevidence coverage
- unresolved burden
- opponent-follow-up visibility
- team-specific process visibility

The core decision question:

> Given a different admitted match package, does P02 let HPFA read progression more correctly, more deeply and more defensibly than before?

No information gain => LATER/REJECT.

Defaults:
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
