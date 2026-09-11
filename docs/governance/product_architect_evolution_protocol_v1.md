# HPFA Product Architect Evolution Protocol V1

Status: `POLICY_CORRECTION_PASS_ZFGV_MIGRATION`

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

## Mission

Every architecture review must strengthen HPFA as a long-lived ZFGV/EFOD-based, claim-safe football intelligence product.

ZFGV is a multi-surface Football Observation Fabric:

```text
event ⊂ ZFGV
ZFGV != event
```

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

## Observation capability rule

Global `event-only compatible?` is retired as a product admission gate.

For every construct ask:

```text
1. Which observation capabilities are required?
2. Which are actually available and admitted?
3. What source/evidence strength do they have?
4. What is the maximum safe claim ceiling?
5. Which capability gaps require downgrade, abstention, external evidence or tracking/video?
```

Canonical admission rule:

```text
required_capabilities ⊆ admitted_capabilities
```

Observation families:

```text
ACTION / EVENT
ENTITY / ACTOR
TEMPORAL
SPATIAL
OUTCOME / QUALIFIER
RELATIONAL
PROCESS / PARTICIPATION
AGGREGATE / TABULAR
EXTERNAL CONTEXT
TRACKING / VIDEO — only when genuinely present
HPFA-DERIVED INTELLIGENCE
```

Event-specific modules remain legitimate event subsystems. Historical identifiers are not blindly renamed. Historical event-only global gates are rehabilitated rather than copied forward.

## Mandatory search order

Before proposing implementation:

```text
1. current hpfa main / current producer-contract-tests
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive
6. Dropbox
7. academic support
8. targeted runtime discovery / ACTIVE_MATCH evidence
```

The search begins with a declared HPFA product gap. Never search donors merely for interesting code.

## Donor rule

```text
ADAPT_NOT_COPY
REHABILITATE_BEFORE_PARALLEL_ENGINE
CODE_LAST
```

Never transplant donor modules or donor truth.

Extract only:

```text
capabilities
patterns
algorithms
contracts
interfaces
pipelines
data structures
testing strategies
architecture decisions
reusable concepts
```

Then design an HPFA-native implementation with HPFA observation requirements, contracts, claim ceilings, tests, runtime boundaries and release state.

## Required architecture review output

Every substantive review must include:

```text
Current limitation
Hidden limitation
Required observation capability
Available admitted surface
Safe new ceiling
Still forbidden
Better architecture
Migration plan
Tests required
Analyst value gain
Release readiness
```

When relevant, also include:

```text
Decision log
Rejected ideas
Accepted ideas
Architecture changes
Implementation plan
Risk register
Release status
```

## Multi-role review council

Every major proposal is reviewed from seven roles.

### CEO

Questions:

```text
Does this create durable product differentiation?
Does it improve analyst value or reduce strategic risk?
Does it move HPFA toward the strongest defensible football intelligence platform?
```

### CTO

Questions:

```text
Is the architecture reusable?
Does it reduce or create coupling?
Does it preserve source authority, capability admission and release boundaries?
```

### Principal Engineer

Questions:

```text
Are contracts explicit?
Are identities stable?
Can failures propagate deterministically?
Is the implementation composable and maintainable?
```

### Football Scientist

Questions:

```text
What football behaviour becomes visible?
Which observation capability supports it?
What alternative explanations exist?
What cannot be inferred from the admitted evidence?
```

### QA Lead

Questions:

```text
What are the failure modes?
Which regression protects the largest surface?
What evidence is required before merge and release?
```

### Research Director

Questions:

```text
What is the known state of the art?
What remains unknown?
Which competing approaches should be compared?
What evidence could falsify the proposal?
```

### Product Manager

Questions:

```text
Who consumes the output?
What analyst workflow improves?
What is the smallest valuable product slice?
```

## Consensus rule

The council must not converge early.

A proposal is accepted only after recording:

```text
strongest supporting argument
strongest objection
main alternative
rejection condition
remaining uncertainty
```

Consensus cannot override a hard claim, authority, runtime or release boundary.

## Product scorecard

Every proposal is scored from 1 to 5 on:

```text
Product Value
Engineering Cost
Maintainability
Runtime Cost
Future Reuse
AI Reuse
Football Value
Claim Safety
Release Risk
```

Interpretation:

```text
high value + high reuse + high claim safety = preferred
high cost + low reuse + high release risk = reject or defer
```

Pareto and Lindy policies apply:

```text
prioritize high-leverage work
prefer durable contracts and abstractions
reject isolated novelty with no downstream consumer
```

## Tough-review checklist

The reviewer must actively search for:

```text
architectural debt
coupling
circular dependencies
weak abstractions
naming problems
governance drift
scalability risks
testing gaps
claim risks
football interpretation risks
AI integration risks
maintenance risks
provider lock-in
silent data loss
state promotion
identity loss
obsolete global event-only gates
capability suppression
```

For every issue provide:

```text
minimal fix
ideal fix
priority
impact
migration cost
```

## 2035 opportunity filter

Research may draw from:

```text
machine learning
systems engineering
physics
network science
information theory
neuroscience
complex adaptive systems
military decision systems
robotics
distributed systems
Bayesian inference
knowledge graphs
ontology engineering
```

Ideas are eligible when their required observation capabilities can be stated explicitly and the current/future HPFA surface can satisfy them without inventing truth.

Tracking-dependent research is not rejected wholesale. Separate the tracking/video-required component from the parts applicable to current ZFGV surfaces.

Every research idea must include:

```text
scientific basis
football construct
required observations
ZFGV applicability
runtime feasibility
claim safety
potential module
priority
research roadmap
evidence required
failure modes
future research questions
```

## Known-state / unknown-state protocol

For every research topic document:

```text
known state of the art
unknown problems
research gaps
competing approaches
potential breakthroughs
cross-disciplinary ideas
implementation roadmap
evidence required
failure modes
future research questions
```

A paper or donor document is research support only. It is never runtime truth.

## ZFGV eligibility gate

A proposal is eligible only when its required observation capabilities are explicit and can be bound to admitted surfaces or explicitly marked external/tracking/video required.

Examples potentially eligible with current ZFGV observations, depending on admission:

```text
sequence/process candidates
change-point candidates
entropy diagnostics
transition matrices
point-process intensity candidates
Bayesian evidence updates
argument graphs
contradiction routing
uncertainty and abstention
multi-scale context windows
spatial zone/channel candidates
process participation candidates
aggregate/tabular reconciliation
context-conditioned variation
successful/failed/deviant process comparison
```

Examples rejected as direct truth without tracking/video or equivalent authority:

```text
true pitch control
true off-ball structure or geometry
true team shape/compactness
body orientation truth
scanning truth
fatigue/physical load truth
true pressure geometry
coach intention
tactical plan
causality
dominance
```

## Architecture preference

Prefer:

```text
stable identifiers
small deterministic modules
explicit input/output contracts
append-only registries
provider-neutral schemas
shared validation utilities
thin orchestrators
stage ledgers
traceable JSON/TSV/text artifacts
fail-closed state machines
construct-specific capability admission
```

Reject or isolate:

```text
monoliths
implicit field aliases
silent repair
opaque aggregate scores
hardcoded match identity
provider-specific shortcuts
untraceable generated language
single-signal truth assignment
global event-only product gates
```

## AI reuse standard

AI may assist with:

```text
search
classification
schema proposal
argument comparison
counter-scenario generation
report candidate composition
research synthesis
```

AI may not become an unlogged source of match truth.

Every AI-assisted artifact must preserve:

```text
input evidence refs
model-independent contract
claim ceiling
review state
withdrawal conditions
human or gate decision
```

## Required decision log

Each major architecture decision records:

```text
decision_id
product_gap
current_main_state
required_observation_capabilities
available_admitted_surfaces
donor_sources_checked
accepted_capability
rejected_alternatives
HPFA_native_contract
runtime_dependency
claim_impact
test_strategy
analyst_value_gain
release_impact
migration_cost
open_questions
```

## Required risk register

Each proposal records:

```text
risk_id
risk_family
trigger
impact
likelihood
mitigation
regression_test
owner_module
release_blocking
```

Risk families:

```text
architecture
data authority
claim safety
football interpretation
runtime
AI integration
maintenance
release
```

## Release discipline

The architecture council may recommend implementation, but cannot promote release without evidence.

```text
IMPLEMENTED != TESTED
TESTED != VALIDATED
VALIDATED_ON_ONE_MATCH != GENERALIZED
CI_GREEN != FOOTBALL_VALID
OPEN_PR != MAIN
MAIN != PRODUCTION
ACTIVE_MATCH_PASS != PRODUCTION_RELEASE
```

Required release answer:

```text
current status
missing evidence
blocking risks
next eligible status
```

## Current HPFA architecture priorities

Current highest-leverage work:

```text
1. ZFGV migration + obsolete global event-only gate rehabilitation
2. observation/source semantics + provenance/dependency
3. episode/process/consequence integration
4. successful/failed/deviant variant comparison
5. recurrence/variation/deviation + counterevidence
6. Safe Finding + human analyst report closure
7. multi-match Gold Corpus
8. longitudinal Postmatch intelligence
```

Random isolated metrics, parallel engines and new product verticals are lower priority until the Postmatch reference spine is proven.

## Final rule

```text
Do not optimize for today's feature.
Optimize for HPFA's ten-year capability surface.
Close a real evidence-spine gap and create new defensible analyst intelligence.
```
