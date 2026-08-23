# Evidence Graph Engine Lite V1

Module id: `evidence_graph_engine_lite_v1`

## Product purpose

Evidence Graph Engine Lite V1 reads a **defeasibly routed argument candidate** and builds a traceable evidence graph.

Canonical upstream order:

```text
composite_argument_builder_lite_v1
-> defeasible_argument_router_lite_v1
-> evidence_graph_engine_lite_v1
```

The graph must represent the argument after support / weakening / withdrawal routing. It must not rebuild a pre-routing argument and silently ignore counter-evidence.

It does not create claim text, final safe sentences or analyst report prose.

## Football value

The analyst can trace:

```text
what supports the argument candidate
what qualifies it
what explicit counter-evidence weakens it
which context references bind it
which counter-scenarios remain live
which withdrawal conditions were declared
which withdrawal conditions actually matched
whether the argument remains SUPPORTED, is WEAKENED, or is WITHDRAWN
```

These remain evidence-routing states, not tactical truth.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Termux and donor repos are donor/reference only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
defeasible_argument_router_lite_v1
```

Required minimum fields:

```text
route_id
argument_id
supporting_refs
claim_ceiling=defeasible_argument_candidate_only
defeasible_state in {SUPPORTED, WEAKENED, WITHDRAWN}
```

Optional lineage/context fields preserved when present:

```text
fusion_id
argument_family
relation_scope
analysis_route
whole_to_unit
unit_to_whole
bidirectional
qualifying_refs
counter_evidence_refs
complementary_refs
context_refs
counter_scenarios
declared_withdrawal_conditions
matched_withdrawal_conditions
```

## Allowed outputs

```text
evidence graph candidate
defeasible route node
argument node
fusion lineage node
support / qualifier / counter-evidence nodes
context / complement nodes
counter-scenario nodes
declared withdrawal-condition nodes
matched withdrawal-condition nodes
relation-scope / analysis-route nodes
review_required
review_reasons
```

## Review propagation

```text
SUPPORTED -> graph status may be SMOKE_PASS
WEAKENED -> graph status=REVIEW_REQUIRED
WITHDRAWN -> graph status=REVIEW_REQUIRED
BLOCKED / failed route -> FAIL_CLOSED
```

`REVIEW_REQUIRED` is not an engineering failure. It preserves analyst-facing uncertainty / withdrawal state.

Required review reasons:

```text
defeasible_argument_weakened
defeasible_argument_withdrawn
```

## Blocked outputs

```text
claim text
safe sentence
report language
tactical truth
dominance truth
control truth
coach intention
off-ball truth
pitch-control truth
causal truth
quality truth
sequence truth
organism truth
canonical event count claim
```

Nested forbidden outputs must be scanned recursively with path-aware hits.

## Decision states

```text
READY_FOR_EVIDENCE_TRACE_CONSUMER
ROUTE_EVIDENCE_GRAPH_TO_REVIEW
BLOCK_GRAPH
```

## Hard blocks

```text
defeasible_route_required_fields_missing
upstream_defeasible_route_failed_closed
defeasible_state_invalid
upstream_defeasible_route_forbidden_output_attempted
upstream_defeasible_route_claim_output_allowed
upstream_defeasible_route_report_language_allowed
upstream_defeasible_route_safe_sentence_allowed
canonical_event_count_claim_rejected
duplicate_graph_node_id
supporting_refs_required_for_graph
```

## Claim boundary

```text
claim_ceiling=evidence_graph_candidate_only
canonical_event_count=UNKNOWN
claim_output_allowed=false
report_language_allowed=false
safe_sentence_allowed=false
production_release=false
```

## Release status

Exact-head CI is required for this contract change.
ACTIVE_MATCH evidence is not implied by contract/CI success.
PASS != RELEASE.
MERGED != PRODUCTION_RELEASE.
