# HPFA Match Context Slicer Binding Spec V1

Status: BINDING_SPEC_READY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Module id: match_context_slicer_lite_v1
Claim safety: CONTEXT_PACKET_CANDIDATE_ONLY

This binding spec defines Match Context Slicer Lite V1 as a context packet binding node. It binds upstream HPFA product outputs into context slice packets for downstream intelligence consumers.

It is not a phase engine, possession engine, tactical diagnosis engine, sequence truth producer, event-count validator or production release.

## Decision

PROCEED_TO_MATCH_CONTEXT_SLICER_BINDING_SPEC

Allowed:

- contract
- schema
- test plan
- dry-run implementation
- fail-closed wrapper
- phone output audit

Conditional:

- ACTIVE_MATCH execution

Blocked:

- production binding
- canonical event count
- deduplicated event count
- tactical truth
- phase truth
- possession truth
- sequence truth

## Required upstream inputs

The slicer must read only flat ACTIVE_MATCH / phone-output artifacts from HPFA product modules:

- canonical_event_lite_v1.json
- team_binding_lite_v1.json
- event_identity_resolution_gate_lite_v1.json
- primary_event_surface_gate_lite_v1.json
- source_mapping_contract_v1.json
- source_conflict_registry_lite_v1.json
- minimum_viable_context_lite_v1.json
- event_window_builder_lite_v1.json
- time_scale_router_lite_v1.json
- axis_integrity_tagger_lite_v1.json
- reasoning_grammar_spine_lite_v1.json

Optional downstream consumers must not be treated as upstream truth producers:

- context_signal_apparatus
- phase_sequence_composite
- metric_fusion_engine
- postmatch_analyst_report_lite

## Binding order

Correct order:

```text
minimum_viable_context_lite
+ event_window_builder_lite
+ time_scale_router_lite
+ axis_integrity_tagger_lite
+ source_mapping_contract_lite
+ source_conflict_registry_lite
+ team_binding_lite
-> match_context_slicer_lite_v1
-> context_signal_apparatus
-> metric_fusion_engine
-> reasoning_grammar_spine
-> analyst_report
```

`phase_sequence_composite` is a consumer after context packet production. It must not be read as phase or possession truth by the slicer.

## Required outputs

Flat phone outputs only:

- /sdcard/Download/HPFA/match_context_slicer_lite_v1.json
- /sdcard/Download/HPFA/match_context_slicer_lite_v1.txt
- /sdcard/Download/HPFA/match_context_slicer_lite_v1_audit.json

Nested output paths under the phone output root must fail with:

```text
nested_phone_output_directory_rejected
```

## Minimum context packet fields

Each context slice packet must contain:

```json
{
  "slice_id": "string",
  "source_file": "string",
  "source_role": "string",
  "team_label": "string|null",
  "team_label_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "half_candidate": "1H|2H|ET|UNKNOWN",
  "half_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "score_state_candidate": "LEADING|DRAWING|TRAILING|UNKNOWN",
  "score_state_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "card_state_candidate": "EVEN|PLAYER_UP|PLAYER_DOWN|UNKNOWN",
  "card_state_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "restart_open_play_candidate": "RESTART|OPEN_PLAY_CANDIDATE|UNKNOWN",
  "restart_open_play_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "action_family": "PASS|SHOT|DUEL|CARRY|LOSS|RECOVERY|RESTART|CARD|META|UNKNOWN",
  "action_family_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "zone_candidate": "string|null",
  "zone_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "channel_candidate": "string|null",
  "channel_candidate_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "window_id": "string|null",
  "window_axis": "EVENT_ORDER|TIME_SEC|MINUTE|UNKNOWN",
  "window_status": "VALIDATED|CANDIDATE|UNKNOWN",
  "claim_level": "ROW_OBSERVATION|CONTEXT_CANDIDATE|BLOCKED"
}
```

## Upstream binding ledger

Every upstream artifact must be evaluated before use:

- module_name
- output_found
- json_valid
- txt_valid
- active_match_authority
- phone_output_flat
- claim_boundary
- can_feed_context_slicer
- block_reason

If a required upstream output is missing or invalid, context binding must downgrade or fail closed according to the field dependency.

## Context field status registry

Required field statuses:

- VALIDATED: directly supported by an eligible HPFA product artifact and allowed by its claim boundary.
- CANDIDATE: derived or carried as context candidate, with truth blocked.
- UNKNOWN: missing, unresolved, unsupported or blocked.

Score/card rule:

- if no eligible goal timeline exists, score_state_candidate must be UNKNOWN.
- if no eligible card timeline exists, card_state_candidate must be UNKNOWN.
- metadata or file name must not unlock score/card truth.

## Claim boundary

Required output boundary:

```json
{
  "canonical_event_count": "UNKNOWN",
  "deduplicated_event_count": "UNKNOWN",
  "event_count_claim_allowed": false,
  "production_binding_allowed": false,
  "phase_truth": false,
  "possession_truth": false,
  "sequence_truth": false,
  "time_window_truth": false,
  "score_state_truth": false,
  "card_state_truth": false,
  "tactical_truth": false,
  "dominance_truth": false
}
```

## Required tests

- test_upstream_binding_ledger_reports_missing_required_outputs
- test_context_field_status_registry_defaults_unknown_without_evidence
- test_score_state_unknown_without_goal_timeline
- test_card_state_unknown_without_card_timeline
- test_context_signal_apparatus_is_downstream_consumer_not_upstream_truth
- test_phase_sequence_composite_is_downstream_consumer_not_phase_truth
- test_event_index_window_uses_context_ordinal_not_source_row_index
- test_context_sample_truncation_blocks_complete_summary
- test_match_context_slicer_audit_output_written
- test_nested_phone_output_rejected
- test_no_canonical_event_count_claim
- test_no_sample_match_identity_leak

## Analyst value

The analyst can now ask:

- which team label is attached to this row/slice?
- which event-order/time/window context is attached?
- which half/time candidate is attached?
- which zone/channel candidate is attached?
- which action family is visible?
- which source role and claim boundary govern this evidence?

## Release rule

This binding spec permits dry-run implementation only. ACTIVE_MATCH execution may produce REVIEW_REQUIRED evidence. It does not create PRODUCTION_RELEASE or runtime truth beyond context packet candidates.
