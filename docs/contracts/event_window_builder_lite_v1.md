# Event Window Builder Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `event_window_builder_lite_v1`
Claim safety: `EVENT_WINDOW_CANDIDATE_ONLY`

## Purpose

Build event-only window candidates from Minimum Viable Context surface rows.

This module does not create phase truth, possession truth, sequence truth, rhythm truth or tactical truth.

## Why this exists

Professional post-match analysis requires time-scale and episode context. Match-wide surface volume is not enough.

HPFA must be able to ask:

```text
Which visible action families appear together inside a bounded window?
Where is the window concentrated?
Does the window contain terminal action surface?
Does the window contain loss/recovery/restart surface?
Is the window sufficiently dense for later signal or sequence analysis?
```

## Inputs

Preferred input:

```text
minimum_viable_context_lite_v1.json
```

Fallback input:

```text
flat ACTIVE_MATCH directory with .csv/.tsv/.xml surfaces
```

## Outputs

Flat phone outputs only:

```text
event_window_builder_lite_v1.json
event_window_builder_lite_v1.txt
```

## Window policy

Default minute window:

```text
window_size_mins=5
hop_mins=5
```

Windowing is event-only and minute-bucket based. It is not possession, phase or sequence truth.

## Window candidate fields

```text
window_id
start_minute
end_minute
surface_row_count
action_family_counts
team_label_counts
zone_counts
channel_counts
terminal_action_surface_present
loss_recovery_surface_present
restart_surface_present
context_density
window_confidence
claim_allowed
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
phase_truth=false
possession_truth=false
sequence_truth=false
rhythm_truth=false
tactical_truth=false
dominance_truth=false
claim_safety=EVENT_WINDOW_CANDIDATE_ONLY
```

## Allowed language

```text
event-window candidate
visible action-family window
terminal-action surface present
loss/recovery window surface
restart window surface
requires sequence validation
```

## Forbidden language

```text
possession window truth
phase window truth
sequence truth
rhythm state truth
tactical phase
dominance window
coach intention
```

## Required tests

```text
test_builds_windows_from_minimum_context_json
test_window_counts_action_families
test_terminal_loss_restart_flags
test_claim_boundaries_remain_false
test_no_sample_match_identity_leak
test_flat_outputs
```
