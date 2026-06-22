# HPFA Canonical Ingest Surface Manifest V1

Status: executable candidate  
Runtime authority: ACTIVE_MATCH raw folder only  
Claim layer: CLOSED  
Report language: CLOSED

## Purpose

This module inventories an ACTIVE_MATCH raw folder before canonical event construction.

It does not create true events. It does not merge CSV/XML/XLSX rows into an event stream. It records the surface evidence family so downstream modules cannot confuse provider rows, XML instances, and aggregate XLSX tables with validated football events.

## Surface families

Expected ACTIVE_MATCH family:

```txt
Players.csv
Teams.csv
Goalkeepers.csv
Players.xml
Teams.xml
Goalkeepers.xml
Players.xlsx
Goalkeepers.xlsx
```

## Product meaning

This is the match-data registration desk.

It tells HPFA:

- which source files exist
- which role each file has: players, teams, goalkeepers
- which format each file has: csv, xml, xlsx
- how many surface rows/instances are visible
- that canonical_event_count is still UNKNOWN
- that XLSX is aggregate validation surface, not event surface

## Boundary

Allowed output:

```txt
surface inventory
surface_row_count
source_file_role
source_format
aggregate_surface flag
canonical_event_count=UNKNOWN
claim_safety=EVIDENCE_ONLY
```

Blocked output:

```txt
true event count
true event stream
tactical truth
dominance truth
pitch-control truth
off-ball truth
fatigue truth
coach intention
report-language claims
```

## Next consumer

Data Quality Gate and downstream postmatch modules may use this manifest to preserve authority and surface lineage.
