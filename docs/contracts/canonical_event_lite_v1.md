# HPFA Canonical Event Lite V1 Contract

Date: 2026-06-22

Status: P2S_SURFACE_COUNT_CORRECTION_IMPLEMENTED_EXECUTION_PENDING

## Product Node

```text
P2 Canonical Event Lite V1
P2S Canonical Lite Surface Count Correction
```

## Purpose

Canonical Event Lite V1 converts readable ACTIVE_MATCH CSV/XML/XLSX surfaces into a normalized multi-surface row inventory.

P2S corrects the previous count semantics: rows from Players, Teams, Goalkeepers, XML and XLSX surfaces must not be read as a deduplicated match event count.

## Source Authority

Runtime match truth:

```text
runtime/active_single_match/current
```

Product code may read runtime surfaces, but it must not hardcode match identity, team names, tournament names, dates or sample ids.

## Inputs

Required:

```text
active_match_dir
--out-dir
```

Allowed phone output roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must be rejected.

## Outputs

P2 writes:

```text
canonical_event_lite_v1.json
canonical_event_lite_v1.tsv
canonical_event_lite_audit_v1.json
canonical_event_lite_audit_v1.txt
```

All outputs must be flat under the selected output root.

## Correct Count Semantics

Primary count fields:

```text
surface_row_inventory_total
surface_role_row_counts
source_surface_row_counts
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
primary_event_surface_candidate=UNRESOLVED
event_count_claim_allowed=false
```

Deprecated compatibility field:

```text
canonical_lite_row_count_deprecated
```

Deprecated field rule:

```text
canonical_lite_row_count_deprecated is an alias for surface_row_inventory_total.
It is not a match event count.
```

## Surface Inventory Layer

P2 may read all visible CSV/XML/XLSX surfaces and report:

- rows_read per source file;
- detected columns;
- event_type coverage rows;
- team coverage rows;
- coordinate coverage rows;
- surface_role_row_counts;
- source_surface_row_counts;
- event-family volume over visible surface rows;
- zone/channel distribution over visible surface rows.

This layer answers:

```text
what surfaces are visible?
what columns are readable?
which rows expose event_type/team/coordinate evidence?
```

It does not answer:

```text
how many deduplicated match events occurred?
which surface is the primary event stream?
which row in one surface maps to a row in another surface?
```

## Primary Event Candidate Layer

P2 does not yet select a primary event surface.

Until a dedicated gate is implemented:

```text
primary_event_surface_candidate=UNRESOLVED
deduplicated_event_count=UNKNOWN
event_count_claim_allowed=false
```

A later gate may evaluate Players / Teams / Goalkeepers surfaces, but P2 must not assume one is primary by default.

## Column Synonym Registry

P2 detects columns by normalized synonyms.

### event_type

```text
action
event
event_type
type
name
title
label
action_name
event name
action type
event type
```

### team

```text
team
team_name
squad
club
side
participant
team_id
team id
```

### player

```text
player
player_name
athlete
player id
player_id
```

### coordinates

P2 supports common x/y aliases including:

```text
x
start_x
x1
x_coord
x_coordinate
location_x
pos_x
coord_x
y
start_y
y1
y_coord
y_coordinate
location_y
pos_y
coord_y
```

## Claim Boundary

Allowed language:

```text
surface row inventory
visible row evidence
multi-surface row inventory
coordinate evidence is visible
team label evidence is visible
requires primary event surface gate
```

Blocked language:

```text
multi_surface_rows_as_event_count
deduplicated event count without primary surface gate
complete event truth
possession truth
phase truth
tactical truth
dominance truth
```

## Technical Limits

```text
Players, Teams and Goalkeepers surfaces may represent overlapping or aggregate views.
Rows across surfaces must not be summed as match event count.
XLSX aggregate rows are not event truth.
canonical_event_count remains UNKNOWN.
deduplicated_event_count remains UNKNOWN.
primary_event_surface_candidate remains UNRESOLVED.
```

## Acceptance Criteria

P2S correction requires:

1. module compiles;
2. tests pass;
3. audit exposes `surface_row_inventory_total`;
4. audit exposes `surface_role_row_counts`;
5. audit exposes `deduplicated_event_count=UNKNOWN`;
6. audit exposes `primary_event_surface_candidate=UNRESOLVED`;
7. audit exposes `event_count_claim_allowed=false`;
8. old `canonical_lite_row_count` is not emitted as a main audit field;
9. deprecated alias is clearly marked;
10. no sample match identity leak in product code.

## Current Status

```text
P2S_SURFACE_COUNT_CORRECTION_IMPLEMENTED
ACTIVE_MATCH_EXECUTION_PENDING
PRODUCTION_RELEASE_NOT_GRANTED
```

P2 previous ACTIVE_MATCH execution remains useful as surface coverage evidence, but event-count semantics require rerun with P2S fields.
