# Event Window Builder Lite V1 — Time Semantic / Partial-Order Hardening

Status: P0_HARDENING_CANDIDATE
Claim safety: `EVENT_WINDOW_CANDIDATE_ONLY`

## Admission
Event windows are football-time candidates only when every used context row has explicit admitted time semantics and the visible minute range passes the semantic sanity guard.

`time_field_admission_status`:
- `ADMITTED`
- `FAIL_CLOSED_UNKNOWN_TIME_UNIT`
- `REVIEW_REQUIRED`
- `MISSING`

Generic numeric magnitude must never choose seconds versus minutes.

`ordering_authority=PARTIAL_ORDER_ONLY`
`source_row_order_is_temporal_truth=false`
`same_timestamp_internal_ordering_allowed=false`

Same-minute multiplicity is `SAME_TIME_UNORDERED` descriptive evidence. Minute equality is not duplicate-event evidence. Duplicate identity requires SHA/reflection lineage.

When time semantics are unknown, conflicted, partial, implausible, or truncated:
- minute temporal admission is disabled;
- any context-ordinal/event-index windows are provenance-only;
- `window_integrity_summary.downstream_ready=false`.

The upper-range check is a semantic corruption sanity guard, not match-length truth.

## Claim locks
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`sequence_truth=false`
`possession_truth=false`
`phase_truth=false`
`rhythm_truth=false`
`time_window_truth=false`
`production_release=false`
