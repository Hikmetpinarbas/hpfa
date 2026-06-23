# HPFA Multiversion Donor Rebuild Plan

Date: 2026-06-23

Status: PLAN_ACTIVE

## Purpose

Rebuild useful donor capabilities inside the main `hpfa` product repository without copying donor code directly.

This plan applies first to:

```text
Event Identity Resolution Gate Lite V1
```

## Core Rule

```text
ADAPT_NOT_COPY
```

Donor repos, Drive, Dropbox and academic sources can provide capability patterns only.

Only the `hpfa` product repo can contain executable HPFA product modules.

Only ACTIVE_MATCH runtime can provide match evidence.

## Donor Capabilities Identified

### D1 Canonical Schema / Deterministic Event Identity

Source:

```text
configs/hpfa_canon/HPFA_Canonical_Event_Schema_v0.1.yaml
```

Reusable capability:

```text
composite primary key
deterministic event id from content
hash input list
collision handling
period/time/event/player/coordinate fields
```

HPFA rebuild use:

```text
V0_EXACT_FINGERPRINT
V1_BUCKETED_FINGERPRINT
```

Boundary:

```text
candidate fingerprint only; not deduplicated event truth
```

### D2 Source Role Governance

Source:

```text
docs/governance/runtime_pack_v1/source_role_registry.json
```

Reusable capability:

```text
ACTIVE_MATCH_RUNTIME_AUTHORITY
GITHUB_DONOR_REPO
DRIVE_DONOR_LIBRARY
DROPBOX_DONOR_LIBRARY
ACADEMIC_SUPPORT
```

HPFA rebuild use:

```text
source authority preserved in every candidate cluster
runtime truth never comes from donor/reference sources
```

Boundary:

```text
donor methods do not create match truth
```

### D3 Drive Canonicalization / Dedup Support

Source role:

```text
DRIVE_GOVERNANCE / DRIVE_DONOR_LIBRARY
```

Reusable capability:

```text
canonicalization
deduplication
unique identifiers
provenance tracking
identity resolution
redundant telemetry cleanup
```

HPFA rebuild use:

```text
V2_PROVENANCE_CLUSTER
```

Boundary:

```text
reference-only; not executable truth
```

### D4 Academic Dedup / Entity Resolution Support

Source role:

```text
ACADEMIC_SUPPORT
```

Reusable capability:

```text
record linkage
entity resolution
duplicate-risk detection
active review of uncertain pairs
```

HPFA rebuild use:

```text
review queue for duplicate-risk candidates
confidence bands
fail-closed unresolved state
```

Boundary:

```text
method context only; no football truth from papers
```

## Multiversion Strategy

The main repo will expose multiple strategies inside one product module:

```text
V0_EXACT_FINGERPRINT
V1_BUCKETED_SPATIOTEMPORAL_FINGERPRINT
V2_PROVENANCE_CLUSTER_REVIEW
V3_FAIL_CLOSED_UNRESOLVED
```

### V0 Exact Fingerprint

Uses fields when available:

```text
event_family
team_normalized
player_raw
x_meters
y_meters
minute/timestamp if available
```

Result:

```text
exact duplicate-risk candidate only if fields match exactly after normalization
```

### V1 Bucketed Fingerprint

Uses rounded/bucketed fields:

```text
event_family
team bucket
player bucket
coordinate bucket
period/time bucket if available
```

Result:

```text
near duplicate-risk candidate
```

### V2 Provenance Cluster Review

Groups same or similar evidence across source roles:

```text
players surface
teams surface
goalkeepers surface
aggregate support surface
```

Result:

```text
review cluster with all source row provenance
```

### V3 Fail-Closed Unresolved

If enough fields are missing:

```text
UNRESOLVED_INSUFFICIENT_FIELDS
```

Result:

```text
no deduplicated event count
no metric count unlock
```

## Required Outputs

```text
event_identity_resolution_gate_lite_v1.json
event_identity_resolution_gate_lite_v1.txt
```

Must include:

```text
strategy_versions
candidate_cluster_count
duplicate_risk_candidate_count
unresolved_candidate_count
deduplicated_event_count=UNKNOWN
canonical_event_count=UNKNOWN
event_count_claim_allowed=false
metric_count_allowed=false
source_row_provenance
```

## Required Tests

```text
test_v0_exact_fingerprint_groups_exact_candidates
test_v1_bucketed_fingerprint_groups_near_candidates
test_v2_preserves_cross_surface_provenance
test_v3_missing_fields_fail_closed
test_no_deduplicated_event_count_claim
test_no_sample_match_identity_leak
test_nested_phone_output_directory_is_rejected
```

## Release Boundary

This module can reach ACTIVE_MATCH_EVIDENCE_PASS if it produces duplicate-risk candidates and preserves claim boundaries.

It cannot reach PRODUCTION_RELEASE until downstream gates consume it safely.

## Current Status

```text
PLAN_ACTIVE
IMPLEMENTATION_NEXT
PRODUCTION_RELEASE_NOT_GRANTED
```
