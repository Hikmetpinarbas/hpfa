# HPFA Football Time Foundation Lite V1 Contract

Date: 2026-06-27

Status: SPEC_ONLY

## Product Node

P0B-G3 Football Time Foundation Lite V1

## Purpose

Football Time Foundation Lite defines the minimum claim-safe time model that downstream HPFA modules must consume before phase, possession, sequence, rhythm, metric fusion or report synthesis.

The module does not create phase truth, possession truth, sequence truth, rhythm truth, tactical truth or dominance truth. It only resolves the source time primitives and derived football time fields.

## Source Evidence

The 2026-06-27 Termux ACTIVE_MATCH scan showed that readable runtime CSV/XML surfaces expose:

```text
start
end
half
```

The same scan did not show native source fields for:

```text
minute
second
timestamp
```

Therefore, minute must be treated as a derived display or aggregation field, not primitive source truth.

## Source Authority

Runtime source time must come from:

```text
ACTIVE_MATCH_RUNTIME_AUTHORITY
runtime/active_single_match/current
```

Donor repositories, Drive documents, Dropbox archives, Sider Scholar, Scholar Gateway and Consensus may support the contract but cannot create runtime time truth.

## Inputs

Required:

```text
active_match_dir
out_dir
```

Allowed source columns:

```text
start
end
half
```

Optional aliases may be added later through a source mapping contract, but the module must report which alias was used and whether degradation occurred.

## Outputs

Flat outputs under the selected output root:

```text
football_time_foundation_lite_v1.json
football_time_foundation_lite_v1.txt
```

Nested phone output directories must be rejected through the existing phone output guard.

## Derived Time Model

Required derivation order:

```text
raw_start_seconds = source start
raw_end_seconds = source end
half = source half
half_clock_seconds = derived from start/end within half
absolute_match_seconds = derived cross-half normalized axis
football_minute = derived numeric minute
minute_display = derived display value
```

No module may consume `minute` as primitive when `start/end/half` are available.

## Minimum JSON Shape

```json
{
  "module_id": "football_time_foundation_lite_v1",
  "status": "REVIEW_REQUIRED",
  "claim_safety": "TIME_FOUNDATION_ONLY",
  "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
  "source_time_fields": {
    "start": true,
    "end": true,
    "half": true,
    "minute": false,
    "second": false,
    "timestamp": false
  },
  "derived_time_fields": {
    "raw_start_seconds": true,
    "raw_end_seconds": true,
    "half_clock_seconds": true,
    "absolute_match_seconds": true,
    "football_minute": true,
    "minute_display": true
  },
  "time_axis_status": "TIME_PRIMITIVES_PRESENT_REVIEW_REQUIRED",
  "canonical_event_count": "UNKNOWN",
  "claim_boundary": {
    "phase_truth": false,
    "possession_truth": false,
    "sequence_truth": false,
    "rhythm_truth": false,
    "tactical_truth": false,
    "dominance_truth": false
  }
}
```

## Degradation Rules

If `start` or `end` is missing:

```text
status=FAIL_CLOSED
phase_candidate_allowed=false
sequence_candidate_allowed=false
rhythm_candidate_allowed=false
```

If `half` is missing but start/end exist:

```text
status=REVIEW_REQUIRED
time_axis_status=HALF_FIELD_MISSING_ABSOLUTE_AXIS_REVIEW_REQUIRED
```

If `minute` exists but start/end/half also exist:

```text
minute_source_truth=false
minute_derivation_required=true
```

## Academic Backing

Academic support from passing-sequence entropy, passing-network state dynamics and event-sequence point-process literature supports the need for reliable temporal ordering before sequence, rhythm or network-state interpretation.

Tracking-data literature supports a strict claim ceiling: event-only time foundations do not authorize off-ball structure, pitch-control, tactical-mechanism or dominance claims.

## Claim Boundary

Allowed language:

```text
source time primitives are visible
minute derived from source time fields
time axis candidate is available
time axis requires later validation
```

Blocked language:

```text
phase truth
possession truth
sequence truth
rhythm truth
tactical truth
dominance truth
coach intention
```

## Required Tests

```text
test_start_end_half_are_time_primitives
test_minute_is_derived_not_source_truth
test_missing_start_fails_closed
test_missing_end_fails_closed
test_missing_half_degrades_to_review_required
test_no_canonical_event_count_claim
test_no_phase_truth_claim
test_phone_output_flat_path_required
test_no_sample_match_identity_leak
```

## Downstream Consumers

```text
event_window_builder_lite_v1
time_scale_router_lite_v1
phase_candidate_tagger_lite_v1
possession_boundary_apparatus_lite_v1
sequence_candidate_lite_v1
metric_readiness_report_lite_v1
event_only_rhythm_evidence_stack_v12
postmatch_analyst_report_lite_v1
```

## Release Rule

This contract remains `SPEC_ONLY` until implementation, tests and ACTIVE_MATCH execution write flat outputs and a runtime evidence ledger entry.
