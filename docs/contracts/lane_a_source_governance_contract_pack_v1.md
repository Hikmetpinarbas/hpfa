# HPFA Lane A Source Governance Contract Pack V1

Status: SPEC_ONLY
Release status: REVIEW_REQUIRED
Product authority: hpfa
Runtime authority: runtime/active_single_match/current
Claim safety: SOURCE_GOVERNANCE_CONTRACT_ONLY

This document defines the first modernization contract pack for Lane A: Canonical Surface and Source Governance.

It is not executable product code and does not create runtime match truth.

## Step gain record

```json
{
  "step_id": "LANE_A_SOURCE_GOVERNANCE_CONTRACT_PACK_V1",
  "source_repo": "HP-Motor-main|HP-Motor",
  "source_role": "GITHUB_DONOR_REPO",
  "target_hpfa_module": "source_governance_contract_pack",
  "engineering_gain": [
    "data quality gate contract",
    "gate report consumer compatibility requirement",
    "no silent drop audit contract",
    "source mapping registry contract",
    "duplicate risk blocker contract",
    "coordinate boundary gate contract",
    "temporal consistency gate contract",
    "team identity gate contract"
  ],
  "analyst_gain": [
    "the analyst can see which surface rows are readable before football interpretation",
    "missing fields and source conflicts become visible",
    "event-like rows are preserved as surface evidence without event-count truth",
    "downstream policy consumers can read the gate output without bypass"
  ],
  "new_blockers": [
    "ACTIVE_MATCH runtime execution required",
    "canonical_event_count remains UNKNOWN",
    "event_count_claim_allowed remains false",
    "Data Quality Gate Lite output must remain compatible with Gate Report Consumer"
  ],
  "claim_boundary_change": "none",
  "runtime_evidence_required": true,
  "release_status": "REVIEW_REQUIRED"
}
```

## Donor basis

Allowed donor use:

- HP-Motor-main canonical schema discipline
- HP-Motor-main gate policy concepts
- HP-Motor-main canon index concept
- HP-Motor vendor mapping and normalizer concepts

Blocked donor use:

- direct source copy
- donor runtime truth
- donor release truth
- canonical event count truth

## Existing consumer compatibility rule

Data Quality Gate Lite must not bypass the existing Gate Report Consumer.

Any `data_quality_gate_lite_v1.json` emitted by future executable work must include the fields required by the current gate report reader and keep compatible semantics:

```text
tool
status
input
input_format
row_count
valid_row_count
claim_safety
authority_note
next_action
findings
```

Required status values for the consumer-compatible envelope:

```text
PASS
DEGRADED
FAIL_CLOSED
```

Required `claim_safety` value for the consumer-compatible envelope:

```text
NO_FOOTBALL_CLAIMS_EMITTED
```

Required `next_action` keys:

```text
phase_sequence_allowed
metric_layer_allowed
claim_layer_allowed
reason
```

`findings` must be a non-empty list.

HPFA-specific Lane A fields may be added as extensions, but the consumer-compatible envelope is mandatory.

## Contract A1 — Data Quality Gate Lite V1

Purpose:

Validate whether ACTIVE_MATCH surface rows can be used as row-level surface evidence.

Inputs:

- active match surface files
- source mapping output
- source conflict registry output
- active match identity guard output

Outputs:

- data_quality_gate_lite_v1.json
- data_quality_gate_lite_v1.txt

Required consumer-compatible fields in JSON output:

- tool
- status
- input
- input_format
- row_count
- valid_row_count
- claim_safety
- authority_note
- next_action
- findings

Required Lane A extension fields in JSON output:

- module_id
- decision
- surface_file_count
- readable_surface_count
- blocked_surface_count
- missing_required_field_report
- duplicate_risk_report
- coordinate_boundary_report
- temporal_consistency_report
- team_identity_report
- claim_boundary
- outputs

Consumer-compatible status mapping:

- DATA_QUALITY_CANDIDATE_ONLY -> DEGRADED
- FAIL_CLOSED_MISSING_ACTIVE_MATCH -> FAIL_CLOSED
- REVIEW_REQUIRED_SOURCE_CONFLICTS -> DEGRADED
- REVIEW_REQUIRED_MISSING_REQUIRED_FIELDS -> DEGRADED

Decisions:

- DATA_QUALITY_CANDIDATE_ONLY
- FAIL_CLOSED_MISSING_ACTIVE_MATCH
- REVIEW_REQUIRED_SOURCE_CONFLICTS
- REVIEW_REQUIRED_MISSING_REQUIRED_FIELDS

Required `next_action` policy:

```json
{
  "phase_sequence_allowed": false,
  "metric_layer_allowed": false,
  "claim_layer_allowed": false,
  "reason": "SOURCE_GOVERNANCE_REVIEW_REQUIRED"
}
```

Required first finding when no stronger gate finding exists:

```json
{
  "gate_id": "LANE_A_DATA_QUALITY_GATE_LITE_V1",
  "status": "DEGRADED",
  "message": "Data quality gate emits row-level surface evidence only; downstream truth layers remain blocked.",
  "evidence": {
    "canonical_event_count": "UNKNOWN",
    "event_count_claim_allowed": false
  }
}
```

Claim boundary:

- no canonical event count
- no complete event truth
- no phase truth
- no possession truth
- no sequence truth
- no tactical truth

## Contract A2 — No Silent Drop Audit Lite V1

Purpose:

Ensure HPFA never hides surface rows removed, skipped, unreadable, malformed or blocked.

Inputs:

- active match surface inventory
- source mapping output
- data quality gate output

Outputs:

- no_silent_drop_audit_lite_v1.json
- no_silent_drop_audit_lite_v1.txt

Required fields in output:

- surface_rows_seen
- surface_rows_readable
- surface_rows_blocked
- surface_rows_unreadable
- surface_rows_skipped
- skipped_reason_counts
- blocked_reason_counts
- source_file_breakdown
- row_preservation_status

Decisions:

- ROW_PRESERVATION_AUDIT_ONLY
- REVIEW_REQUIRED_ROWS_BLOCKED
- FAIL_CLOSED_UNEXPLAINED_DROP

Claim boundary:

- surface_rows is allowed
- visible rows is allowed
- event-like rows is allowed
- canonical event count is blocked

## Contract A3 — Source Mapping Registry Lite V1

Purpose:

Normalize source column aliases into HPFA candidate fields without claiming event truth.

Candidate fields:

- source_file
- source_role
- source_format
- team_candidate
- player_candidate
- action_candidate
- time_candidate
- period_candidate
- x_candidate
- y_candidate
- outcome_candidate
- restart_candidate
- card_candidate
- goal_candidate

Outputs:

- source_mapping_registry_lite_v1.json
- source_mapping_registry_lite_v1.txt

Decisions:

- SOURCE_MAPPING_CANDIDATE_ONLY
- REVIEW_REQUIRED_UNMAPPED_REQUIRED_FIELD
- FAIL_CLOSED_NO_READABLE_SURFACE

Claim boundary:

- mapped column does not become truth
- vendor field does not become canonical field truth
- possession_id, sequence_id and phase fields remain candidate-only if present

## Contract A4 — Duplicate Risk Gate Lite V1

Purpose:

Detect duplicate or near-duplicate row candidates without creating deduplicated event truth.

Outputs:

- duplicate_risk_gate_lite_v1.json
- duplicate_risk_gate_lite_v1.txt

Required fields:

- duplicate_cluster_count
- duplicate_candidate_row_count
- duplicate_risk_level
- duplicate_keys_used
- review_required_clusters_sample

Claim boundary:

- deduplicated_event_count remains UNKNOWN
- duplicate risk evidence does not create canonical event count

## Contract A5 — Coordinate Boundary Gate Lite V1

Purpose:

Check whether coordinate evidence stays inside accepted pitch bounds.

Accepted candidate systems:

- 105x68 physical meters
- 0-100 normalized percentage

Outputs:

- coordinate_boundary_gate_lite_v1.json
- coordinate_boundary_gate_lite_v1.txt

Required fields:

- coordinate_system_candidate
- coordinate_rows_seen
- coordinate_rows_inside_bounds
- coordinate_rows_out_of_bounds
- coordinate_boundary_status
- out_of_bounds_sample

Claim boundary:

- coordinate evidence is surface location only
- no pitch control truth
- no attacking-direction truth without separate gate

## Contract A6 — Temporal Consistency Gate Lite V1

Purpose:

Check candidate time order, period values and backward-jump risk.

Outputs:

- temporal_consistency_gate_lite_v1.json
- temporal_consistency_gate_lite_v1.txt

Required fields:

- time_rows_seen
- period_candidate_counts
- backward_jump_count
- non_numeric_time_count
- temporal_status
- time_truth_allowed

Claim boundary:

- time context candidate only
- no phase truth
- no possession truth
- no sequence truth

## Contract A7 — Team Identity Gate Lite V1

Purpose:

Check whether team labels are usable as candidate team surface evidence.

Outputs:

- team_identity_gate_lite_v1.json
- team_identity_gate_lite_v1.txt

Required fields:

- team_labels_seen
- unknown_team_row_count
- multi_team_player_risk_count
- team_identity_status
- team_truth_allowed

Claim boundary:

- team label evidence is candidate-only until binding allows it
- no production binding without active match identity guard

## Required tests

- test_data_quality_gate_blocks_missing_active_match
- test_data_quality_gate_reports_missing_required_fields
- test_data_quality_gate_output_is_gate_report_consumer_compatible
- test_data_quality_gate_next_action_blocks_downstream_truth_layers
- test_data_quality_gate_findings_non_empty
- test_no_silent_drop_reports_all_skipped_rows
- test_no_silent_drop_fail_closed_on_unexplained_drop
- test_source_mapping_registry_keeps_fields_candidate_only
- test_duplicate_risk_does_not_create_deduplicated_count
- test_coordinate_boundary_blocks_out_of_bounds_spatial_truth
- test_temporal_consistency_blocks_backward_jump_time_truth
- test_team_identity_conflict_blocks_production_binding
- test_no_canonical_event_count_claim

## Output policy

All user-visible Termux outputs must be flat under:

- /sdcard/Download/HPFA
- /storage/emulated/0/Download/HPFA

Nested output directories under these roots must be rejected with:

```text
nested_phone_output_directory_rejected
```

## Release rule

This pack is SPEC_ONLY. Each module must later provide executable code, tests, ACTIVE_MATCH runtime evidence and football output audit before any stronger status is allowed.
