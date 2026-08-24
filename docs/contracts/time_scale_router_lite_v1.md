# Time Scale Router Lite V1 — Admission Propagation

Status: P0_HARDENING_CANDIDATE
Claim safety: `TIME_SCALE_CANDIDATE_ONLY`

The router may temporally admit a minute window only if the upstream Event Window report:
- is `PASS`;
- has `time_field_admission_status=ADMITTED`;
- has `window_integrity_summary.downstream_ready=true`;
- has `ordering_authority=PARTIAL_ORDER_ONLY`;
- explicitly forbids source-row temporal truth and same-timestamp internal order.

A minute-shaped window without those conditions routes to `TIME_SEMANTIC_REVIEW_REQUIRED`.
Context-ordinal/event-index windows route to `PROVENANCE_BUCKET_REVIEW_ONLY`.

The router publishes:
`upstream_time_admission_status`
`upstream_time_allowed`
`downstream_time_allowed`
`downstream_sequence_time_allowed`
`downstream_phase_time_allowed`
`downstream_rhythm_time_allowed`

No route creates time-window, sequence, phase, rhythm, possession, tactical or dominance truth.
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
