# Composite Argument Builder Lite V1

Module id: `composite_argument_builder_lite_v1`

## Product purpose

Composite Argument Builder Lite V1 reads candidate-only fusion relation records and builds argument candidates for later safe-language routing.

It is the third productive intelligence node in the Composite Football Intelligence line.

It does not create claim text, safe sentences or analyst report prose.

## Football value

The analyst can now see a candidate argument object with supporting refs, qualifying refs, contradicting refs, context refs, relation scope, analysis route, counter scenarios, withdrawal conditions and claim ceiling.

Example product reading:

```text
right_channel_access SUPPORTS
low_shot_volume QUALIFIES
window_001 CONTEXTUALIZES
-> context_bound_relation
-> bidirectional
-> progression_without_terminal_value argument candidate
```

## Event relation scope rule

A football event may be an isolated observation, a context-bound relation, or part of a sequence candidate. It must not be treated as a chain member by default.

The module emits one of:

```text
standalone_observation
context_bound_relation
sequence_candidate
```

No sequence truth or organism truth is produced.

## Bidirectional analysis route rule

The module also emits one of:

```text
unit_to_whole
whole_to_unit
bidirectional
undetermined
```

Meaning:

```text
whole_to_unit = whole/context/team/phase/window surface helps read the unit action
unit_to_whole = unit/action/event/feature surface helps form a whole/context candidate
bidirectional = both routes are present in the same argument candidate
```

`bidirectional` is candidate-only. It does not create tactical truth, causal truth, sequence truth or organism truth.

## Runtime authority

Only HPFA-generated ACTIVE_MATCH artifacts may become runtime input.

Google Drive, Dropbox, Sider Scholar and donor repos are reference-only and may guide contracts, naming and tests. They do not become runtime truth.

## Required upstream

```text
multi_signal_evidence_fusion_lite_v1
```

## Initial argument families

```text
progression_without_terminal_value
territory_access_without_shot_conversion
recovery_to_progression_chain
restart_dependency_with_low_open_play_value
high_loss_exposure_under_context
corridor_bias_with_terminal_limit
circulation_without_penetration
direct_play_isolation_candidate
late_terminal_pressure_candidate
defensive_event_height_without_pressing_truth
player_function_proxy_from_sequence_role
rhythm_shift_candidate_from_event_density
```

## Allowed outputs

```text
argument candidate
relation scope
analysis route
whole-to-unit flag
unit-to-whole flag
bidirectional flag
standalone observation flag
context-bound relation flag
sequence candidate flag
support ref list
qualifier ref list
contradiction ref list
counter scenarios
withdrawal conditions
safe-router readiness
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
READY_FOR_SAFE_ROUTER
READY_FOR_SAFE_ROUTER_WITH_QUALIFIER
READY_FOR_SAFE_ROUTER_WITH_CONTRADICTION
INSUFFICIENT_SUPPORT
BLOCK_ARGUMENT
```

## Hard blocks

```text
fusion_required_fields_missing
upstream_fusion_failed_closed
upstream_fusion_forbidden_output_attempted
upstream_fusion_claim_output_allowed
upstream_fusion_report_language_allowed
sequence_argument_requires_sequence_scope
rhythm_argument_requires_context_or_sequence_scope
analysis_route_undetermined
counter_scenario_required
withdrawal_condition_required
```

## Upstream failure rule

If the upstream fusion record carries hard blocks, `decision=BLOCK_FUSION`, `fusion_status=BLOCKED`, or `status=FAIL_CLOSED`, the argument builder must fail closed. A failed fusion must never be promoted into an argument candidate.

## Test requirements

```text
test_argument_requires_fusion_id
test_argument_requires_relation_records
test_context_bound_relation_scope_detected
test_standalone_observation_scope_detected
test_sequence_candidate_scope_detected
test_bidirectional_route_detected_from_unit_and_whole_refs
test_whole_to_unit_route_detected
test_unit_to_whole_route_detected
test_sequence_argument_requires_sequence_scope
test_argument_preserves_support_qualifier_context_refs
test_argument_preserves_explicit_contradiction_refs
test_failed_upstream_fusion_blocks_argument
test_quality_truth_upstream_output_blocks_argument
test_forbidden_upstream_output_blocks_argument
test_argument_does_not_emit_claim_or_sentence
test_argument_blocks_truth_language_families
test_write_outputs_rejects_nested_phone_output
test_no_sample_match_identity_leak
```

## Release status

SMOKE_PASS target only.
Not ACTIVE_MATCH_EVIDENCE_PASS.
Not PRODUCTION_RELEASE.

PASS != RELEASE.
