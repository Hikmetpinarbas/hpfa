# HPFA Next Node Decision V1

Date: 2026-06-22

Status: P0A_GOVERNANCE_FILE

## Decision

The completed product node is:

```text
P1 ACTIVE_MATCH Analyst Report Lite V1
```

P1 has ACTIVE_MATCH execution evidence.

The next correct product node is:

```text
P2 Canonical Event Lite V1
```

Rhythm implementation must not start before Canonical Event Lite, sequence candidate, signal density gate and claim router exist.

## Reason

P0 runner-flat-out-v1 is closed. The repo has a spine runner, boundary scorer, surface manifest and flat phone-output guard.

P0A Product Governance Runtime Pack V1 files have been written under:

```text
docs/governance/runtime_pack_v1/
```

P1 contract, implementation, root CLI and tests have been written.

Termux operator evidence shows:

```text
py_compile PASS
pytest 4 passed
ACTIVE_MATCH run status PASS
canonical_event_count UNKNOWN
flat phone outputs written
```

Produced outputs:

```text
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt
```

## P1 Evidence Summary

P1 produced:

- match snapshot
- surface inventory
- action-family volume
- zone/channel distribution block
- team row-volume
- goalkeeper/restart signal
- pass/shot/duel/carry/loss/recovery block
- analyst reading
- missing-column report
- technical limits

Observed ACTIVE_MATCH surface evidence:

```text
surface_file_count=8
expected_surface_count=8
canonical_event_count=UNKNOWN
csv_visible_rows_scanned=7725
PASS=3708
GOALKEEPER_RESTART=1164
DUEL_PRESSURE=748
POSITIONAL_ATTACK_SIGNAL=729
SHOT=353
CARRY_DRIBBLE=286
BALL_LOSS=215
RECOVERY=147
FOUL=64
Turkey row-volume=2318
Australia row-volume=1141
```

Important correction:

```text
zone_distribution=UNKNOWN 100.0%
channel_distribution=UNKNOWN 100.0%
```

Reason:

- current CSV surfaces did not expose x/y columns through the P1 Lite reader;
- missing-column report flagged x/y absence for Goalkeepers.csv and Players.csv;
- Teams.csv also lacked team/x/y for the current Lite reader.

This is not a failed P1 run. It is a surfaced data-dictionary gap.

## P1 Claim Boundary

P1 may say:

- row-level evidence shows
- visible surface evidence indicates
- action-family volume suggests
- restart signal volume is visible
- team row-volume is visible
- requires later validation

P1 must not say:

- team dominated
- coach planned
- tactical truth
- pitch control truth
- off-ball structure truth
- body orientation truth
- fatigue truth
- canonical event count before Canonical Event Lite
- clean phase truth before claim gate

P1 preserved:

```text
canonical_event_count = UNKNOWN
```

## Rhythm / V12 Decision

V12 rhythm evidence stack remains queued.

Current V12 status:

```text
SPEC_CORRECTION_ACCEPTED
```

EXT-V11-EO advanced metrics are accepted as support-layer extension:

- spectral_flux supports rhythm break / tempo-shift evidence
- Markov sterile-loop detector remains primary event-only loop detector
- cross-channel rhythm coherence supports diagnostic rhythm interaction

V12 implementation waits for upstream gates:

- Canonical Event Lite
- sequence candidate
- signal density gate
- claim router

No rhythm state can be assigned from one signal alone.

## Fitness Decision

Fitness signal support remains:

```text
INDEX_AND_ISOLATE_NOT_RUNTIME_AUTHORITY
```

Reason:

- no real external fitness/load/GPS/HRV files were found in current scan evidence;
- fitness can be support signal only;
- fitness cannot override ACTIVE_MATCH evidence.

## Next Executable Step

Write P2 Canonical Event Lite V1 contract.

P2 must solve the surfaced gap from P1:

- canonical event-lite schema
- column synonym registry
- event type normalization
- team label normalization
- coordinate column detection
- canonical_event_count policy remains UNKNOWN until validation completes

Recommended contract path:

```text
docs/contracts/canonical_event_lite_v1.md
```

## Decision Result

```text
P0A_GOVERNANCE_PACK_WRITTEN
P1_ACTIVE_MATCH_EVIDENCE_PASS
P2_NEXT_PRODUCT_NODE
RHYTHM_IMPLEMENTATION_DEFERRED
FITNESS_SUPPORT_ISOLATED
```

This file is governance evidence plus operator-reported ACTIVE_MATCH evidence summary. It is not PRODUCTION_RELEASE by itself.
