# HPFA Next Node Decision V1

Date: 2026-06-22

Status: P0A_GOVERNANCE_FILE

## Decision

The next correct product node after P0A is:

```text
P1 ACTIVE_MATCH Analyst Report Lite V1
```

Rhythm implementation must not start before P1.

## Reason

P0 runner-flat-out-v1 is closed. The repo has a spine runner, boundary scorer, surface manifest and flat phone-output guard.

The next executable analyst value is not a rhythm engine. It is a claim-safe ACTIVE_MATCH report that turns visible surface evidence into analyst-facing output without overclaiming.

## P1 Contract Target

P1 must produce:

```text
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.json
/sdcard/Download/HPFA/active_match_analyst_report_lite_v1.txt
```

## P1 Required Content

P1 must include:

- match snapshot
- surface inventory
- action-family volume
- zone/channel distribution
- team row-volume
- goalkeeper/restart signal
- pass/shot/duel/carry/loss/recovery block
- analyst reading
- missing-column report
- technical limits

## P1 Claim Boundary

P1 may say:

- row-level evidence shows
- visible surface evidence indicates
- action-family volume suggests
- coordinate evidence is concentrated in
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

P1 must preserve:

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

Write P1 ACTIVE_MATCH Analyst Report Lite V1 contract before implementing the module.

Recommended path:

```text
docs/contracts/active_match_analyst_report_lite_v1.md
```

Then implement:

```text
active_match_analyst_report_lite.py
hpfa/modules/core/active_match_analyst_report_lite/
```

## Decision Result

```text
NEXT_NODE_LOCKED_P1_ANALYST_REPORT_LITE_V1
RHYTHM_IMPLEMENTATION_DEFERRED
FITNESS_SUPPORT_ISOLATED
```

This file is governance evidence. It is not ACTIVE_MATCH execution evidence and not product release proof.
