# Evidence Graph Engine Lite V1

Module id: `evidence_graph_engine_lite_v1`

## Product purpose

Evidence Graph Engine Lite V1 reads candidate-only argument records and builds a traceable evidence graph.

It is the fourth productive intelligence node in the Composite Football Intelligence line.

It does not create claim text, safe sentences or analyst report prose.

## Football value

The analyst can trace how an argument candidate is supported, qualified, contextualized, challenged and withdrawn.

Example product reading:

```text
fusion_cep_progression_001
-> arg_fusion_cep_progression_001
right_channel_access -> SUPPORTS_ARGUMENT
low_shot_volume -> QUALIFIES_ARGUMENT
window_001 -> CONTEXTUALIZES_ARGUMENT
shot_timing_or_angle_limited_terminal_action -> CHALLENGES_ARGUMENT
terminal_action_value_becomes_high_in_same_window -> WITHDRAWS_ARGUMENT_IF_TRUE
```

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
composite_argument_builder_lite_v1
```

## Allowed outputs

```text
evidence graph candidate
graph nodes
graph edges
trace start
trace end
support edge
qualifier edge
contradiction edge
context edge
counter-scenario edge
withdrawal-condition edge
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

## Decision states

```text
READY_FOR_EVIDENCE_TRACE_CONSUMER
BLOCK_GRAPH
```

## Hard blocks

```text
argument_required_fields_missing
upstream_argument_failed_closed
upstream_argument_forbidden_output_attempted
upstream_argument_claim_output_allowed
upstream_argument_report_language_allowed
upstream_argument_safe_sentence_allowed
duplicate_graph_node_id
supporting_refs_required_for_graph
```

## Upstream failure rule

If the upstream argument record carries hard blocks, `decision=BLOCK_ARGUMENT`, or `status=FAIL_CLOSED`, the evidence graph must fail closed. A failed argument must never become a traceable graph candidate.

## Test requirements

```text
test_graph_requires_argument_id
test_graph_requires_fusion_id_and_supporting_refs
test_graph_preserves_argument_and_fusion_nodes
test_graph_preserves_support_qualifier_context_nodes
test_graph_preserves_scope_and_route_nodes
test_graph_keeps_counter_scenarios_and_withdrawal_conditions
test_failed_upstream_argument_blocks_graph
test_forbidden_upstream_argument_output_blocks_graph
test_graph_does_not_emit_claim_or_sentence
test_graph_blocks_truth_language_families
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
