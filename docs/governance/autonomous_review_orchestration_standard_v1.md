# HPFA Autonomous Review Orchestration Standard V1

Status: `POLICY_CORRECTION_PASS`

## Purpose

This standard converts five proposed orchestration prompts into HPFA-native product governance.

It extends:

```text
Product Architect Evolution Protocol V1
Pareto Operating Standard V1
Lindy + Pareto Roadmap V1
```

It does not create runtime capability, match truth or production release.

## Core rule

```text
Use structured disagreement to improve product decisions.
Do not use theatrical roleplay to manufacture confidence.
```

Every orchestration method must improve at least one of:

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

## Prompt 1 — Role Conflict and Consensus Protocol

Decision: `ACCEPT_WITH_RISK_TIERING`

### Accepted capability

Use independent review roles with different objectives:

```text
CEO / Product Value
CTO / Architecture
Principal Engineer / Contracts and failure behavior
Systems Scientist / Scientific validity
Football Scientist / Football interpretation
QA Lead / Failure modes and tests
Product Manager / Analyst workflow
```

### Correction

A fixed three-round debate is not mandatory for every change.

Mandatory debate depth must depend on risk:

```text
R0 documentation typo:
  one-pass review

R1 isolated low-risk utility:
  two-role challenge

R2 shared contract or cross-module behavior:
  multi-role review plus strongest objection

R3 authority, claim, runtime or release change:
  minimum three challenge rounds plus decision log and risk register
```

### Required consensus record

```text
strongest supporting argument
strongest objection
main alternative
falsification or rejection condition
remaining uncertainty
final decision
```

### Rejected behavior

```text
forced consensus
role agreement without evidence
long debate with no decision artifact
```

## Prompt 2 — Evolution Engine / 2035 Reverse Roadmap

Decision: `ACCEPT`

### Required research frame

```text
known current state
hidden limitations
research gaps
competing approaches
2035 target capability
reverse roadmap
first reusable abstraction
first interface contract
required evidence
failure modes
```

### Product correction

Current best practice must not be rejected merely because it is current.

Use:

```text
retain durable current practices
reject only those that fail HPFA requirements
```

Examples of durable practices:

```text
stable identifiers
explicit contracts
append-only registries
fail-closed gates
regression tests
provenance
small deterministic functions
```

### Mandatory first question

```text
What capability must still be useful across providers, seasons, models and analyst workflows in ten years?
```

## Prompt 3 — Zero-Debt / Fail-Closed Auditor

Decision: `ACCEPT_WITH_MISSINGNESS_CLASSIFICATION`

### Core rule

No imputation is allowed for authority-critical or analysis-critical fields.

Missing fields must be classified:

```text
AUTHORITY_CRITICAL
ANALYSIS_CRITICAL
OPTIONAL_DIAGNOSTIC
DISPLAY_ONLY
```

Default behavior:

```text
AUTHORITY_CRITICAL -> FAIL_CLOSED
ANALYSIS_CRITICAL -> FAIL_CLOSED or REVIEW_REQUIRED by contract
OPTIONAL_DIAGNOSTIC -> DEGRADED with explicit missing report
DISPLAY_ONLY -> continue without semantic promotion
```

### Required audit format

```text
Kritiklik
Neden
Minimal Fix
Ideal Fix
Priority
Impact
Migration Cost
Required Test
Release Effect
```

### Resource discipline

Every implementation proposal must state:

```text
memory behavior
I/O behavior
materialization policy
streaming or batch mode
cache policy
phone/runtime constraints
```

### Rejected behavior

```text
silent repair
implicit defaults
average-value substitution
model-generated authority fields
```

## Prompt 4 — Popperian Falsification and Caravaggio Contrast

Decision: `ADAPT_STRONGLY`

### Accepted capability

Every strong analytical claim candidate should carry:

```text
falsification condition
counter-scenario
withdrawal condition
missing evidence
alternative mechanism
```

### Rejected capability

Caravaggio cannot mean black-and-white epistemic certainty.

Event-only football evidence includes:

```text
missingness
sampling effects
provider variation
context dependence
uncertainty
```

Therefore the accepted Caravaggio interpretation is visual and editorial contrast:

```text
observed vs not observed
supported vs unsupported
eligible vs blocked
known vs unknown
```

Not:

```text
certainly working vs certainly failing strategy
```

### Fix correction

A faultline must not automatically produce a definitive fix.

Allowed output:

```text
intervention_option_candidate
expected benefit
trade-off
required validation
counter-scenario
withdrawal condition
```

## Prompt 5 — High-Value Synthesizer / Cognitive Load Manager

Decision: `ACCEPT_WITH_EVIDENCE_PRESERVATION`

### Standard output

```text
Current Limitation
Hidden Limitation
High-Value Finding
Runtime Impact
Decision
Next Product Action
Release Status
```

### Selection criteria

```text
decision relevance
evidence strength
materiality
counter-evidence importance
novelty relative to baseline
claim safety
future reuse
```

### Hard rule

Contradictory or disconfirming evidence must never be removed solely to simplify the summary.

### Rejected behavior

```text
compression that removes uncertainty
executive summaries that hide blockers
strong language replacing missing evidence
```

## Unified orchestration pipeline

```text
1. Product gap declaration
2. Current hpfa search
3. Existing capability overlap check
4. Donor capability scan when required
5. Risk-tier assignment
6. Independent role critiques
7. Falsification and counter-scenario pass
8. High-value synthesis
9. HPFA-native architecture decision
10. Decision log and risk register
11. Test and runtime evidence plan
12. Release-status decision
```

## Risk tiers

### R0 — Editorial

```text
document wording
typo
non-semantic formatting
```

### R1 — Local implementation

```text
isolated utility
non-shared parser helper
local report formatter
```

### R2 — Shared product contract

```text
shared validation
schema
registry
cross-module interface
identity behavior
```

### R3 — Authority and claim critical

```text
runtime authority
canonical promotion
claim eligibility
AI provenance
release status
failure propagation
imputation policy
```

## Required artifacts by risk

```text
R0:
  change record

R1:
  tests + minimal risk note

R2:
  architecture decision log + regression + integration plan

R3:
  architecture decision log + risk register + multi-role review + integration evidence + runtime evidence requirement
```

## AI reuse boundary

AI may generate critiques, alternatives and research candidates.

AI may not:

```text
promote match truth
fill authority-critical fields
remove blockers
invent test evidence
promote release status
```

AI-assisted outputs must preserve:

```text
source evidence refs
claim ceiling
review state
falsification condition
counter-scenario
human or gate decision
```

## Current application to HPFA

### PR #145

Risk tier: `R3`

Reason:

```text
cross-module failure propagation
claim-safety impact
downstream argument prevention
```

Required before merge:

```text
direct test execution or CI evidence
review feedback closure
no regression in existing fusion tests
```

### Recursive forbidden-field guard

Risk tier: `R3`

Required architecture:

```text
shared path-aware scanner
module-local decision vocabulary
nested list/dict coverage
no silent field deletion
```

### Canonical domain interface registry

Risk tier: `R2`

Required architecture:

```text
domain ownership
input artifact
output artifact
claim ceiling
failure state
review state
authority dependency
downstream consumers
```

## Tests required

```text
test_risk_tier_requires_expected_artifacts
test_r3_decision_requires_risk_register
test_r3_decision_requires_falsification_condition
test_summary_preserves_counter_evidence
test_authority_missingness_fails_closed
test_optional_missingness_degrades_explicitly
test_intervention_output_remains_candidate_only
test_ai_output_cannot_promote_release_state
test_no_sample_match_identity_leak
```

## Rejected ideas

```text
mandatory long debate for trivial changes
forced consensus
rejecting all current best practices by default
black-and-white football certainty
faultline to definitive fix
compression that hides uncertainty or contradiction
AI-generated execution evidence
```

## Accepted ideas

```text
risk-tiered role conflict
2035 reverse roadmap
fail-closed review
missingness classification
falsification conditions
counter-scenarios
high-value synthesis
resource-aware architecture
```

## Release readiness

```text
policy status: POLICY_CORRECTION_PASS
runtime capability: NONE
execution evidence: NOT_APPLICABLE
production release: false
```
