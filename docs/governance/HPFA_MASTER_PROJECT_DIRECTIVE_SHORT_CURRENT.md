# HPFA MASTER PROJECT DIRECTIVE — CURRENT

Status: ACTIVE_GOVERNANCE_RECORD  
Product: Hikmet Pınarbaş Football Analytics (HPFA)

## Purpose

HPFA is a match-agnostic football intelligence system for converting observable match evidence into defensible analyst knowledge.

The product objective is not more code, guards or metrics. It is higher-quality football understanding with explicit evidence, uncertainty and claim boundaries.

## Canonical doctrine

```text
EVENT ⊂ ZFGV
```

Event data is one observation family, not the whole observation universe.

Observation families include:

- ACTION / EVENT
- ENTITY / ACTOR
- TEMPORAL
- SPATIAL
- OUTCOME / QUALIFIER
- RELATIONAL
- PROCESS / PARTICIPATION
- AGGREGATE / TABULAR
- EXTERNAL CONTEXT
- HPFA-DERIVED INTELLIGENCE

Required missing observation capability causes FAIL_CLOSED or DOWNGRADE for the affected construct. Optional missing capability causes DEGRADED only where relevant.

## Evidence spine

```text
SOURCE
→ SURFACE
→ OBSERVATION
→ SEMANTICS
→ IDENTITY / DEPENDENCY
→ TIME / SPACE ADMISSION
→ RELATION
→ EPISODE / PROCESS
→ FEATURE
→ METRIC / MODEL
→ SIGNAL
→ HYPOTHESIS
→ COUNTEREVIDENCE
→ FINDING
→ CLAIM
→ ANALYST OUTPUT
```

## Truth locks

```text
ROW != EVENT TRUTH
EVENT != WHOLE OBSERVATION UNIVERSE
PROVIDER LABEL != PHYSICAL / TACTICAL TRUTH
AGGREGATE != ACTION IDENTITY
MULTIFORMAT != INDEPENDENT EVIDENCE
SAME TIMESTAMP != TOTAL ORDER
COORDINATE != TRACKING
PROCESS LABEL != COACH INTENTION
RECURRENCE != CAUSALITY
MODEL OUTPUT != FACT
LLM TEXT != EVIDENCE
ABSENCE != COUNTEREVIDENCE
NO_VISIBLE_FOLLOWUP != FAILURE
```

CSV and XML may be reflections of the same upstream observation. XLSX aggregate rows do not create action identity. Row/list/index order is not chronology.

## Tracking and video boundary

Tracking and video are not mandatory HPFA dependencies.

Research that uses tracking/video is not automatically rejected. It must be separated into:

1. capability that genuinely requires tracking/video;
2. capability that can be supported by admitted event/time/coordinate/actor/team/aggregate observations.

The second part may be adapted under the correct construct name.

Event-derived proxy != physical or tactical truth.

Without the required surfaces HPFA does not claim true shape, compactness, pitch control, off-ball geometry, true speed/load, pressure geometry, coach intention, dominance or causality.

## Product authority

- GitHub: code, contracts, tests, CI and review.
- ACTIVE_MATCH: physical runtime acceptance.
- Drive/Dropbox/research/donor repositories: support or historical evidence.

```text
OPEN PR != MAIN
CI PASS != ACTIVE_MATCH
ACTIVE_MATCH != PRODUCTION
DONOR PASS != PRODUCT PASS
```

Current product head is resolved from GitHub at read time. Static SHAs in historical records do not override current state.

## Runtime authority

The single-match physical runtime authority is:

```text
runtime/active_single_match/current
```

The absolute host/device path is discovered and verified at execution time and is not product authority.

Default claim locks:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Product method

```text
problem
→ current producer
→ gap
→ observation requirement
→ source role
→ contract
→ admission
→ tests
→ ACTIVE_MATCH need
→ minimal code
→ real-match evidence
→ red team
```

Rules:

- WIP=1
- ADAPT_NOT_COPY
- REHABILITATE_BEFORE_PARALLEL_ENGINE
- CODE_LAST
- provider differences are resolved at the boundary
- missing surfaces affect only dependent constructs
- no team/player/match/package-specific logic in product code
- no fixed row/event/episode count as portable truth

## Postmatch standard

```text
Observation
→ Episode / Process
→ Context
→ Consequence
→ Recurrence / Variation / Deviation
→ Counterevidence
→ Safe Finding
→ Human Analyst Report
```

Minimum useful chain:

```text
Evidence
→ Episode / Process
→ Successful / Failed / Deviant Variant
→ Counterevidence
→ Safe Finding
→ Analyst Output
```

Safe Finding fields should preserve:

- WHAT_VISIBLE
- SUPPORT
- COUNTEREVIDENCE
- SAFE_MEANING
- FORBIDDEN_INFERENCE
- UNCERTAINTY
- WITHDRAWAL_CONDITION
- ANALYST_ACTION

0 EMIT is valid. REVIEW_REQUIRED is not FAIL. Unresolved outcomes are not converted to negatives.

## Development objective

```text
MATCH PACKAGE
→ capability discovery
→ admitted surfaces
→ governed analysis
→ safe findings
→ professional postmatch report
→ human analyst decision support
```

Every product change must answer:

> If HPFA receives a different match package, can it read the football more correctly, more deeply and more defensibly?

If not, the work is LATER or REJECT.
