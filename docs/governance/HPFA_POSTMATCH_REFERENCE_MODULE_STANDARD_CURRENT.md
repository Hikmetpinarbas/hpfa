# HPFA Postmatch Reference Module Standard — Current

Status: CURRENT ARCHITECTURE STANDARD  
Reference product: Single-Match Postmatch  
Canonical repository: `Hikmetpinarbas/hpfa`

## Decision

All HPFA analytical product modules take their architectural example from Postmatch.

Postmatch is the reference implementation for **how an HPFA module is built, governed, tested, admitted and presented to the analyst**. Other modules do not copy Postmatch football questions or outputs blindly; they inherit its product discipline and evidence architecture.

This rule applies to:

- Prematch;
- Scouting;
- Player / Team Compare;
- Longitudinal / Season / Trends;
- Reporting products;
- future analyst-facing football intelligence modules.

No module may introduce a parallel evidence engine, parallel truth model, parallel claim grammar or incompatible module topology when Postmatch already defines the applicable pattern.

## Reference pattern

A professional HPFA analytical module should converge on the following internal shape when applicable:

```text
<module>/
├── README.md
├── contracts/
│   ├── input_contract_v*.json
│   └── output_contract_v*.json
├── src/
│   ├── admission / capability discovery
│   ├── football intelligence construction
│   ├── counterevidence / uncertainty handling
│   └── analyst-output assembly
└── tests/
    ├── contract tests
    ├── football-behaviour tests
    ├── truth-boundary tests
    └── regression tests
```

Folders are not mandatory merely for visual symmetry. The architecture is semantic: each concern must have one clear owner and one testable contract.

## Shared evidence spine

Every module inherits the HPFA evidence spine used by Postmatch:

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

A module may start later in the spine only when it consumes already-admitted upstream objects. It may not skip required epistemic stages and then recreate truth from presentation data.

## Shared football-product method

Postmatch remains the reference flow:

```text
Observation
→ Episode / Process
→ Context
→ Consequence
→ Recurrence / Variation / Deviation
→ Counterevidence
→ Safe Finding
→ Human Analyst Output
```

Minimum analytical shape:

```text
Evidence
→ Episode / Process
→ Successful / Failed / Deviant Variant
→ Counterevidence
→ Safe Finding
→ Analyst Output
```

Other modules adapt this to their own estimand and time horizon.

### Prematch adaptation

```text
Historical / current evidence
→ recurring opponent/team process
→ context and matchup condition
→ variation / failure cases
→ counterevidence
→ reviewable match hypothesis
→ analyst watchpoint
```

Prematch must not convert historical recurrence into target-match fact or causal prediction.

### Scouting adaptation

```text
Admitted player observations
→ role-relevant process participation
→ opportunity / execution context
→ reference population
→ variation and limitations
→ counterevidence
→ safe player finding
→ analyst decision support
```

Position != role. Similarity != quality. Similarity != replacement truth.

### Longitudinal adaptation

```text
Repeated admitted match observations
→ stable construct definition
→ comparable observation unit
→ change / recurrence / deviation
→ context and dependency burden
→ counterevidence
→ safe trend finding
→ analyst interpretation
```

Trend != causality. Recent form != future truth.

### Reporting adaptation

Reporting consumes admitted findings. It does not create new football evidence or strengthen the claim ceiling.

## Shared Safe Finding contract

Where a module emits analyst-facing findings, the Postmatch Safe Finding structure is the default reference:

- WHAT_VISIBLE
- SUPPORT
- COUNTEREVIDENCE
- SAFE_MEANING
- FORBIDDEN_INFERENCE
- UNCERTAINTY
- WITHDRAWAL_CONDITION
- ANALYST_ACTION

The exact field names may differ only when the target module has a justified domain-specific need. The semantic responsibilities may not disappear.

## Shared truth locks

All modules inherit Postmatch truth locks:

- ROW != EVENT TRUTH
- EVENT != WHOLE OBSERVATION UNIVERSE
- PROVIDER LABEL != PHYSICAL / TACTICAL TRUTH
- AGGREGATE != ACTION IDENTITY
- MULTIFORMAT != INDEPENDENT EVIDENCE
- SAME TIMESTAMP != TOTAL ORDER
- COORDINATE != TRACKING
- PROCESS LABEL != COACH INTENTION
- RECURRENCE != CAUSALITY
- MODEL OUTPUT != FACT
- LLM TEXT != EVIDENCE
- ABSENCE != COUNTEREVIDENCE
- NO_VISIBLE_FOLLOWUP != FAILURE

These are repository-wide rules, not Postmatch-only rules.

## Shared source and observation model

Every module uses the same ZFGV observation universe. EVENT is one family inside ZFGV, not the whole product.

Required observation families are declared by the football question. Missing required observations cause FAIL_CLOSED / DOWNGRADE / REVIEW_REQUIRED / UNOBSERVABLE_WITH_CURRENT_DATA as appropriate. Optional missing observations degrade only the affected construct.

Tracking and video remain optional external surfaces, never mandatory dependencies for HPFA product execution.

## Shared engineering discipline

Every new module follows the Postmatch development order:

```text
football problem
→ current owner
→ real gap
→ observation requirement
→ source role
→ contract
→ admission
→ tests
→ ACTIVE_MATCH / real-match need
→ minimal code
→ football evidence
→ Red Team
```

Additional rules:

- WIP = 1;
- REHABILITATE_BEFORE_PARALLEL_ENGINE;
- ADAPT_NOT_COPY;
- CODE LAST;
- one capability = one current owner;
- donor repository code is never imported as a parallel runtime dependency;
- a new module must reuse current core owners before creating local duplicates.

## Shared analyst-output standard

The analyst should experience different HPFA modules as one product family.

Each output answers, in football language:

1. What was observed?
2. What process / mechanism is visible?
3. What context changes the meaning?
4. What consequence or decision relevance exists?
5. What counterevidence weakens the finding?
6. What remains unknown or unobservable?
7. What should the analyst inspect, compare or watch next?

Implementation vocabulary stays behind the analyst interface unless decision-critical.

## What Postmatch is NOT used for

Postmatch is not a template for blindly copying:

- Postmatch-specific metrics;
- single-match denominators into season/scouting contexts;
- phase labels unsupported by another module's observations;
- event-derived proxies into tracking truth;
- report wording into different decision contexts;
- module names, version names or historical donor naming.

The transferable asset is the professional architecture and epistemic discipline.

## Repository consequence

When Prematch, Scouting, Longitudinal, Compare or another product lane becomes active, its first design question is:

> How does Postmatch solve the equivalent ownership, contract, evidence, uncertainty, counterevidence, testing and analyst-output problem?

Only the domain-specific delta is newly designed.

This standard supersedes any donor or historical design that creates an independent analytical architecture beside Postmatch.
