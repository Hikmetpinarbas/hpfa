# HPFA Product Architect Evolution Protocol V1

Status: `ZFGV_POLICY_CORRECTION_PASS`

## Product authority

```text
Hikmetpinarbas/hpfa = ONLY executable product repository
HP-Motor = donor
HP-Engine = donor
HP-PROJELERI = donor
Google Drive = donor / governance reference
Dropbox = donor / archive reference
Academic papers = research support
runtime/active_single_match/current = ONLY match-truth authority
```

This protocol extends, and does not replace, `HPFA_DONOR_TO_PRODUCT_OPERATING_MODEL_V1`.

## Canonical observation doctrine

```text
EVENT ⊂ ZFGV
ZFGV != EVENT
```

HPFA is a ZFGV football-intelligence product. ACTION/EVENT is one observation family and must never be used as the product-wide observation ceiling, admission veto, eligibility default or routing assumption.

Every construct is evaluated from the evidence it actually requires:

```text
CONSTRUCT
→ REQUIRED OBSERVATION CAPABILITIES
→ ADMITTED CAPABILITIES
→ OPTIONAL CAPABILITIES
→ FORBIDDEN WITHOUT
→ CLAIM CEILING
→ ADMISSION DECISION
```

Missing required capability => `FAIL_CLOSED / DOWNGRADE`.
Missing optional capability => `DEGRADED`.

## Mission

Every architecture review must strengthen HPFA as a long-lived ZFGV football intelligence product.

The objective is not to finish the current feature. The objective is to increase one or more of:

```text
football intelligence
scientific validity
automation
explainability
claim safety
analyst productivity
product scalability
knowledge reuse
engineering quality
repository governance
```

## Mandatory search order

Before proposing implementation:

```text
1. current hpfa main + current development frontier
2. current producer / contract / tests / consumers
3. HP-Motor
4. HP-Engine
5. HP-PROJELERI
6. Google Drive
7. Dropbox
8. academic support
9. ACTIVE_MATCH evidence when physically required
```

The search begins with a declared HPFA product gap.
Never search donors merely for interesting code.

## Donor rule

```text
ADAPT_NOT_COPY
REHABILITATE_BEFORE_PARALLEL_ENGINE
CODE_LAST
```

Never transplant donor modules. Extract capabilities, algorithms, contracts, interfaces, pipelines, data structures, tests and architecture ideas, then design an HPFA-native implementation with explicit observation requirements, claim ceilings, tests, runtime boundaries and release status.

## Required architecture review output

Every substantive review must include:

```text
Current limitation
Hidden limitation
Required observation capabilities
Admitted / missing capabilities
Better architecture
Migration plan
Tests required
ACTIVE_MATCH need
Analyst value delta
Claim ceiling
Release readiness
```

## Multi-role review council

### CEO
- Does this create durable product differentiation?
- Does it improve analyst value or reduce strategic risk?
- Does it expand defensible ZFGV intelligence rather than merely adding code?

### CTO
- Is the architecture reusable?
- Does it reduce or create coupling?
- Does it preserve source authority and release boundaries?
- Does any ACTION/EVENT-specific component accidentally become a global ZFGV gate?

### Principal Engineer
- Are contracts explicit?
- Are identities stable?
- Can failures propagate deterministically?
- Is admission capability-specific?

### Football Scientist
- What football behaviour becomes visible?
- Which observation families are required?
- What alternative explanations exist?
- What cannot be inferred without tracking/video/external authority?

### QA Lead
- What are the failure modes?
- Which regression protects the largest capability surface?
- Can a valid non-event ZFGV construct be rejected by an event-shaped prerequisite?

### Research Director
- What is the known state of the art?
- What remains unknown?
- Which competing approaches should be compared?
- What evidence could falsify the proposal?

### Product Manager
- Who consumes the output?
- What analyst workflow improves?
- What is the smallest valuable product slice?

## Product scorecard

Score Product Value, Engineering Cost, Maintainability, Runtime Cost, Future Reuse, AI Reuse, Football Value, Claim Safety and Release Risk.

Prefer high-value, reusable, claim-safe work. Reject isolated novelty with no downstream consumer.

## Tough-review checklist

Actively search for:

```text
architectural debt
coupling
circular dependencies
weak abstractions
governance drift
provider lock-in
silent data loss
state promotion
identity loss
hidden event-shaped universal prerequisite
observation-family suppression
aggregate→action identity leakage
coordinate→tracking leakage
provider label→tactical truth leakage
```

For every issue provide minimal fix, ideal fix, priority, impact and migration cost.

## Research and opportunity eligibility

A proposal is eligible when its required observation capabilities are available or can be acquired and admitted with an explicit claim ceiling.

Eligible observation families include:

```text
ACTION/EVENT
ENTITY/ACTOR
TEMPORAL
SPATIAL
OUTCOME/QUALIFIER
RELATIONAL
PROCESS/PARTICIPATION
AGGREGATE/TABULAR
EXTERNAL CONTEXT
TRACKING/VIDEO when available and admitted
HPFA-DERIVED INTELLIGENCE
```

No proposal is rejected merely because it is not ACTION/EVENT-shaped.

Examples:
- aggregate/tabular constructs may be valid without action identity;
- spatial constructs may be valid after pitch-frame/direction admission without tracking truth;
- relational/process constructs may be valid without being reduced to provider success/failure labels;
- tracking/video constructs require actual tracking/video authority where physical/off-ball truth is claimed.

## Claim-safety boundary

Without the required admitted tracking/video/external evidence, do not promote to truth:

```text
true pitch control
true team shape / compactness / defensive-line height
off-ball geometry / runs / options
body orientation / scanning
true speed / load / fatigue
pressure geometry
coach intention / tactical plan
dominance
causality
```

This is an evidence-ceiling rule, not an Event-Only rule.

Truth locks:

```text
ROW != EVENT TRUTH
EVENT != WHOLE OBSERVATION UNIVERSE
PROVIDER LABEL != PHYSICAL/TACTICAL TRUTH
AGGREGATE != ACTION IDENTITY
MULTIFORMAT != INDEPENDENT EVIDENCE
SAME TIMESTAMP != TOTAL ORDER
COORDINATE != TRACKING
PROCESS LABEL != COACH INTENTION
RECURRENCE != CAUSALITY
MODEL OUTPUT != FACT
LLM TEXT != EVIDENCE
ABSENCE != COUNTEREVIDENCE
```

## Architecture preference

Prefer stable identifiers, small deterministic modules, explicit contracts, provider-neutral schemas, shared validation utilities, thin orchestrators, stage ledgers, traceable artifacts and fail-closed state machines.

Reject or isolate monoliths, implicit aliases, silent repair, opaque aggregate scores, hardcoded match identity, provider-specific shortcuts, untraceable generated language and single-signal truth assignment.

## AI reuse standard

AI may assist with search, classification, schema proposal, argument comparison, counter-scenario generation, report candidate composition and research synthesis. AI may not become an unlogged source of match truth.

Every AI-assisted artifact must preserve input evidence refs, model-independent contract, claim ceiling, review state, withdrawal conditions and human/gate decision.

## Release discipline

```text
SPEC_ONLY != executable
SMOKE_PASS != ACTIVE_MATCH evidence
RELEASE_CANDIDATE != production
PASS != RELEASE
```

The architecture council may recommend implementation but cannot promote release without required evidence.

## Final rule

```text
Do not ask whether a football capability fits Event-Only.
Ask which ZFGV observations are required to defend it.
Do not optimize for today's feature.
Optimize for HPFA's ten-year capability surface.
```
