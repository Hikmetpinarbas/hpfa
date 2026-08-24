# Sequence Output Contract Guard Lite V1 — Time Admission Regression

Status: P0_HARDENING_CANDIDATE
Claim safety: `SEQUENCE_OUTPUT_CONTRACT_GUARD_ONLY`

A sequence consumer receives `timestamp_or_order=true` only when:
- Event Window time axis is AVAILABLE;
- `time_field_admission_status=ADMITTED`;
- `window_integrity_summary.downstream_ready=true`;
- `ordering_authority=PARTIAL_ORDER_ONLY`;
- at least one minute window is explicitly `temporal_admission=true` and `time_semantic_admission=true`;
- source-row temporal truth and same-timestamp internal ordering remain false.

Context ordinal and legacy event index are provenance-only and never satisfy sequence temporal admission.

`sequence_truth=false`
`consequence_truth=false`
`tactical_truth=false`
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
