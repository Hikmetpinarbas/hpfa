# HPFA Intelligence Layer Integration Audit V1

Status: `REVIEW_REQUIRED`

Release meaning: audit evidence only. No executable orchestration, ACTIVE_MATCH evidence, final report output or production release claim.

## Objective

Determine whether the current Intelligence Layer modules form a directly composable product pipeline rather than a collection of individually valid modules.

Target chain:

```text
composite evidence packet
-> multi-signal fusion
-> composite argument
-> defeasible argument route
-> evidence graph
-> 360 evidence lens matrix
-> safe sentence
-> analyst report block
-> report output contract
-> draft assembly eligibility
```

## Product authority

```text
hpfa main = product code truth
runtime/active_single_match/current = match truth
HP-Motor / HP-Engine / HP-PROJELERI / Drive / Dropbox = donor/reference only
```

ADAPT_NOT_COPY remains mandatory.

## Current integration matrix

| Step | Producer output | Consumer requirement | Compatibility | Audit result |
|---|---|---|---|---|
| Packet -> Fusion | `packet_id`, `packet_family`, input refs, signals, `claim_ceiling=composite_candidate_only` | same standard fields | PARTIAL_PASS | Standard fields align, but upstream packet failure state is not propagated by Fusion. |
| Fusion -> Argument | `fusion_id`, `relation_records`, `claim_ceiling=fusion_relation_candidate_only` | same standard fields | PASS_WITH_RISK | Standard fields align; nested forbidden-field handling is not uniform. |
| Argument -> Defeasible Router | argument candidate, counter evidence, withdrawal conditions | explicit argument identity and counter-evidence surface | PARTIAL_PASS | Candidate routing exists, but integration adapter and end-to-end fixture are absent. |
| Argument -> Evidence Graph | argument identity, evidence refs, counter scenarios, withdrawal conditions | argument candidate-only contract | PASS_WITH_RISK | Graph path exists; no end-to-end producer-consumer test. |
| Evidence Graph -> Lens Matrix | `graph_id`, `nodes`, `edges`, `claim_ceiling=evidence_graph_candidate_only` | same standard fields | PASS | Nested forbidden scan hotfix merged. |
| Evidence Graph -> Safe Router | graph identity and evidence node families | candidate graph contract | PASS_WITH_RISK | Standard safe-sentence output exists; no whole-chain execution test. |
| Safe Router -> Report Block | `safe_sentence_candidate_tr`, `claim_ceiling=safe_sentence_candidate_only` | non-empty standard field | PASS | Legacy alias cannot rescue an empty standard value. |
| Report Block -> Output Contract | `report_block_candidate_tr`, `claim_ceiling=analyst_report_block_candidate_only` | same standard fields | PASS | Include/review/reject contract exists. |
| Output Contract -> Assembly Gate | contract item identity, inclusion decision, candidate text, claim ceiling | draft assembly eligibility inputs | PASS_WITH_RISK | Contract is defined; no integrated execution fixture. |

## Confirmed blocker 1 — Packet failure propagation gap

`composite_evidence_packet_builder_lite_v1` emits:

```text
hard_block_hits
status=FAIL_CLOSED
decision=BLOCK_PACKET
```

`multi_signal_evidence_fusion_lite_v1` currently validates required fields, claim ceiling, output flags and forbidden fields, but does not explicitly reject an upstream packet because it already carries:

```text
hard_block_hits
status=FAIL_CLOSED
decision=BLOCK_PACKET
```

Risk:

A packet that failed closed for minimum-source or other packet-level reasons may still be reinterpreted by Fusion if its fields remain populated.

Required correction:

```text
_upstream_packet_failed(packet)
```

must block Fusion when any of these are true:

```text
hard_block_hits is non-empty
decision starts with BLOCK
status is FAIL_CLOSED or BLOCKED
```

Required regression tests:

```text
test_failed_upstream_packet_blocks_fusion
test_block_packet_decision_blocks_fusion
test_packet_hard_block_hits_propagate_to_fusion
```

## Confirmed blocker 2 — Forbidden-field scan inconsistency

The current Intelligence Layer does not use one shared recursive forbidden-field policy.

Observed states:

```text
Composite Evidence Packet Builder: top-level scan
Multi-Signal Evidence Fusion: top-level scan
Composite Argument Builder: top-level scan
Evidence Lens Matrix: recursive path-aware scan after hotfix
Discipline Lens Registry candidate: recursive path-aware scan
```

Risk:

Nested payload fields such as:

```text
input_features[0].claim_text
supporting_signals[0].payload.tactical_truth
relation_records[0].safe_sentence_candidate_tr
```

may bypass early-layer claim guards.

Required correction:

Create one HPFA-native utility or identical contract implementation:

```text
scan_forbidden_fields_recursive(value) -> path-aware hit list
```

Minimum target modules:

```text
composite_evidence_packet_builder_lite_v1
multi_signal_evidence_fusion_lite_v1
composite_argument_builder_lite_v1
evidence_graph_engine_lite_v1
safe_argument_router_tr_lite_v1
```

## Confirmed blocker 3 — No end-to-end contract execution fixture

Each module has unit tests, but no single test proves that real producer output can be passed unchanged into the next consumer through the whole chain.

Required fixture:

```text
synthetic match-agnostic candidate input
-> packet output
-> fusion output
-> argument output
-> evidence graph output
-> lens matrix output
-> safe sentence output
-> report block output
-> output contract output
-> assembly gate output
```

The fixture must not contain real team, match, competition, date or sample identity.

Required tests:

```text
test_intelligence_chain_standard_fields_connect
test_intelligence_chain_upstream_failure_propagates
test_intelligence_chain_nested_forbidden_field_fails_closed
test_intelligence_chain_canonical_event_count_stays_unknown
test_intelligence_chain_no_sample_match_identity_leak
```

## Confirmed blocker 4 — Defeasible route is not yet positioned in one canonical path

Current architecture permits both:

```text
argument -> evidence graph
argument -> defeasible router
```

The canonical order must be declared.

Recommended order:

```text
argument candidate
-> defeasible argument router
-> routed argument candidate
-> evidence graph
```

Reason:

The graph should represent the argument after explicit support, weakening, withdrawal and block routing. Otherwise the graph may preserve an argument that should already have been withdrawn.

Required contract decision:

```text
defeasible_argument_router_lite_v1 becomes the canonical upstream for evidence_graph_engine_lite_v1
```

Evidence Graph must preserve:

```text
argument_route_state
counter_evidence_refs
matched_withdrawal_conditions
unmatched_withdrawal_conditions
```

## Orchestrator readiness decision

Current decision:

```text
NOT_READY_FOR_INTELLIGENCE_PIPELINE_ORCHESTRATOR_IMPLEMENTATION
```

Reason:

```text
packet failure propagation gap
recursive forbidden scan inconsistency
no end-to-end producer-consumer fixture
canonical position of defeasible routing unresolved
```

## Required correction order

```text
P0  Fusion upstream packet failure propagation
P0  Recursive forbidden-field guard for Packet/Fusion/Argument
P0  Canonical argument -> defeasible route -> graph contract
P1  End-to-end contract fixture
P1  Intelligence Pipeline Orchestrator Lite V1
P2  Contradiction Candidate Engine Lite V1
P2  Match-level Knowledge Graph V2
P3  ACTIVE_MATCH Intelligence Run
```

## Proposed orchestrator contract

Future module id:

```text
intelligence_pipeline_orchestrator_lite_v1
```

Required stage ledger fields:

```text
run_id
stage_index
stage_module_id
input_artifact_type
input_artifact_ids
output_artifact_type
output_artifact_ids
status
decision
claim_ceiling
hard_block_hits
review_hits
engineering_evidence
analyst_evidence
```

Fail-closed rule:

```text
No downstream stage may run when the canonical upstream stage is BLOCKED or FAIL_CLOSED.
```

Review rule:

```text
REVIEW_REQUIRED may be recorded and stopped; it must not silently become SMOKE_PASS downstream.
```

Output boundary:

```text
candidate pipeline ledger only
no final report text
no production report
no tactical truth
no dominance/control truth
no coach intention truth
no off-ball truth
no causal truth
canonical_event_count=UNKNOWN until validated
```

## Analyst evidence expected from future ACTIVE_MATCH execution

The orchestrator must eventually expose:

```text
which visible signals were grouped
which relations supported or qualified the argument
which counter evidence weakened it
which withdrawal condition matched
which evidence lenses were missing
why the candidate stopped, continued or was routed to review
```

## Engineering evidence expected

```text
module executed
input accepted or rejected
output written
status and decision recorded
claim ceiling preserved
failure propagated
phone output root validated
```

## Final audit decision

```text
INTEGRATION_GAPS_CONFIRMED
ORCHESTRATOR_IMPLEMENTATION_BLOCKED_UNTIL_P0_CORRECTIONS
```
