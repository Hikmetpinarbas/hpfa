# HPFA Event Identity Resolution Gate Lite V1 Contract

Date: 2026-06-23

Status: SPEC_WRITTEN

## Product Node

```text
Event Identity Resolution Gate Lite V1
```

## Purpose

Detect cross-surface duplicate-risk candidates where one underlying football action may appear in multiple ACTIVE_MATCH surfaces.

This gate prevents repeated metric counting before primary event surface selection, temporal ordering, possession, sequence or pattern modules.

## Why This Gate Exists

Current ACTIVE_MATCH evidence shows readable multi-surface inventory:

```text
surface_row_inventory_total=15516
surface_role_row_counts={goalkeepers:390, players:6986, teams:8140}
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
```

A single football action may appear in:

```text
Players surface
Teams surface
Goalkeepers surface
```

Therefore metrics must not sum across surfaces before event identity resolution.

## Donor / Reference Support

GitHub canonical schema donor:

```text
configs/hpfa_canon/HPFA_Canonical_Event_Schema_v0.1.yaml
```

Relevant donor concepts:

```text
deterministic event_id from content
composite primary key
collision handling
match_id + temporal field + event_type + player/team + coordinate inputs
```

Drive donor support:

```text
canonicalization and deduplication
unique event identifiers
provenance tracking
identity resolution
redundant telemetry removal
```

These sources are donor/support only. ACTIVE_MATCH runtime remains the only match truth.

## Required Inputs

Preferred inputs:

```text
canonical_event_lite_v1.json
canonical_event_lite_audit_v1.json
team_binding_lite_audit_v1.json
surface_inventory_interpretation_gate_lite_v1.json
```

## Outputs

Flat phone output only:

```text
event_identity_resolution_gate_lite_v1.json
event_identity_resolution_gate_lite_v1.txt
```

## Output Sections

The output should include:

- module_id
- status
- claim_safety
- candidate_cluster_count
- duplicate_risk_candidate_count
- duplicate_cluster_candidates
- fingerprint_strategy
- unresolved_reason
- event_count_claim_allowed
- deduplicated_event_count
- blocked_claims
- required_next_gates

## Fingerprint Strategy

The gate may compute deterministic candidate fingerprints using available fields only:

```text
source_role
source_format
event_family
team_normalized
player_raw
x_meters rounded or bucketed
y_meters rounded or bucketed
minute/timestamp fields if available
source_row_index for provenance only
```

Because current surfaces have incomplete temporal fields, fingerprints are duplicate-risk evidence only.

## Similarity Strategy

Allowed candidate matching signals:

```text
same or compatible event_family
same team_normalized if available
same player_raw if available
near coordinate bucket if available
near time bucket if available
source roles differ
source rows are from same ACTIVE_MATCH
```

If time is missing, the gate must lower confidence.

If player/team fields are missing, the gate must lower confidence.

If candidate evidence is insufficient, return unresolved.

## Decision Values

Allowed decision values:

```text
DUPLICATE_RISK_CANDIDATES_FOUND
NO_DUPLICATE_RISK_CANDIDATES_FOUND
UNRESOLVED_INSUFFICIENT_FIELDS
FAIL_CLOSED
```

## Claim Boundary

Allowed language:

```text
duplicate-risk candidate
possible cross-surface representation of the same action
requires primary event surface gate
requires temporal validation
requires analyst validation
```

Blocked language:

```text
confirmed duplicate event
deduplicated event truth
validated event count
deduplicated event count
primary event stream
metric count allowed
```

## Acceptance Criteria

This node can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. contract exists;
2. module compiles;
3. tests pass;
4. ACTIVE_MATCH run writes flat outputs;
5. candidate fingerprint logic is deterministic;
6. duplicate-risk candidates include provenance for all source rows;
7. incomplete-field cases remain unresolved or low-confidence;
8. deduplicated_event_count remains UNKNOWN;
9. canonical_event_count remains UNKNOWN;
10. event_count_claim_allowed remains false;
11. no metric count is unlocked.

## Downstream Rule

Primary Event Surface Gate must consume this output.

If duplicate-risk candidates are present or unresolved:

```text
primary_event_surface_candidate may still be selected for downstream review,
but event_count_claim_allowed must remain false.
```

If fields are insufficient:

```text
phase, possession, sequence and metric count claims remain blocked.
```

## Current Status

```text
SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
