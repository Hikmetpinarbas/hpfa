# HPFA Reasoning Grammar Spine Lite V1

Date: 2026-06-27

Status: SPEC_ONLY

## Purpose

Build the smallest useful bridge from admitted ZFGV evidence to analyst-facing football reading.

Canonical spine:

```text
observation -> primitive candidate -> relation/sequence/process candidate -> context -> behaviour hypothesis -> recurrence/variation -> counterevidence -> explanation candidate
```

ACTION/EVENT is one possible observation family, not the whole reasoning universe.

No direct jump from metric/model output to story is allowed.

## Scope

This contract starts with primitive candidate reasoning only.

Primitive-only output may emit primitive candidates and primitive explanations. It must not emit behaviour or pattern truth until the relevant relation/sequence/process/context gates exist and pass.

Possible inputs, depending on construct requirements:

- ACTIVE_MATCH identity-compatible runtime
- admitted ACTION/EVENT evidence when required
- aggregate/tabular observation when required
- admitted temporal/spatial/context observations
- relation/process/participation candidates
- postmatch analyst evidence surfaces
- sequence/window outputs when required

## Primitive Candidates

Allowed initial candidates may include:

- pass_surface_candidate
- carry_progression_surface_candidate
- recovery_surface_candidate
- loss_surface_candidate
- terminal_action_surface_candidate
- restart_surface_candidate
- channel_progression_surface_candidate
- aggregate_metric_surface_candidate
- relational_candidate
- process_participation_candidate

## Evidence Ladder

Every candidate must expose the evidence properties relevant to its construct, including provenance/dependency, observation family, identity/context where required, confidence/review state, falsifier or withdrawal condition, and blocked claims.

## Stage Gate

Primitive Grammar Lite may only produce candidate-level evidence and explanation.

The following remain gated until their own required capabilities are admitted:

- sequence truth
- behaviour truth
- pattern truth
- tactical truth
- causal truth
- match story claim

## Overclaim Guard

Reject:

- ready for deployment without release evidence
- football ontology is validated
- cognitive state is measured from match rows
- pre-motor time or mental decline inferred from ordinary match observations
- next action predicted as truth
- Voronoi or pitch-control truth without admitted tracking/geometry authority
- off-ball structure without admitted tracking/video authority
- coach intention without appropriate external evidence
- city/culture as match runtime truth

Allowed replacement language:

- candidate
- proxy
- visible/admitted observation indicates
- action-surface reading
- aggregate/tabular support
- relation/process candidate
- requires later validation
- evidence-only until claim gate

## Claim Boundary

Allowed where supported:

- visible observation indicates
- action-family volume suggests
- aggregate/tabular support indicates
- admitted spatial candidate is concentrated in
- relation/process candidate
- primitive explanation candidate

Blocked without the required admitted evidence:

- tactical truth
- dominance truth
- possession truth
- phase truth
- sequence truth
- coach intention
- off-ball structure
- pitch control
- causality

## Truth Locks

```text
ROW != EVENT TRUTH
EVENT != WHOLE OBSERVATION UNIVERSE
AGGREGATE != ACTION IDENTITY
MULTIFORMAT != INDEPENDENT EVIDENCE
SAME TIMESTAMP != TOTAL ORDER
COORDINATE != TRACKING
PROCESS LABEL != COACH INTENTION
RECURRENCE != CAUSALITY
MODEL OUTPUT != FACT
ABSENCE != COUNTEREVIDENCE
```

## Minimality Gate

Do not add a construct unless it improves analyst decision quality and has explicit required observation capabilities, claim ceiling and consumer.

## Tests

- outputs remain inside approved output root
- no tracking truth claims without tracking/video authority
- no metric/model-to-story jump
- candidates include falsifier/withdrawal conditions where applicable
- no sample match identity leak
- primitive-only mode blocks behaviour/pattern truth
- valid non-event ZFGV observation is not rejected merely for lacking ACTION/EVENT identity

## Release

SPEC_ONLY until implementation, tests, and required ACTIVE_MATCH evidence exist.
