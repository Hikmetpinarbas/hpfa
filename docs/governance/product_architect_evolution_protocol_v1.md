# HPFA Product Architect Evolution Protocol V1

Status: `POLICY_CORRECTION_PASS`

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

Every architecture review must strengthen HPFA as a long-lived event-only football intelligence product.

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
1. current hpfa main
2. HP-Motor
3. HP-Engine
4. HP-PROJELERI
5. Google Drive
6. Dropbox
7. academic support
8. runtime discovery / ACTIVE_MATCH evidence
```

The search begins with a declared HPFA product gap.

Never search donors merely for interesting code.

## Donor rule

```text
ADAPT_NOT_COPY
```

Never transplant donor modules.

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

Then design an HPFA-native implementation with HPFA contracts, claim ceilings, tests, runtime boundaries and release status.

## Required architecture review output

Every substantive review must include:

```text
Current limitation
Hidden limitation
Better architecture
Migration plan
Future opportunities
Tests required
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
Does it move HPFA toward the best event-only platform?
```

### CTO

Questions:

```text
Is the architecture reusable?
Does it reduce or create coupling?
Does it preserve source authority and release boundaries?
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
What alternative explanations exist?
What cannot be inferred from event-only data?
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

Only ideas eventually implementable with event data are eligible.

Reject ideas that fundamentally require tracking, video-derived geometry or physical-load truth.

Every research idea must include:

```text
scientific basis
football interpretation
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

## Event-only eligibility gate

A proposal is eligible only if its core output can eventually be generated from event data plus declared metadata.

Examples of eligible families:

```text
sequence candidates
change-point candidates
entropy diagnostics
transition matrices
point-process intensity
Bayesian evidence updates
argument graphs
contradiction routing
uncertainty and abstention
multi-scale context windows
```

Examples rejected without tracking or additional authority:

```text
true pitch control
true off-ball structure
body orientation truth
fatigue truth
physical load truth
coach intention
complete tactical truth
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
donor_sources_checked
accepted_capability
rejected_alternatives
HPFA_native_contract
runtime_dependency
claim_impact
test_strategy
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
SPEC_ONLY != executable
SMOKE_PASS != ACTIVE_MATCH evidence
RELEASE_CANDIDATE != production
PASS != RELEASE
```

Required release answer:

```text
current status
missing evidence
blocking risks
next eligible status
```

## Current HPFA architecture priorities

Under Pareto + Lindy review, current highest-leverage work remains:

```text
1. repository and open-PR hygiene
2. cross-module failure propagation
3. shared recursive forbidden-field guard
4. canonical Argument -> Defeasible Route -> Evidence Graph contract
5. end-to-end Intelligence Chain fixture
6. thin Intelligence Pipeline Orchestrator
7. ACTIVE_MATCH engineering + analyst evidence
```

New isolated metrics, readers and report templates are lower priority until this integration spine is proven.

## Final rule

```text
Do not optimize for today's feature.
Optimize for HPFA's ten-year capability surface.
```
