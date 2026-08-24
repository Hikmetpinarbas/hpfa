# Minimum Viable Context Lite V1

Status: P0_TIME_SEMANTIC_HARDENING_CANDIDATE
Module id: `minimum_viable_context_lite_v1`
Claim safety: `CONTEXT_CANDIDATE_ONLY`

## Purpose
Build match-local visible context candidates without converting raw numeric fields or source row order into football temporal truth.

## Time semantic admission
Only explicit unit-bearing field roles are admitted generically:
- minute/minutes/minute_raw/match_minute -> `MINUTE`
- second/seconds/second_raw/absolute_time_seconds/match_second -> `SECOND`
- clock-shaped values may be admitted as `CLOCK` when parseable.

Generic numeric `time`, `timestamp`, `start`, `end`, `start_time`, `end_time`, `match_time`, `game_time`, `t`, `tc` do **not** acquire a unit from magnitude. They remain `UNKNOWN_TIME_UNIT` unless an upstream validated semantic mapping gives an explicit minute/second role.

Required candidate fields:
`time_field_admission_status`, `time_unit_status`, `raw_time_candidates`, `admitted_time_evidence`, `rejected_time_field_candidates`.

## Ordering boundary
`source_row_index` is provenance only.
No global source-row sort creates previous/next football actions.
`previous_action_family=UNKNOWN_PREVIOUS_ACTION`
`next_action_family=UNKNOWN_NEXT_ACTION`
`ordering_authority=PARTIAL_ORDER_ONLY`
`source_row_order_is_temporal_truth=false`
`same_timestamp_internal_ordering_allowed=false`

## Claim locks
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`phase_truth=false`
`possession_truth=false`
`sequence_truth=false`
`tactical_truth=false`
`production_release=false`

## Required tests
- explicit minute admission
- explicit second conversion without magnitude heuristic
- generic numeric start/time/timestamp does not create time truth
- source order does not create previous/next adjacency
- no sample match identity leak
