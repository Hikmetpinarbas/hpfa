# Axis Integrity Tagger Lite V1 — Time Permission Contraction

Status: P0_HARDENING_CANDIDATE
Claim safety: `AXIS_INTEGRITY_CANDIDATE_ONLY`

Minute-axis availability is not inferred from minute-bearing counts alone.
`downstream_time_allowed` must be explicitly admitted by Time Scale Router.

If router time semantics are review/fail/unknown, the minute axis is not downstream-available and all time-dependent permissions contract:
- downstream_time_allowed=false
- downstream_phase_candidate_allowed=false
- downstream_sequence_candidate_allowed=false
- downstream_rhythm_candidate_allowed=false

`time_permission_basis` retains router permission and upstream time admission state.

Axis availability never creates phase, possession, sequence, rhythm, tactical or dominance truth.
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
