# Base Event and Event Label Main Rule V1

## Authority

This contract is a product rule for HPFA. Runtime truth remains:

`runtime/active_single_match/current`

## Main rule

```text
A raw surface row does not automatically equal a distinct canonical event.
```

This rule does not deny that passes, shots, recoveries, interceptions, tackles, duels, carries, losses, fouls, restarts, saves, and goalkeeper actions are football events.

It requires HPFA to distinguish the physical football event from the labels, attributes, contexts, participation markers, provider reflections, and derived classes attached to that event.

## Three-layer ontology

### 1. Base football event

A row or deterministic row group may become a `BASE_EVENT_CANDIDATE` when it provides a football action family such as:

- PASS
- SHOT
- RECOVERY
- INTERCEPTION
- TACKLE
- DUEL
- CARRY_DRIBBLE
- BALL_LOSS
- FOUL
- RESTART
- SAVE_GK_ACTION

Canonical admission still requires match binding, actor/team identity, time/source consistency, and duplicate/reflection resolution.

### 2. Event label or attribute

A label may express:

- event outcome;
- event qualifier;
- event context;
- event participation;
- provider-defined event class;
- rule-derived or model-derived event class;
- cross-role reflection.

Examples include accurate, inaccurate, forward, progressive, long, successful pressure, high-threat loss, positional-attack involvement, counterattack, chance creation, and mistake leading to chance or goal.

A label may be valid, invalid, conflicting, or unresolved independently from the base event.

### 3. Label validity evidence

Every non-trivial label must preserve, when available:

- operational definition ID;
- definition version;
- provider and label origin;
- annotator or system ID;
- interobserver/intraobserver reliability or equivalent audit evidence;
- linked base-event candidates;
- source rows;
- event/sequence/phase/pattern scope;
- validation status;
- conflict reasons;
- claim ceiling.

## Non-duplication rule

A physical pass represented by labels such as:

```text
passes accurate
passes forward accurate
progressive passes accurate
long passes accurate
```

must not automatically become four pass events. HPFA should create one base pass candidate and attach the compatible labels to it when actor, time, location, source, and relation evidence support that grouping.

## Independent gate rule

A base event can remain a valid surface candidate while one or more labels remain `REVIEW_REQUIRED_DEFINITION_AUDIT`.

```text
BASE EVENT ADMISSION != LABEL VALIDATION
```

## XLSX / CSV / XML roles

```text
XLSX = aggregate WHAT HAPPENED layer
CSV/XML = base-event and event-label surfaces showing HOW IT HAPPENED
```

XLSX does not create a timeline. CSV/XML do not become canonical events merely by row count.

## Match-test requirements

The first match test must report:

- source evidence atom count;
- CSV/XML conformant trace units;
- base-event surface candidates by family;
- event-label candidates by semantic role;
- labels attached to base-event candidates;
- label-only groups;
- incompatible multi-family groups;
- identity gate status;
- canonical event count;
- production release status.

## Claim boundary

Until identity and relation gates pass:

```text
base event count = surface candidate count only
canonical_event_count = UNKNOWN
production_release = false
```

## Status

`MAIN_RULE_ACCEPTED / EXECUTABLE_MATCH_TEST_REQUIRED / NOT_PRODUCTION`
