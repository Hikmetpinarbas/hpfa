# P2C XML-CSV Temporal-Spatial Binder Lite V1

Status: SPEC_ONLY / REVIEW_REQUIRED

Linked issue: #85

## Purpose

P2C defines the first HPFA Event-Time-Space fusion layer.

It binds CSV spatial event/action evidence with XML temporal/action conformance evidence before any sequence, phase, metric primitive, player-role interpretation or professional postmatch sentence is allowed.

P2C is not a report writer. It is an evidence binder.

## Source Authority

Runtime truth remains:

```text
runtime/active_single_match/current
```

Dropbox, Google Drive, donor repos, archive packs, academic sources and historical reports are donor/reference support only.

## Source Roles

### CSV

CSV is the primary candidate event/action spatial surface.

Allowed use:

- team
- player
- action/event label
- x/y coordinate
- half
- event order
- optional start/end if present

Blocked use:

- CSV row count as canonical event count
- CSV duplicate labels as separate event truth
- CSV-only tactical or phase truth

### XML

XML is the temporal/action conformance surface.

Allowed use:

- event id
- start
- end
- duration
- half
- action label
- coordinate fields if present
- event relation / chain identifiers if present

Blocked use:

- XML-only canonical event truth
- XML-only sequence truth without conformance checks

### XLSX / PDF

XLSX and PDF are aggregate validation/support surfaces.

Allowed use:

- xG / xA
- possession
- shot/pass/goalkeeper/player summaries
- phase tables when present
- line-break and pressure aggregate support when present

Blocked use:

- aggregate values overriding event-time-space surface
- aggregate-to-sequence substitution

## Core Output Object

### event_time_space_atom

```json
{
  "event_atom_id": "source-preserved-or-derived",
  "source_csv_row": null,
  "source_xml_event_id": null,
  "team": null,
  "player": null,
  "half": null,
  "start_time": null,
  "end_time": null,
  "duration_sec": null,
  "x": null,
  "y": null,
  "action_labels": [],
  "action_family": "candidate",
  "zone": "candidate",
  "lane": "candidate",
  "third": "candidate",
  "previous_event": null,
  "next_event": null,
  "sequence_id": null,
  "quality_flags": [],
  "claim_boundary": "event_time_space_surface"
}
```

## Candidate Action Moment Grouping

Grouping key:

```text
team + player + start + end + half + pos_x + pos_y
```

Rules:

1. Multiple labels under the same key must be stored in `action_labels`.
2. The grouped object is a candidate action moment, not canonical event truth.
3. The module must preserve source row/id fields.
4. `canonical_event_count` remains `UNKNOWN` unless Canonical Event Lite validates it.

## Required Audit Output

The module must emit a `temporal_spatial_ingestion_audit` with:

- csv_surface_rows
- xml_instance_count
- csv_xml_row_or_id_conformance
- start_end_conformance
- duplicate_action_label_density
- missing_coordinate_count
- missing_team_count
- missing_player_count
- missing_action_count
- source_conflict_count
- canonical_event_count = UNKNOWN

## Allowed Derived Objects

P2C may produce:

- event_time_space_atom
- candidate_action_moment_inventory
- temporal_spatial_ingestion_audit
- csv_xml_conformance_report
- missing_column_report
- source_conflict_report

P2C must not produce:

- possession truth
- sequence truth
- phase truth
- behaviour truth
- pattern truth
- match identity truth
- tactical truth
- dominance/control claims

## Zone/Lane Candidate Tags

P2C may attach candidate tags only:

- defensive_third
- middle_third
- final_third
- left_wing
- left_half_space
- central_lane
- right_half_space
- right_wing
- zone14_corridor
- box
- wide_delivery_zone
- turnover_risk_zone
- shot_generation_zone

## Action Family Candidate Tags

P2C may normalize labels into action families:

- pass
- progressive_pass
- carry
- dribble
- shot
- goal
- assist_or_key_pass
- recovery
- interception
- tackle_or_challenge
- clearance
- lost_ball
- restart_or_set_piece
- cross_or_box_delivery
- goalkeeper_action
- unknown_or_other

## Claim Boundary

Allowed language:

- event-time-space surface shows
- row-level evidence indicates
- temporal conformance supports
- spatial coordinate surface indicates
- candidate action moment
- requires later validation

Blocked language:

- controlled
- dominated
- intended
- tactical plan was
- performance truth
- quality truth
- causality without design evidence
- pitch-control truth
- off-ball structure truth
- body orientation truth

## Phone Output Policy

User-visible Termux outputs must be flat under one of:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must fail closed with:

```text
nested_phone_output_directory_rejected
```

## Required Tests

- `test_csv_xml_time_space_binder_preserves_source_ids`
- `test_candidate_action_moment_groups_duplicate_labels`
- `test_canonical_event_count_unknown_without_canonical_gate`
- `test_aggregate_data_cannot_override_event_surface`
- `test_no_tracking_truth_from_event_only`
- `test_outputs_are_flat_phone_paths`
- `test_nested_phone_output_directory_is_rejected`
- `test_no_sample_match_identity_leak`

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.

P2C is not production release and not full postmatch intelligence.
