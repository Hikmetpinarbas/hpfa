# HPFA Team Binding Lite V1 Contract

Date: 2026-06-22

Status: P3_CONTRACT_SPEC_WRITTEN

## Product Node

```text
P3 Team Binding Lite V1
```

## Purpose

Bind team and player identity surfaces from Canonical Event Lite and aggregate support tables into a claim-safe identity registry.

P3 exists because P2 exposed multiple team label forms in the same ACTIVE_MATCH runtime surface.

Example runtime surface pattern:

```text
Team label with external id
Team label without external id
Unknown / missing team rows
Aggregate rows from XLSX support tables
```

P3 does not create quality, superiority, tactical or possession claims.

## Source Authority

Runtime truth:

```text
runtime/active_single_match/current
```

Preferred upstream flat outputs:

```text
canonical_event_lite_v1.json
canonical_event_lite_audit_v1.json
```

Optional support surfaces:

```text
Goalkeepers.xlsx
Players.xlsx
```

Support surfaces are used for identity/aggregate binding only. They are not event truth.

## Inputs

Required:

```text
--canonical-event-lite-json <path>
--out-dir <flat output root>
```

Allowed output roots:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested phone output directories must be rejected.

## Outputs

Flat phone output only:

```text
team_binding_lite_v1.json
team_binding_lite_audit_v1.json
team_binding_lite_audit_v1.txt
```

## Required Binding Fields

Team entity record should include:

- team_entity_key
- display_label_candidate
- external_ids
- aliases
- visible_rows
- source_files
- source_formats
- event_family_volume
- zone_distribution
- channel_distribution
- unresolved_rows
- claim_boundary

Player binding record may include:

- player_entity_key
- player_label_candidate
- team_entity_key_candidate
- aliases
- source_files
- visible_rows
- aggregate_support_available
- claim_boundary

## Binding Logic

P3 may:

- group labels that only differ by external id suffix;
- preserve all raw aliases;
- preserve all external ids;
- count visible row evidence per entity;
- mark missing or ambiguous team rows as unresolved;
- keep XLSX rows as aggregate support only.

P3 must not:

- infer team quality from row volume;
- infer tactical identity from team label;
- infer possession truth from team row counts;
- infer dominance;
- infer player role truth unless a validated upstream role source exists;
- hardcode match identity, team names, dates, tournaments or sample row counts.

## Match-Agnostic Rule

Product code and tests must not hardcode active match names, team names, tournament names, dates or runtime row counts.

Required test:

```text
test_no_sample_match_identity_leak
```

Synthetic tests must use neutral names such as Alpha and Beta.

## Claim Boundary

Allowed language:

```text
team label evidence is bound
alias evidence is preserved
external id candidate is preserved
row-level team surface is visible
unresolved identity rows require review
```

Blocked language families:

```text
quality claim by identity
possession claim by row count
dominance claim
tactical claim by label
coach intention claim
complete event truth
```

## Acceptance Criteria

P3 may reach ACTIVE_MATCH_EVIDENCE_PASS only if:

1. contract exists;
2. module compiles;
3. tests pass;
4. `test_no_sample_match_identity_leak` passes;
5. ACTIVE_MATCH run writes flat outputs;
6. team aliases and external ids are preserved;
7. unresolved team rows are reported;
8. no blocked claim is emitted;
9. canonical_event_count remains UNKNOWN.

## Current Status

```text
P3_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```

## Next Step

Implement:

```text
hpfa/modules/core/team_binding_lite/src/team_binding_lite.py
```

Root CLI:

```text
team_binding_lite.py
```

Tests:

```text
hpfa/modules/core/team_binding_lite/tests/test_team_binding_lite.py
```
