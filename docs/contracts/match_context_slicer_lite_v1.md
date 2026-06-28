# HPFA Match Context Slicer Lite V1

## Status

`IMPLEMENTATION_PREP_READY`

Runtime status: `RUNTIME_IMPLEMENTATION_CONDITIONAL`

This contract defines candidate-only match context slicing for ACTIVE_MATCH evidence. It does not open production binding, canonical event truth, phase truth, possession truth, sequence truth, tactical truth, dominance truth, or coach-intention claims.

## Module

```text
module_id=match_context_slicer_lite_v1
claim_safety=CONTEXT_SLICE_CANDIDATE_ONLY
status=REVIEW_REQUIRED | FAIL_CLOSED
```

## Purpose

The module converts upstream ACTIVE_MATCH surface evidence into analyst-facing context slice candidates. It exists because action-family volume without team, time, match-state, restart/open-play, zone/channel, and window context remains raw surface volume rather than football intelligence.

The slicer groups row-level/context-level evidence by:

- team label
- half candidate
- score-state candidate
- card-state candidate
- restart/open-play candidate
- action family
- zone candidate
- channel candidate
- event window
- source file / source role
- claim level

## Required upstream inputs

Read from a flat input directory, normally `/sdcard/Download/HPFA`:

```text
minimum_viable_context_lite_v1.json
event_window_builder_lite_v1.json
```

Optional upstream support:

```text
time_scale_router_lite_v1.json
axis_integrity_tagger_lite_v1.json
reasoning_grammar_spine_lite_v1.json
active_match_identity_guard_lite_v1.json
primary_surface_review_resolution_lite_v1.json
postmatch_analyst_report_lite_v1.json
active_match_analyst_report_lite_v1.json
```

If required inputs are missing, the module must emit `FAIL_CLOSED` and must still write claim-safe JSON/TXT outputs.

## Output files

Only flat phone output is allowed:

```text
/sdcard/Download/HPFA/match_context_slicer_lite_v1.json
/sdcard/Download/HPFA/match_context_slicer_lite_v1.txt
```

Nested output under `/sdcard/Download/HPFA/<subdir>` or `/storage/emulated/0/Download/HPFA/<subdir>` must be rejected with:

```text
nested_phone_output_directory_rejected
```

## Candidate slice fields

Each slice candidate should contain:

```text
slice_id
context_id
context_position
source_file
source_format
source_row_index
source_role
team_label
action_family
previous_action_family
next_action_family
zone_candidate
channel_candidate
window_id
window_axis
half_candidate
score_state_candidate
card_state_candidate
restart_open_play_candidate
claim_level
claim_allowed
```

## Field rules

| Field | Source | Rule |
|---|---|---|
| `team_label` | Minimum Viable Context / team binding candidate | Use candidate label; unknown remains `unknown`. |
| `action_family` | Minimum Viable Context / source mapping | Use candidate family; no event truth claim. |
| `zone_candidate` | Axis / coordinate candidate | Neutral pitch location only; no attacking-direction or pitch-control claim. |
| `channel_candidate` | Axis / coordinate candidate | Neutral channel only; no tactical width claim. |
| `context_position` | Ordered context candidate list | Zero-based ordinal in the loaded or rebuilt context list. |
| `window_id` / `window_axis` | Event Window Builder | Technical segment only; not sequence or possession. For `event_index` windows, match by `context_position`, not by per-file `source_row_index`. |
| `half_candidate` | Time Scale Router / period/minute candidate | If no time/period support, emit `UNKNOWN_HALF`. |
| `score_state_candidate` | Goal timeline | If no verified goal timeline, emit `UNKNOWN_SCORE_STATE`. |
| `card_state_candidate` | Card timeline | If no verified card timeline, emit `UNKNOWN_CARD_STATE`. |
| `restart_open_play_candidate` | action family | Restart/dead-ball can be candidate; open play remains candidate only. |

## Context sample safety rule

`context_candidates_sample` must never be summarized as complete match evidence when upstream `context_candidate_count` is larger than the sample length.

If full `context_candidates` are present, the slicer may summarize them as `COMPLETE_CONTEXT_CANDIDATES`.

If only `context_candidates_sample` is present and upstream `context_candidate_count` is larger, the slicer must either rebuild full context from available surface rows or mark:

```text
context_sample_truncated=true
slice_summary_scope=SAMPLE_ONLY_BLOCKED_FOR_COMPLETE_MATCH_SUMMARY
blocker=truncated_context_sample_only
```

Required report fields:

```text
upstream_context_candidate_count
context_source
context_sample_truncated
rebuilt_full_context
slice_summary_scope
```

## Required claim boundary

Every output must include:

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

## Allowed analyst language

Allowed:

```text
visible surface evidence indicates...
row-level evidence shows...
context slice candidates suggest...
coordinate evidence is concentrated in...
event-index window evidence shows...
requires later validation...
```

Blocked:

```text
team deliberately...
coach planned...
dominated...
controlled the pitch...
off-ball structure...
true tactical phase...
clean possession sequence...
verified rhythm state...
```

## Decisions

```text
FAIL_CLOSED_MISSING_REQUIRED_INPUTS
CONTEXT_SLICES_CANDIDATE_ONLY
```

## Required tests

```text
test_context_slicer_reads_minimum_context
test_event_index_window_uses_context_ordinal_not_source_row_index
test_context_sample_truncation_blocks_complete_summary
test_full_context_not_marked_truncated
test_team_slice_candidates
test_half_candidate_unknown_when_time_missing
test_score_state_candidate_unknown_without_goal_timeline
test_card_state_candidate_unknown_without_card_timeline
test_restart_open_play_candidate_from_action_family
test_no_phase_possession_sequence_claims
test_no_tactical_or_dominance_claims
test_flat_phone_outputs
test_nested_phone_output_rejected
```

## Release rule

This module can reach `ACTIVE_MATCH_EVIDENCE_PASS` only after ACTIVE_MATCH execution evidence. It cannot become `PRODUCTION_RELEASE` while upstream identity/source review blockers remain open.
