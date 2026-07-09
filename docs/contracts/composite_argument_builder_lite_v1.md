# Composite Argument Builder Lite V1

Module id: `composite_argument_builder_lite_v1`

## Product purpose

Composite Argument Builder Lite V1 reads candidate-only fusion relation records and builds argument candidates for later safe-language routing.

It is the third productive intelligence node in the Composite Football Intelligence line.

It does not create claim text, safe sentences or analyst report prose.

## Football value

The analyst can now see a candidate argument object with:

```text
supporting refs
qualifying refs
contradicting refs
context refs
counter scenarios
withdrawal conditions
claim ceiling
```

Example product reading:

```text
right_channel_access SUPPORTS
low_shot_volume QUALIFIES
window_001 CONTEXTUALIZES
→ progression_without_terminal_value argument candidate
```

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
upstream_fusion_forbidden_output_attempted
upstream_fusion_claim_output_allowed
upstream_fusion_report_language_allowed
counter_scenario_required
withdrawal_condition_required
```

## Test requirements

```text
test_argument_requires_fusion_id
test_argument_requires_relation_records
test_argument_uses_predefined_family
test_argument_preserves_support_qualifier_context_refs
test_argument_preserves_explicit_contradiction_refs
test_argument_requires_counter_scenario_and_withdrawal_condition
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
