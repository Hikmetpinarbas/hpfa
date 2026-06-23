# HPFA Next Node Decision V1

Date: 2026-06-23

Status: GAP_DRIVEN_NEXT_NODE_DECISION

## Decision

The completed evidence-pass nodes are:

```text
P1 ACTIVE_MATCH Analyst Report Lite V1
P2S Canonical Event Lite Surface Count Correction
P2B Reference Document Ingest Lite V1
P2D Surface Inventory Interpretation Gate Lite V1
P3 Team Binding Lite V1
Event Identity Resolution Gate Lite V1
Fitness Signal PDF Support Lite
Fitness-Tactical Integration Bridge Lite V1
```

The next correct support/product boundary node is:

```text
P2D Event Physical Cost Surface Lite V1
```

Primary Event Surface Gate remains waiting until event identity and physical-cost/report boundaries are explicit.

## Reason

HPFA development must not leave hidden gaps between modules.

P2S corrected surface inventory semantics.

P2D Surface Inventory Interpretation converted large row counts into analyst-safe surface inventory language.

P3 bound team and player identity surfaces while preserving event-count unknowns.

Event Identity Resolution detected cross-surface duplicate-risk candidates while preserving deduplicated_event_count=UNKNOWN and metric_count_allowed=false.

The newly recognized support boundary is:

```text
physical_cost_surface != event_surface
report_metric_surface != event_surface
```

Fitness files, form reports, FIFA reports and match reports must not enter event counting, duplicate-risk resolution or primary event surface selection as event rows.

## Runtime Evidence Summary

P2S evidence:

```text
py_compile PASS
pytest 5 passed
ACTIVE_MATCH run PASS
surface_row_inventory_total=15516
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=False
```

Event Identity Resolution evidence:

```text
pytest 7 passed
ACTIVE_MATCH run PASS
decision=DUPLICATE_RISK_CANDIDATES_FOUND
candidate_cluster_count=25
duplicate_risk_candidate_count=134
unresolved_candidate_count=8102
deduplicated_event_count=UNKNOWN
metric_count_allowed=false
```

P2D Physical Cost boundary target:

```text
physical-cost and report surfaces classified separately
runtime_event_truth=false
event_count_claim_allowed=false
metric_count_allowed=false
```

## Analyst Evidence

The analyst now has:

- readable multi-surface row inventory;
- team/player identity binding;
- duplicate-risk candidate clusters;
- fitness/report PDF availability;
- reference text extraction evidence.

The analyst still does not have:

- selected primary event surface;
- deduplicated event count;
- event-bound physical cost;
- phase truth;
- possession truth;
- sequence truth;
- pattern structure truth.

## Current ACTIVE_MATCH Safe Surface Reading

```text
ACTIVE_MATCH contains readable multi-surface row inventory and duplicate-risk candidate evidence. Fitness/FIFA/form/match reports are support surfaces, not event surfaces. Physical-cost metrics can be reviewed beside event evidence only after explicit support-boundary and claim gates.
```

## Active Blocking Gaps

See:

```text
docs/governance/runtime_pack_v1/development_gap_register.md
```

Highest priority support boundary:

```text
physical_cost_surface != event_surface
report_metric_surface != event_surface
```

## Next Executable Step

Implement and run:

```text
P2D Event Physical Cost Surface Lite V1
```

Contract path:

```text
docs/contracts/event_physical_cost_surface_lite_v1.md
```

Module path:

```text
hpfa/modules/support/event_physical_cost_surface_lite/src/event_physical_cost_surface.py
```

Tests:

```text
hpfa/modules/support/event_physical_cost_surface_lite/tests/test_event_physical_cost_surface.py
```

Outputs:

```text
/storage/emulated/0/Download/HPFA/physical_cost_surface_manifest_v1.json
/storage/emulated/0/Download/HPFA/physical_cost_metric_extract_v1.tsv
/storage/emulated/0/Download/HPFA/physical_cost_surface_audit_v1.json
/storage/emulated/0/Download/HPFA/physical_cost_surface_audit_v1.txt
```

## Decision Result

```text
P1_ACTIVE_MATCH_EVIDENCE_PASS
P2S_ACTIVE_MATCH_EVIDENCE_PASS
P2B_ACTIVE_MATCH_EVIDENCE_PASS
P2D_SURFACE_INVENTORY_ACTIVE_MATCH_EVIDENCE_PASS
P3_ACTIVE_MATCH_EVIDENCE_PASS
EVENT_IDENTITY_RESOLUTION_ACTIVE_MATCH_EVIDENCE_PASS
EVENT_PHYSICAL_COST_SURFACE_NEXT_SUPPORT_NODE
PRIMARY_EVENT_SURFACE_GATE_WAIT
TIME_PHASE_WAIT
POSSESSION_WAIT
SEQUENCE_WAIT
RHYTHM_IMPLEMENTATION_DEFERRED
PRODUCTION_RELEASE_NOT_GRANTED
```

This file is governance evidence plus operator-reported ACTIVE_MATCH evidence summary. It is not PRODUCTION_RELEASE by itself.
