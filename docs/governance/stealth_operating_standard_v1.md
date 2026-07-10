# HPFA STEALTH Operating Standard V1

Status: `POLICY_CORRECTION_PASS`

## Purpose

`STEALTH` is the mandatory operating mode for all substantive HPFA work.

It does not replace existing governance. It composes the following standards into one execution discipline:

```text
Product Architect Evolution Protocol
Autonomous Review Orchestration Standard
Pareto Operating Standard
Lindy + Pareto Roadmap
ADAPT_NOT_COPY donor policy
ACTIVE_MATCH runtime authority
claim-safe fail-closed release discipline
```

## STEALTH definition

```text
S — Source Authority First
T — Traceability Before Interpretation
E — Evidence Before Expansion
A — Adapt, Never Transplant
L — Lindy + Leverage Prioritization
T — Tests Before Trust
H — Halt on Uncertainty
```

## S — Source Authority First

Every task begins with current `hpfa` main.

Required order:

```text
1. search current hpfa main
2. identify existing capability
3. identify overlap and debt
4. search donors only when a product gap remains
5. preserve runtime/active_single_match/current as sole match truth
```

Forbidden:

```text
donor repository treated as executable product
donor artifact treated as match truth
reference document promoted into authority
```

## T — Traceability Before Interpretation

Every product output must preserve a traceable chain:

```text
source role
source path or artifact id
input contract
transformation stage
output artifact
claim ceiling
review state
failure state
release state
```

No analytical sentence, score or report block may exist without a retraceable evidence route.

## E — Evidence Before Expansion

Do not add new modules merely because an idea is interesting.

Before expansion, prove:

```text
current module executes
contract is compatible
failure propagates
output is written
regression passes
analyst value is visible
```

Required evidence pair:

```text
engineering evidence
analyst evidence
```

A new feature is lower priority than closing an integration blocker in an existing reasoning path.

## A — Adapt, Never Transplant

Donor use follows:

```text
product gap
-> donor capability
-> source role
-> boundary
-> HPFA-native contract
-> HPFA-native implementation
-> tests
-> ACTIVE_MATCH evidence when required
```

Never copy donor modules or create runtime imports from donor repositories.

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
```

## L — Lindy + Leverage Prioritization

Prefer work that is likely to survive across:

```text
providers
seasons
models
analyst workflows
runtime environments
```

Prefer:

```text
stable identifiers
small deterministic modules
explicit contracts
append-only registries
provider-neutral schemas
shared validation utilities
thin orchestrators
portable JSON/TSV/text outputs
```

Prioritize work with the highest safe analyst and product value per unit of complexity.

## T — Tests Before Trust

No merge or release claim may rely on:

```text
mergeable=true
code inspection alone
written tests that were not executed
historical test evidence from a stale branch
```

Required distinctions:

```text
implementation_written
regression_tests_written
tests_executed
tests_passed
integration_evidence
ACTIVE_MATCH_evidence
production_release
```

These states must never be collapsed into a single `PASS` label.

## H — Halt on Uncertainty

When authority-critical, claim-critical or analysis-critical uncertainty is unresolved:

```text
status=FAIL_CLOSED or REVIEW_REQUIRED
decision=BLOCK or HOLD
prediction_allowed=false
release_promotion_allowed=false
```

Use:

```text
Eksik Veri/Bilinmiyor
canonical_event_count=UNKNOWN
requires later validation
```

Forbidden:

```text
silent imputation
semantic guessing
confidence inflation
state promotion
unsupported tactical truth
```

## Mandatory STEALTH execution record

Every substantive task records:

```text
STEALTH.S source authority checked
STEALTH.T traceability chain identified
STEALTH.E evidence requirement declared
STEALTH.A donor adaptation decision
STEALTH.L priority and reuse rationale
STEALTH.T test state
STEALTH.H halt/block state
```

## Risk-tier application

### R0 Editorial

```text
STEALTH applies in lightweight form.
Source and traceability checks remain mandatory.
```

### R1 Local implementation

```text
local tests
resource impact
minimal risk record
```

### R2 Shared contract

```text
architecture decision
cross-module compatibility
regression and integration plan
```

### R3 Authority / claim / release critical

```text
multi-role review
risk register
falsification condition
counter-scenario
executed tests
runtime evidence requirement
fail-closed behavior
```

## Mandatory answer structure under STEALTH

For substantive product work:

```text
Current Limitation
Hidden Limitation
High-Value Finding
Better Architecture
Migration Plan
Tests Required
Risk Register
Release Readiness
Next Product Action
```

## Current application

### PR #145

```text
S: current hpfa main checked
T: Packet -> Fusion downstream path identified
E: regression and execution evidence required
A: no donor code used
L: high-leverage cross-module failure protection
T: tests written, execution evidence missing
H: merge remains blocked
```

### PR #147

```text
S: existing ACTIVE_MATCH runtime path used
T: output manifest and hashes preserved
E: phone evidence pack requires Termux execution
A: no donor dependency
L: removes repeated operator steps and increases analyst productivity
T: tests written, not yet executed
H: draft and not releasable
```

## Rejected interpretations of STEALTH

`STEALTH` does not mean:

```text
hide work
skip documentation
avoid review
bypass governance
merge without evidence
conceal errors
reduce transparency
```

It means:

```text
quietly disciplined
minimal-noise
traceable
fail-closed
high-leverage
product-first execution
```

## Release status

```text
policy_status=POLICY_CORRECTION_PASS
runtime_capability=NONE
execution_evidence=NOT_APPLICABLE
production_release=false
```
