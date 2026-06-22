# HPFA ACTIVE_MATCH Analyst Report Lite V1 Contract

Date: 2026-06-22

Status: P1_CONTRACT_SPEC

## Product Node

```text
P1 ACTIVE_MATCH Analyst Report Lite V1
```

## Purpose

Produce a claim-safe analyst-facing report from the ACTIVE_MATCH visible surface.

This is the first analyst report layer after P0A governance. It is not Canonical Event Lite, not Team Binding Lite, not phase truth, not possession truth and not rhythm implementation.

## Runtime Authority

The only runtime match truth source is:

```text
runtime/active_single_match/current
```

Termux example:

```text
/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current
```

Drive, Dropbox, Sider Scholar, donor repos, archives, old reports and samples are not runtime match truth.

## Inputs

Required:

- `active_match_dir`: path to ACTIVE_MATCH runtime directory
- `--out-dir`: output root

Allowed output roots for phone-visible output:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested directories under these roots must be rejected with:

```text
nested_phone_output_directory_rejected
```

## Outputs

P1 must write exactly these flat outputs under the selected output root:

```text
active_match_analyst_report_lite_v1.json
active_match_analyst_report_lite_v1.txt
```

No nested output directory is allowed.

## Required Report Sections

JSON and TXT outputs must include these sections:

1. match snapshot
2. surface inventory
3. action-family volume
4. zone distribution
5. channel distribution
6. team row-volume
7. goalkeeper/restart signal
8. pass/shot/duel/carry/loss/recovery block
9. analyst reading
10. missing-column report
11. technical limits
12. engineering evidence

## Canonical Count Boundary

Before Canonical Event Lite:

```text
canonical_event_count = UNKNOWN
```

P1 must not convert visible rows into canonical event count.

Allowed terms:

- surface rows
- visible rows
- row-level evidence
- event-like rows
- event-row evidence
- action-family volume

Blocked terms:

- canonical event count, unless value is UNKNOWN
- true event stream
- validated event truth
- complete event truth
- thousands of events

## Analyst Language Contract

P1 must speak positively about what the visible surface shows.

Allowed analyst phrases:

- row-level evidence shows
- visible surface evidence indicates
- action-family volume suggests
- coordinate evidence is concentrated in
- this is a candidate
- requires later validation

Blocked analyst phrases:

- dominated
- coach planned
- tactical truth
- pitch control truth
- off-ball structure truth
- body orientation truth
- fatigue truth
- control was lost
- opponent dictated
- press trap truth

## Minimum Analyst Reading

The analyst reading should answer:

- What is visible?
- Where is it visible?
- Which action-family volumes stand out?
- Which zone/channel buckets are concentrated?
- Which team row-volume relationship is visible?
- Which restart/goalkeeper signals are visible?
- What is useful for the analyst without tactical overclaim?

Limits must be in the technical limits section, not repeated as the main report voice.

## Required Evidence Blocks

Engineering evidence must include:

- module id
- status
- active_match_dir
- output root
- output files
- canonical_event_count value
- claim safety level
- missing surfaces / missing columns
- whether nested phone output was rejected if tested

Analyst evidence must include:

- surface inventory summary
- visible action-family volume summary
- visible zone/channel distribution summary
- visible team row-volume summary
- safe analyst interpretation

## Action-Family Grouping

P1 may group labels into these report blocks when visible:

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

Grouping must be transparent and row-level.

## Missing Column Behavior

P1 must not fail hard when optional columns are missing.

It must report:

- missing file
- missing column
- fallback used
- unsupported section skipped

If no reliable team binding exists, P1 may report team row-volume only when team labels are directly visible. It must not create player-quality judgement.

## Test Requirements

Minimum tests before release candidate:

1. module compiles
2. writes JSON and TXT outputs
3. rejects nested phone output root
4. preserves `canonical_event_count = UNKNOWN`
5. uses visible/row-level terminology
6. forbidden claim strings are absent
7. missing columns are reported rather than crashing
8. output files are flat under allowed phone root

## Runtime Acceptance

Example Termux command:

```bash
ACTIVE_MATCH="/data/data/com.termux/files/home/hpfa_claim_integrity/hpfa/runtime/active_single_match/current"
python active_match_analyst_report_lite.py "$ACTIVE_MATCH" --out-dir "/sdcard/Download/HPFA"
ls -la /sdcard/Download/HPFA/active_match_analyst_report_lite_v1.*
```

Runtime status may become:

```text
ACTIVE_MATCH_EVIDENCE_PASS
```

only after ACTIVE_MATCH execution writes both output files and preserves claim boundaries.

## Current Status

```text
P1_CONTRACT_SPEC_WRITTEN
IMPLEMENTATION_NOT_STARTED
ACTIVE_MATCH_EXECUTION_NOT_RUN
PRODUCTION_RELEASE_NOT_GRANTED
```
