# HPFA Pareto Operating Standard V1

Status: `POLICY_CORRECTION_PASS`

## Purpose

HPFA uses the Pareto principle as a formal operating standard for analysis, product development, donor exploitation, testing, audit and release decisions.

The objective is not to do less work. The objective is to identify the small set of actions that create the largest analyst value, reliability gain and product leverage.

## Core rule

```text
Prioritize the smallest set of evidence, modules, fixes and product decisions that produces the largest safe analytical gain.
```

80/20 is a prioritization heuristic, not a truth claim and not a license to ignore required safety, authority or validation gates.

## Non-negotiable boundaries

Pareto prioritization cannot override:

```text
ACTIVE_MATCH runtime authority
claim-safety gates
canonical source authority
required contracts
required regression tests
flat phone output policy
match-agnostic implementation
release-status evidence
```

A high-impact feature that violates a hard boundary is not a Pareto win. It is rejected or deferred.

## Standard decision question

Before analysis or development, ask:

```text
Which 20 percent of available evidence or work will produce roughly 80 percent of the safe analyst or product value?
```

Then ask:

```text
What is the minimum complete evidence set required to avoid a misleading conclusion?
```

## Pareto score

Every proposed work item should be evaluated with:

```text
Pareto Leverage Score =
(Analyst Value + Product Reuse + Reliability Gain + Integration Leverage)
/
(Implementation Cost + Maintenance Cost + Claim Risk + Dependency Risk)
```

The score is comparative, not absolute. It ranks work; it does not create release truth.

## Analysis standard

For match and player analysis, prioritize:

```text
1. decisive evidence families
2. repeated high-value patterns
3. major contradictions
4. context that materially changes interpretation
5. evidence gaps that could reverse the reading
```

Do not spend equal analytical space on every available metric.

Recommended output order:

```text
A. highest-impact observed behaviours
B. strongest supporting evidence
C. most important counter-evidence
D. analyst meaning
E. secondary detail
F. technical limits
```

The main text should communicate the few findings that explain most of the match or player profile. Supporting detail remains traceable in evidence blocks or appendices.

## Development standard

Prefer work that improves multiple downstream modules.

High-leverage examples:

```text
failure propagation
recursive forbidden-field scan
canonical field contract
shared evidence identity
end-to-end integration fixture
runtime evidence ledger
contradiction routing
```

Lower-leverage examples when the spine is incomplete:

```text
one more isolated metric
one more reader with no downstream consumer
one more report template
one more visualization without a registry contract
```

## Donor exploitation standard

Search donors from a declared product gap, not from curiosity.

```text
main product gap
-> donor search query
-> unique donor capability
-> HPFA-native contract
-> tests
-> integration
-> runtime evidence
```

Prioritize donor capabilities that:

```text
solve a current P0/P1 gap
serve multiple modules
reduce false claims
improve contradiction or evidence reasoning
remove repeated implementation
```

Do not copy donor code merely because it exists.

## Testing standard

Prioritize tests that protect the largest failure surface.

First-tier tests:

```text
upstream fail-closed propagation
nested forbidden output rejection
standard field-name compatibility
end-to-end producer-consumer compatibility
canonical_event_count protection
sample identity leak
phone output-root policy
```

Unit tests remain required, but cross-module failures receive higher priority because they can corrupt the whole pipeline.

## Backlog standard

Each backlog item should have:

```text
analyst_value
product_leverage
reuse_scope
claim_risk
integration_risk
effort
priority_decision
```

Priority decisions:

```text
DO_NOW
DO_NEXT
DEFER
REJECT
```

Default interpretation:

```text
DO_NOW = high leverage, current blocker or multi-module gain
DO_NEXT = useful after current blocker closes
DEFER = valid but low current leverage
REJECT = duplicate, unsafe, unsupported or outside product authority
```

## Release standard

Pareto does not mean incomplete release.

A module may be high impact but still remain:

```text
SPEC_ONLY
SMOKE_PASS
REVIEW_REQUIRED
RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
```

Production release still requires the declared evidence and runtime gates.

## Analyst evidence requirement

Every high-priority development item must explain:

```text
what analyst problem it solves
which output becomes more useful
which misleading interpretation it prevents
which downstream modules benefit
```

## Engineering evidence requirement

Every high-priority development item must record:

```text
implementation status
test status
integration status
output status
claim boundary
release status
```

## Current HPFA application

For the current Intelligence Layer, Pareto priority is:

```text
1. close cross-module failure propagation
2. unify recursive forbidden-field protection
3. declare the canonical defeasible argument route
4. add one end-to-end Intelligence Chain fixture
5. build the orchestrator only after 1-4
```

This sequence has greater product leverage than adding more isolated readers, metrics or registries.

## Final rule

```text
Do not optimize for number of modules.
Optimize for safe analyst value per unit of complexity.
```
