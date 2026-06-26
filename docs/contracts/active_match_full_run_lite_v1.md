# Active Match Full Run Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `active_match_full_run_lite_v1`
Claim safety: `RUNTIME_EVIDENCE_ONLY`

## Purpose

Run the current repo-local ACTIVE_MATCH evidence chain with one command.

## Scope

This runner executes engineering and analyst evidence modules. It is not yet a broadcast match report composer.

## Current chain

```text
event_window_builder_lite_v1
time_scale_router_lite_v1
axis_integrity_tagger_lite_v1
```

## Output

Repo-local output:

```text
active_match_full_run_lite_v1.json
active_match_full_run_lite_v1.txt
```

## Safety rules

- Reject empty or missing match input.
- Require nonzero evidence counts.
- Use the same output-root guard as child modules.
- Do not emit canonical event count.
- Do not emit phase, possession, sequence, rhythm, tactical or dominance truth.

## Analyst limitation

This runner tells whether the match can be analyzed by time, space, team and action-family axes. It does not yet write a football-style match analysis.

Next node should be:

```text
active_match_analyst_reading_export_lite_v1
```
