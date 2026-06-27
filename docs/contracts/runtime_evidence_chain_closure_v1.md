# HPFA Runtime Evidence Chain Closure V1

Date: 2026-06-27

Status: SPEC_ONLY

## Product Node

P0B Runtime Evidence Chain Closure

## Purpose

This contract closes the gap between existing HPFA Lite modules and release-safe product evidence.

HPFA already has modules that can read ACTIVE_MATCH surfaces, build windows, route time scale, tag axis integrity, export readings and maintain Canonical Event Lite count semantics. The missing layer is a shared evidence chain that binds every runtime module to source authority, ACTIVE_MATCH identity, engineering evidence, analyst evidence, claim boundary and release status.

## Source Evidence

This contract is informed by a Termux scan package produced on 2026-06-27.

The scan showed three product-relevant facts:

1. The active runtime path can contain a match different from the declared handoff test match.
2. ACTIVE_MATCH surfaces expose `start`, `end` and `half` fields as source time primitives.
3. Runtime output evidence is not guaranteed merely because a runner exists.

These facts require runtime validation before any module can claim ACTIVE_MATCH evidence.

## Required Chain

Every runtime-facing module must preserve this chain:

```text
source role
-> ACTIVE_MATCH identity check
-> input surface inventory
-> module execution
-> output writing
-> engineering evidence
-> analyst evidence
-> claim boundary
-> release status normalization
```

No module may jump from successful execution to release.

## Required Consumers

The first consumers should be:

```text
active_match_full_run_lite_v1
active_match_spine_runner
canonical_event_lite_v1
event_window_builder_lite_v1
time_scale_router_lite_v1
axis_integrity_tagger_lite_v1
phase_candidate_tagger_lite_v1
postmatch_analyst_report_lite_v1
```

## Runtime Identity Rule

A module may not report `ACTIVE_MATCH_EVIDENCE_PASS` unless the observed runtime identity is compatible with the declared runtime manifest identity.

Product modules must not hardcode team names, match names, dates, tournaments or sample ids. Runtime identity must be read from manifest inputs when available and reported as evidence.

If identity is missing or inconsistent, the module must return one of:

```text
REVIEW_REQUIRED
FAIL_CLOSED
```

It must not return `PRODUCTION_RELEASE`.

## Time Primitive Rule

When source surfaces expose `start`, `end` and `half`, these are the source time primitives.

`minute` is a derived field, not source truth.

Required derivation order:

```text
raw_start_seconds
raw_end_seconds
half
half_clock_seconds
absolute_match_seconds
football_minute
minute_display
```

No possession, sequence, rhythm, momentum or narrative module should treat minute as primitive when start/end/half are available.

## Count Semantics Rule

Canonical Event Lite count semantics remain binding:

```text
surface_row_inventory_total != canonical_event_count
canonical_event_count = UNKNOWN
deduplicated_event_count = UNKNOWN
event_count_claim_allowed = false unless a later gate explicitly allows it
```

Visible surface row evidence may support analyst-facing inventory and volume language. It may not create complete event truth.

## Evidence Ledger Minimum Fields

Every ledger entry must contain at least:

```json
{
  "run_id": "string",
  "module_id": "string",
  "status": "REVIEW_REQUIRED",
  "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
  "runtime_active_match_path": "string",
  "declared_active_match_identity": "UNKNOWN",
  "observed_runtime_identity": "UNKNOWN",
  "runtime_identity_match": false,
  "canonical_event_count": "UNKNOWN",
  "surface_rows_processed": 0,
  "outputs_written": [],
  "engineering_evidence": {
    "module_executed": false,
    "output_written": false,
    "phone_output_policy_checked": false,
    "nested_phone_output_rejected": false
  },
  "analyst_evidence": {
    "analyst_summary_written": false,
    "safe_language_only": false
  },
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

## Source Authority Rule

The existing `source_role_registry_v1` is binding.

Only `ACTIVE_MATCH_RUNTIME_AUTHORITY` can provide runtime match truth.

Other sources may support product decisions, but cannot override ACTIVE_MATCH evidence:

```text
GITHUB_PRODUCT_REPO = product code authority
GITHUB_DONOR_REPO = donor support
DRIVE_GOVERNANCE = governance support
DROPBOX_ARCHIVE = archive support
SIDER_ACADEMIC_BACKING = academic support
TERMUX_RUNTIME_EVIDENCE = operator/runtime evidence
```

## Claim Boundary

Allowed language:

```text
visible surface evidence indicates
row-level evidence shows
action-family volume suggests
candidate state detected
requires later validation
```

Blocked language unless later gates explicitly allow it:

```text
dominance truth
tactical truth
coach intention
pitch control truth
off-ball structure truth
fatigue truth
complete event truth
```

## Required Tests

```text
test_runtime_identity_drift_blocks_active_match_evidence_pass
test_start_end_half_are_time_primitives
test_minute_is_derived_not_source_truth
test_no_canonical_event_count_claim
test_surface_rows_not_canonical_events
test_source_role_reference_only_cannot_be_runtime_truth
test_evidence_ledger_requires_engineering_and_analyst_evidence
test_phone_output_flat_path_required
test_phase_candidate_cannot_claim_phase_truth
```

## Release Rule

`PASS` is not release.

This contract can only move beyond `SPEC_ONLY` after:

1. a runtime evidence ledger module exists;
2. the module has tests;
3. ACTIVE_MATCH execution writes ledger output;
4. analyst evidence is written;
5. claim boundary is preserved;
6. phone output policy is preserved;
7. release status is normalized.

Until then, status remains `SPEC_ONLY` or `REVIEW_REQUIRED`.
