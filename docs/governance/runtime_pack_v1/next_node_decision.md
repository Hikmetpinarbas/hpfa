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
Fitness Signal PDF Support Lite
Fitness-Tactical Integration Bridge Lite V1
```

The next correct product node is:

```text
Event Identity Resolution Gate Lite V1
```

Primary Event Surface Gate remains next after Event Identity Resolution.

## Reason

HPFA development must not leave hidden gaps between modules.

P2S corrected surface inventory semantics.

P2D converted large row counts into analyst-safe surface inventory language.

P3 bound team and player identity surfaces while preserving event-count unknowns.

The newly recognized blocking gap is:

```text
cross_surface_event_identity=UNRESOLVED
```

A single football action may appear in both team-level and player-level surfaces. Therefore metric counting, primary surface selection, phase, possession and sequence work must not assume that surface rows are unique actions.

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

P2D evidence:

```text
status=PASS
claim_safety=ANALYST_SAFE_SURFACE_COUNT_LANGUAGE_ONLY
pattern_structure_status=NOT_BUILT_REQUIRES_LATER_GATES
surface_row_inventory_total=15516
```

P3 evidence:

```text
status=PASS
claim_safety=IDENTITY_BINDING_ONLY
team_entity_count=2
player_entity_count=32
unresolved_team_rows=11836
surface_row_inventory_total=15516
event_count_claim_allowed=False
```

Bridge evidence:

```text
status=PASS
candidate_count=2
event_count_claim_allowed=false
```

## Analyst Evidence

The analyst now has:

- readable multi-surface row inventory;
- surface role row counts;
- team/player identity binding;
- unresolved identity row count;
- analyst-safe count language;
- cross-surface support review candidates.

The analyst still does not have:

- cross-surface event identity resolution;
- selected primary event surface;
- deduplicated event count;
- phase truth;
- possession truth;
- sequence truth;
- pattern structure truth.

## Current ACTIVE_MATCH Safe Surface Reading

```text
ACTIVE_MATCH contains 15,516 readable multi-surface rows.
This is not a deduplicated event count.
The same underlying football action may appear in more than one surface.
Event identity resolution is required before metric counting or primary surface selection.
```

## Active Blocking Gaps

See:

```text
docs/governance/runtime_pack_v1/development_gap_register.md
```

Highest priority gap:

```text
G1 Cross-Surface Event Identity / Deduplication Gap
```

## Next Executable Step

Implement:

```text
Event Identity Resolution Gate Lite V1
```

Recommended contract path already written:

```text
docs/contracts/event_identity_resolution_gate_lite_v1.md
```

Recommended module path:

```text
hpfa/modules/core/event_identity_resolution_gate_lite/src/event_identity_resolution_gate.py
```

Recommended tests:

```text
hpfa/modules/core/event_identity_resolution_gate_lite/tests/test_event_identity_resolution_gate.py
```

Recommended outputs:

```text
/storage/emulated/0/Download/HPFA/event_identity_resolution_gate_lite_v1.json
/storage/emulated/0/Download/HPFA/event_identity_resolution_gate_lite_v1.txt
```

## Decision Result

```text
P1_ACTIVE_MATCH_EVIDENCE_PASS
P2S_ACTIVE_MATCH_EVIDENCE_PASS
P2B_ACTIVE_MATCH_EVIDENCE_PASS
P2D_ACTIVE_MATCH_EVIDENCE_PASS
P3_ACTIVE_MATCH_EVIDENCE_PASS
FITNESS_PDF_SUPPORT_ACTIVE_MATCH_EVIDENCE_PASS
FITNESS_TACTICAL_BRIDGE_ACTIVE_MATCH_EVIDENCE_PASS
EVENT_IDENTITY_RESOLUTION_GATE_NEXT_PRODUCT_NODE
PRIMARY_EVENT_SURFACE_GATE_WAIT
TIME_PHASE_WAIT
POSSESSION_WAIT
SEQUENCE_WAIT
RHYTHM_IMPLEMENTATION_DEFERRED
PRODUCTION_RELEASE_NOT_GRANTED
```

This file is governance evidence plus operator-reported ACTIVE_MATCH evidence summary. It is not PRODUCTION_RELEASE by itself.
