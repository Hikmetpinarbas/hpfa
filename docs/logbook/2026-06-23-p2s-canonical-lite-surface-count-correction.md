# HPFA Project Logbook Entry — 2026-06-23

## Session Summary

Session title: P2S Canonical Lite Surface Count Correction

Main product node:

```text
P2 Canonical Event Lite V1
P2S Canonical Lite Surface Count Correction
```

Summary:

- A semantic count issue was identified in Canonical Event Lite.
- Previous `canonical_lite_row_count` represented all readable rows across multiple surfaces.
- That value was at risk of being misread as a match event count.
- P2S changes the audit vocabulary to surface inventory semantics.
- Downstream bridge and team binding modules were updated to use the new semantics.

## Problem

The previous audit field:

```text
canonical_lite_row_count
```

was derived from:

```text
len(rows_out)
```

Rows came from multiple visible surfaces including CSV, XML and XLSX files.

These surfaces can represent different granularity layers. Therefore their rows must not be summed as a match event count.

## Corrected Semantics

New primary fields:

```text
surface_row_inventory_total
deduplicated_event_count=UNKNOWN
canonical_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
surface_role_row_counts
source_surface_row_counts
```

Deprecated compatibility field:

```text
canonical_lite_row_count_deprecated
```

Meaning:

```text
canonical_lite_row_count_deprecated == surface_row_inventory_total
```

It is not an event count.

## Engineering Evidence Written

Updated files:

```text
hpfa/modules/core/canonical_event_lite/src/canonical_event_lite.py
hpfa/modules/core/canonical_event_lite/tests/test_canonical_event_lite.py
hpfa/modules/support/fitness_tactical_bridge_lite/src/fitness_tactical_bridge.py
hpfa/modules/support/fitness_tactical_bridge_lite/tests/test_fitness_tactical_bridge.py
hpfa/modules/core/team_binding_lite/src/team_binding_lite.py
hpfa/modules/core/team_binding_lite/tests/test_team_binding_lite.py
team_binding_lite.py
docs/contracts/canonical_event_lite_v1.md
```

## Analyst Evidence Impact

Correct reading:

```text
ACTIVE_MATCH contains a multi-surface readable row inventory.
This inventory is not a deduplicated event count.
```

Wrong reading now blocked:

```text
multi-surface rows equal match events
```

## Downstream Impact

Fitness-Tactical Bridge Lite now reads:

```text
surface_row_inventory_total
canonical_lite_row_count_deprecated
primary_event_surface_candidate
deduplicated_event_count
event_count_claim_allowed
```

Team Binding Lite now emits:

```text
surface_row_inventory_total
canonical_lite_row_count_deprecated
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
```

## Product Status

Normalized status:

```text
REVIEW_REQUIRED
```

Reason:

- Code and tests were updated in GitHub.
- ACTIVE_MATCH rerun evidence has not yet been attached after the correction.
- Previous P2 ACTIVE_MATCH evidence remains surface coverage evidence, but count semantics are now corrected and require rerun.

Not production release:

```text
PRODUCTION_RELEASE_NOT_GRANTED
```

## Next Correct Step

Run P2S in Termux:

```text
py_compile
pytest canonical_event_lite tests
pytest bridge tests
pytest team_binding_lite tests
ACTIVE_MATCH canonical_event_lite rerun
bridge rerun
team_binding_lite rerun
```

After rerun, promote P2S to ACTIVE_MATCH_EVIDENCE_PASS if fields are present and event-count claim remains blocked.
