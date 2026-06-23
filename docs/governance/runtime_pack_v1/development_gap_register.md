# HPFA Development Gap Register

Date: 2026-06-23

Status: GOVERNANCE_GAP_REGISTER_ACTIVE

## Purpose

Prevent HPFA development from leaving hidden gaps between modules.

Every product node must state:

1. what it proves;
2. what it does not prove;
3. which downstream gate is required before stronger analyst language;
4. whether the output is engineering evidence or analyst evidence;
5. whether runtime evidence exists for ACTIVE_MATCH.

## Rule

No new node may be treated as production-bound unless its known gaps are registered.

```text
PASS != RELEASE
ACTIVE_MATCH_EVIDENCE_PASS != PRODUCTION_RELEASE
surface inventory != pattern structure
identity binding != team behaviour truth
support evidence != runtime event truth
multi-surface duplicate candidates != deduplicated event truth
```

## Active Gap Register

### G1 Cross-Surface Event Identity / Deduplication Gap

Current state:

```text
cross_surface_event_identity=UNRESOLVED
deduplicated_event_count=UNKNOWN
event_count_claim_allowed=false
```

Why it matters:

- A single football action may appear in both team-level and player-level surfaces.
- Goalkeeper surfaces may be filtered or specialized views of rows that also appear elsewhere.
- Aggregate surfaces may summarize event families without representing individual events.
- Metrics must not count the same underlying football action multiple times.

Required node:

```text
Event Identity Resolution Gate Lite V1
```

Current status:

```text
NEXT_PRODUCT_NODE_BEFORE_PRIMARY_SURFACE_SELECTION
```

### G2 Primary Event Surface Selection Gap

Current state:

```text
primary_event_surface_candidate=UNRESOLVED
deduplicated_event_count=UNKNOWN
event_count_claim_allowed=false
```

Why it matters:

- Players, Teams and Goalkeepers surfaces may overlap.
- Multi-surface rows cannot be treated as event count.
- Time/phase/possession/sequence modules need a primary event surface candidate or explicit unresolved state.
- Primary surface selection should consume duplicate-risk evidence from Event Identity Resolution Gate.

Required node:

```text
Primary Event Surface Gate Lite V1
```

Current status:

```text
WAITING_EVENT_IDENTITY_RESOLUTION_GATE
```

### G3 Temporal Ordering Gap

Current state:

```text
time/phase truth unavailable
minute/timestamp columns incomplete or unresolved across surfaces
```

Why it matters:

- No sequence claim can be made without temporal ordering.
- Rhythm V12 cannot run without temporal density and sequence candidate gates.

Required node:

```text
Time / Phase Lite V1
```

Current status:

```text
INTENTIONAL_WAIT
```

### G4 Possession Boundary Gap

Current state:

```text
possession truth unavailable
turnover/continuity boundary not validated
```

Why it matters:

- Team row-volume is not possession.
- Ball control or dominance language remains blocked.

Required node:

```text
Possession Boundary Apparatus Lite V1
```

Current status:

```text
INTENTIONAL_WAIT
```

### G5 Sequence Candidate Gap

Current state:

```text
sequence candidate unavailable
pattern structure not built
```

Why it matters:

- Repeated event-family volume is not pattern structure.
- Pattern claims require ordered, bounded, claim-gated sequence candidates.

Required node:

```text
Sequence Candidate Lite V1
```

Current status:

```text
NOT_STARTED
```

### G6 Report Language Gap

Current state:

```text
safe surface summary exists
claim-safe grammar gate not yet implemented
```

Why it matters:

- Even correct evidence can become unsafe if report wording overclaims.
- Analyst-facing output must separate visible evidence, support evidence and unresolved gates.

Required node:

```text
Claim-Safe Report Grammar Gate V1
```

Current status:

```text
INTENTIONAL_WAIT
```

### G7 Reference Concept Extraction Gap

Current state:

```text
PDF text extracted
concept extraction not implemented
reference claims not bound to event evidence
```

Why it matters:

- Reference documents are support-only.
- Extracted text cannot become football truth without concept extraction and claim routing.

Required node:

```text
Reference Concept Extractor Lite V1
```

Current status:

```text
NOT_STARTED
```

### G8 Rhythm Readiness Gap

Current state:

```text
Rhythm V12 spec accepted
canonical event lite exists as surface inventory
sequence candidate unavailable
signal density gate unavailable
```

Why it matters:

- No rhythm state can be assigned from one signal alone.
- STFT is diagnostic only, not classifier.

Required upstream gates:

```text
Event Identity Resolution Gate
Primary Event Surface Gate
Time / Phase Lite
Sequence Candidate Lite
Signal Density Gate
Claim Router
```

Current status:

```text
SPEC_CORRECTION_ACCEPTED
IMPLEMENTATION_WAITING
```

## Required Per-Node Evidence Block

Every future node must include this block in contract/logbook:

```text
Engineering evidence:
- module exists?
- py_compile passed?
- tests passed?
- ACTIVE_MATCH run passed?
- flat phone outputs written?

Analyst evidence:
- what became visible?
- what remains unresolved?
- which analyst sentence is safe?
- which analyst sentence is blocked?

Gap status:
- gaps closed
- gaps still open
- next required gate
```

## Current Safe Main Analyst Sentence

```text
ACTIVE_MATCH contains readable multi-surface row inventory and identity binding evidence. This is not a deduplicated event count or pattern structure. A single football action may appear in both team-level and player-level surfaces, so event identity resolution is required before primary surface selection, phase, possession, sequence or metric counting claims.
```

## Governance Status

```text
GOVERNANCE_GAP_REGISTER_ACTIVE
PRODUCTION_RELEASE_NOT_GRANTED
```
