# HPFA Active Match Identity Guard Lite V1 Contract

Date: 2026-06-27

Status: SPEC_ONLY

## Product Node

P0B-G9 Active Match Identity Guard Lite V1

## Purpose

Active Match Identity Guard Lite prevents HPFA from reporting ACTIVE_MATCH evidence against the wrong runtime match.

The guard does not create football truth. It verifies that the observed runtime identity is compatible with the declared runtime manifest identity before downstream modules can report `ACTIVE_MATCH_EVIDENCE_PASS`.

## Source Evidence

A 2026-06-27 Termux scan showed that `runtime/active_single_match/current` can contain a match identity different from the expected handoff target.

This is a runtime authority drift risk.

## Source Authority

Runtime truth may only come from:

```text
ACTIVE_MATCH_RUNTIME_AUTHORITY
runtime/active_single_match/current
```

Termux scan evidence is operator/runtime evidence. It may reveal drift, but it does not become product release proof by itself.

GitHub product repo remains code authority.

## Inputs

Required:

```text
active_match_dir
out_dir
```

Optional:

```text
declared_manifest_path
expected_manifest_identity
```

The module must read identity generically from manifests or runtime file inventory. It must not hardcode team names, match names, dates, tournaments or sample ids.

## Outputs

Flat outputs under the selected output root:

```text
active_match_identity_guard_lite_v1.json
active_match_identity_guard_lite_v1.txt
```

Nested phone output directories must be rejected through the existing phone output guard.

## Identity Fields

The JSON output should expose:

```json
{
  "module_id": "active_match_identity_guard_lite_v1",
  "status": "REVIEW_REQUIRED",
  "claim_safety": "RUNTIME_IDENTITY_CHECK_ONLY",
  "active_match_dir": "string",
  "declared_identity": {
    "source": "UNKNOWN",
    "match_label": "UNKNOWN",
    "date": "UNKNOWN",
    "competition": "UNKNOWN"
  },
  "observed_identity": {
    "source": "runtime_file_inventory",
    "match_label_candidates": [],
    "date_candidates": [],
    "competition_candidates": []
  },
  "identity_match_status": "UNKNOWN_OR_REVIEW_REQUIRED",
  "active_match_evidence_allowed": false,
  "canonical_event_count": "UNKNOWN",
  "claim_boundary": {
    "event_truth": false,
    "phase_truth": false,
    "possession_truth": false,
    "sequence_truth": false,
    "rhythm_truth": false,
    "tactical_truth": false,
    "dominance_truth": false
  }
}
```

## Status Rules

```text
PASS
```

is not allowed as a release status.

Allowed runtime statuses:

```text
ACTIVE_MATCH_IDENTITY_COMPATIBLE_REVIEW_REQUIRED
REVIEW_REQUIRED
FAIL_CLOSED
```

The guard may only allow downstream ACTIVE_MATCH evidence if:

```text
active_match_dir exists
runtime surfaces exist
declared identity exists or is explicitly UNKNOWN
observed identity is extracted
identity comparison does not detect contradiction
```

If a contradiction is detected:

```text
status=FAIL_CLOSED
active_match_evidence_allowed=false
```

If identity is missing or ambiguous:

```text
status=REVIEW_REQUIRED
active_match_evidence_allowed=false
```

## Claim Boundary

Allowed language:

```text
runtime identity compatible
runtime identity unresolved
runtime identity drift detected
observed runtime identity candidate
requires operator validation
```

Blocked language:

```text
match truth validated
team behaviour truth
phase truth
possession truth
sequence truth
tactical truth
dominance truth
```

## Required Tests

```text
test_runtime_identity_drift_blocks_active_match_evidence_pass
test_missing_manifest_returns_review_required
test_runtime_file_inventory_identity_candidates_are_generic
test_no_sample_match_identity_leak
test_identity_guard_does_not_claim_canonical_event_count
test_phone_output_flat_path_required
```

## Downstream Consumers

The guard should run before:

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

## Release Rule

This contract is `SPEC_ONLY` until implementation, tests and ACTIVE_MATCH execution produce flat outputs and a runtime evidence ledger entry.
