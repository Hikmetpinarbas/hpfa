# HPFA Phase / Possession / Sequence Composite V1

Status: executable apparatus candidate
Runtime authority: ACTIVE_MATCH only
Boundary: evidence-only output

## Purpose

This module converts an authorized event surface into phase, possession and sequence evidence.

It is not a report generator. It does not open the report-language layer. It produces structured evidence for later metric, progression, value and risk modules.

## Donor basis

This module is adapted from donor behavior, not copied as-is:

- HP-Motor phase tagger: P1-P6 phase taxonomy and rule-based phase tagging.
- HP-Motor possession segmenter: explicit possession_id runs, fallback team-run mode when possession_id is missing.
- HP-Motor sequence segmenter: split possessions by phase and set-piece changes.
- HP-Engine sequence engine: boundary reasons, sequence type, duration, progression_x, passes, shots, duels, carries and recoveries.
- Drive: Phase/Sequence donor discovery and postmatch pipeline governance.
- Dropbox: sequence narration grammar and event-only sequence research folders.
- Sider Scholar: event-to-sequence, possession context, context-aware match analysis and uncertainty-aware event detection support.

## Output files

```txt
phase_events.jsonl
possessions.jsonl
sequences.jsonl
phase_sequence_summary.json
```

## Required upstream gate

If a Data Quality Gate report is supplied, this module must use Gate Report Consumer policy.

- PASS: normal evidence generation.
- DEGRADED: evidence generation only when degraded mode is explicitly enabled.
- FAIL_CLOSED: stop.

The module can run without a gate report only for isolated unit tests or donor inspection. Runtime use must provide a gate report.

## Phase taxonomy

```txt
P1_BUILDUP
P2_PROGRESSION
P3_FINALIZATION
P4_NEG_TRANSITION
P5_ORG_DEFENSE
P6_POS_TRANSITION
```

These are evidence labels, not tactical conclusions.

## Sequence types

```txt
attack_to_shot
transition_attack
direct_attack
sustained_possession
contested_phase
build_up_or_recycle
```

Sequence type is a descriptive event-chain classification. It is not a tactical truth.

## Boundary

Allowed language:

```txt
sequence_id=12 was classified as transition_attack evidence
phase_id=P2_PROGRESSION was assigned from event location/action evidence
possession_authority=FALLBACK_TEAM_RUN means degraded possession segmentation
```

Not allowed from this module alone:

```txt
team controlled the match
team broke the opponent block
team had tactical superiority
coach intended a pattern
```

## First ACTIVE_MATCH target

```txt
runtime/active_single_match/current/*Players.csv
```

The first release target is an evidence pack, not a professional match report.
