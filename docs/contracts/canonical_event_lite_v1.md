# HPFA Canonical Event Lite V1 Contract

Date: 2026-06-22

Status: P2_CONTRACT_SPEC

## Product Node

```text
P2 Canonical Event Lite V1
```

## Purpose

Canonical Event Lite V1 converts readable ACTIVE_MATCH CSV/XML/XLSX surfaces into a normalized event-lite table without claiming complete event truth.

P2 exists because P1 successfully produced an ACTIVE_MATCH analyst report but surfaced a data-dictionary gap:

```text
zone_distribution=UNKNOWN 100.0%
channel_distribution=UNKNOWN 100.0%
```

P2 must solve column discovery, event-family normalization, team label normalization and coordinate extraction.

## Source Authority

Runtime match truth:

```text
runtime/active_single_match/current
```

GitHub donor support:

- HP-Motor provides CSV/XLSX table loading pattern through `hp_motor.ingest.loader.load_table`.
- HP-Motor pipeline shows all event CSV sources should be loaded and concatenated, while other CSV/XLSX/XML-like surfaces can be loaded for schema and validation support.

Donor rule:

```text
ADAPT_NOT_COPY
```

P2 must adapt donor capability into HPFA product code. It must not import HP-Motor as runtime dependency.

## Inputs

Required:

- `active_match_dir`
- `--out-dir`

Allowed output roots for user-visible phone output:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must be rejected.

## Outputs

P2 must write:

```text
canonical_event_lite_v1.json
canonical_event_lite_v1.tsv
canonical_event_lite_audit_v1.json
canonical_event_lite_audit_v1.txt
```

All outputs must be flat under the selected output root.

## Non-Goal

P2 does not create full canonical event truth.

Before validation completes:

```text
canonical_event_count = UNKNOWN
```

P2 may produce:

```text
canonical_lite_row_count
```

P2 must not produce:

- canonical event count as complete match truth
- validated event stream truth
- possession truth
- phase truth
- tactical truth
- off-ball truth
- dominance truth

## Required Reader Capabilities

### CSV

P2 must read CSV with delimiter detection.

Supported delimiters:

- comma
- semicolon
- tab
- pipe

Encoding fallback:

- utf-8-sig
- utf-8 with ignore

### XLSX

P2 must read XLSX as aggregate or validation surface.

XLSX may support:

- player aggregate validation
- goalkeeper aggregate validation
- schema discovery
- later metric binding

P2 must not treat XLSX aggregate rows as event truth.

### XML

P2 must read XML event-like nodes.

Supported node names:

- instance
- event
- row
- action

P2 must flatten node attributes and immediate child text into row dictionaries.

XML rows are event-like rows, not validated canonical events.

## Column Synonym Registry

P2 must detect columns by normalized synonyms.

### event_type

Synonyms:

- action
- Action
- event
- Event
- event_type
- Event Type
- type
- Type
- name
- Name
- title
- Title
- label
- Label
- action_name
- Action Name

### team

Synonyms:

- team
- Team
- team_name
- Team Name
- squad
- Squad
- club
- Club
- side
- Side
- participant
- Participant
- team_id
- Team ID

### player

Synonyms:

- player
- Player
- player_name
- Player Name
- athlete
- Athlete
- name
- Name

### time

Synonyms:

- minute
- Minute
- min
- Min
- second
- Second
- time
- Time
- timestamp
- Timestamp
- match_time
- Match Time
- period
- Period

### coordinates

x synonyms:

- x
- X
- start_x
- Start X
- x1
- X1
- x_coord
- X Coord
- x_coordinate
- X Coordinate
- location_x
- Location X
- pos_x
- Pos X
- coord_x
- Coord X

 y synonyms:

- y
- Y
- start_y
- Start Y
- y1
- Y1
- y_coord
- Y Coord
- y_coordinate
- Y Coordinate
- location_y
- Location Y
- pos_y
- Pos Y
- coord_y
- Coord Y

P2 must also support fuzzy normalized header matching:

- lower-case
- trim whitespace
- replace spaces, hyphens, dots and slashes with underscore
- remove repeated underscores

## Canonical Lite Schema

Each canonical-lite row should contain:

- source_file
- source_format
- source_role
- source_row_index
- event_type_raw
- event_family
- team_raw
- team_normalized
- player_raw
- minute_raw
- second_raw
- timestamp_raw
- x_raw
- y_raw
- x_meters
- y_meters
- zone
- channel
- row_claim_safety
- row_warnings

## Coordinate Policy

Coordinate values must be numeric to produce zones/channels.

Expected pitch scale:

```text
x in [0, 105]
y in [0, 68]
```

If values appear normalized to 0-1 or 0-100, P2 must preserve raw value and add a warning unless conversion policy is explicit.

Zone buckets:

- DEFENSIVE_THIRD
- MIDDLE_THIRD
- FINAL_THIRD
- UNKNOWN

Channel buckets:

- LEFT_CHANNEL
- CENTRAL_CHANNEL
- RIGHT_CHANNEL
- UNKNOWN

## Event Family Policy

P2 must map raw labels into Lite event families:

- PASS
- SHOT
- DUEL_PRESSURE
- CARRY_DRIBBLE
- BALL_LOSS
- RECOVERY
- FOUL
- GOALKEEPER_RESTART
- POSITIONAL_ATTACK_SIGNAL
- UNKNOWN_OR_OTHER

Raw labels must be preserved.

## Team Label Policy

P2 may normalize team labels by exact string cleanup only:

- trim whitespace
- collapse repeated spaces
- preserve numeric id if embedded

P2 must not infer team identity from filename when row-level team field is missing. It may report file-level hints separately.

## Audit Requirements

P2 audit must report:

- files read
- rows read by file
- canonical-lite rows emitted
- columns detected by source
- missing column families
- coordinate coverage
- team coverage
- event_type coverage
- zone/channel coverage
- warnings
- claim boundary

## Acceptance Criteria

P2 can reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. module compiles;
2. tests pass;
3. ACTIVE_MATCH execution writes all four flat output files;
4. CSV/XML/XLSX readers report schema coverage;
5. canonical_event_count remains UNKNOWN unless validation policy is upgraded later;
6. coordinate coverage is reported honestly;
7. no forbidden football claim is emitted.

## Current Status

```text
P2_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
```
