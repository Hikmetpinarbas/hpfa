# HPFA — Hikmet Pınarbaş Football Analytics

HPFA is a ZFGV/EFOD-based, claim-safe Football Intelligence Platform. ZFGV is a multi-surface Football Observation Fabric: event/action evidence is one observation family inside the product, not the whole observation universe. HPFA turns admitted football observations into defensible analyst intelligence without promoting rows, provider labels, timestamps, aggregates, metrics, model outputs, or derived narratives beyond the evidence that supports them.

## Authority

- Product repository: `Hikmetpinarbas/hpfa`
- ACTIVE_MATCH truth: `runtime/active_single_match/current`
- The absolute Termux path is discovered and verified at execution time; it is not product authority.
- Drive, Dropbox, donor repositories, PDFs, academic sources, historical PRs and old runtime artefacts are support/reference sources only.

## Canonical observation model

```text
event ⊂ ZFGV
ZFGV != event
```

Observation families include:

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
TRACKING / VIDEO — only when genuinely available
HPFA-DERIVED INTELLIGENCE
```

Global `event-only compatible?` is not a product admission question. The product asks which observation capabilities a football construct requires and whether those capabilities are actually admitted:

```text
required_capabilities ⊆ admitted_capabilities
```

A missing capability must fail closed, downgrade, abstain, or explicitly require external/tracking/video evidence. ZFGV does not create an unlimited claim ceiling.

## Core product model

```text
SOURCE
→ SURFACE
→ OBSERVATION
→ SEMANTICS
→ IDENTITY / DEPENDENCY
→ TIME / SPACE ADMISSION
→ RELATION
→ EPISODE / PROCESS
→ CONTEXT
→ CONSEQUENCE
→ FEATURE
→ METRIC / MODEL
→ SIGNAL
→ HYPOTHESIS
→ COUNTEREVIDENCE
→ FINDING
→ CLAIM
→ ANALYST OUTPUT
```

This is a conceptual DAG. A node that is not implemented and admitted must not be presented as current product truth. A downstream node may not create truth that upstream evidence does not permit.

## Current safety locks

Unless an explicit upstream gate proves otherwise:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Non-tracking observations do not directly prove true team shape, defensive-line height, compactness, pitch control, off-ball geometry/options/runs, body orientation, scanning, true physical speed/load, true pressure geometry, coach intention, tactical plan, dominance, or causality. Provider labels do not override these locks.

## Engineering rules

- `ADAPT_NOT_COPY`
- `REHABILITATE_BEFORE_PARALLEL_ENGINE`
- `CODE_LAST`
- current `hpfa` producer/contracts/tests before donor code
- same SHA on multiple paths is duplicate reflection/lineage, not independent evidence
- CSV/XML reflections from the same upstream fact are not independent football votes
- aggregate/tabular surfaces are valuable observations but do not create action identity
- numeric time is not chronology without semantic-role/unit/clock-basis/period/provenance admission
- same timestamp does not create internal order
- source row order is provenance only
- coordinates require admitted semantics/pitch frame/direction before spatial claims
- process/participation labels do not create possession truth, tactical plan or coach intention
- upstream FAIL_CLOSED contracts downstream permission
- product code is match-agnostic; sample match identity leakage is forbidden

## Event-only migration

The historical event-only doctrine is retired as a global product ontology. Existing references are classified before modification:

```text
GLOBAL_ERROR
LEGITIMATE_EVENT_TERM
LEGACY_IDENTIFIER
HISTORICAL
```

Event-specific modules remain valid where the construct is genuinely event-specific. Legacy identifiers are not blindly renamed. Old global gates are rehabilitated into construct-specific ZFGV capability requirements while claim locks are preserved.

Current migration records:

- `docs/governance/HPFA_EVENT_ONLY_MIGRATION_LEDGER_V1.json`
- `docs/governance/HPFA_ZFGV_RETROACTIVE_CAPABILITY_RECOVERY_MAP_V1.md`

## Repository map

- `hpfa/modules/core/` — canonical product modules
- `docs/contracts/` — machine/product contracts
- `docs/governance/` — authority, claim and release governance
- `tools/` — operator and ACTIVE_MATCH execution tools
- `.github/workflows/` — engineering CI; CI is not ACTIVE_MATCH evidence
- root Python files — compatibility/entry wrappers; canonical implementations live under `hpfa/modules/core/`

## Runtime evidence

Every real run must preserve two distinct evidence layers.

**Engineering evidence** records code head, runtime authority, inputs, execution status, outputs, failures and integrity.

**Analyst evidence** records what is visible, where/when it is visible, supporting evidence, context, counterevidence, alternative explanations, safe meaning, forbidden inference, uncertainty, withdrawal condition and analyst action.

`CI SUCCESS != ACTIVE_MATCH EVIDENCE` and `MERGED != PRODUCTION_RELEASE`.

## Release vocabulary

Use explicit states such as:

```text
DISCOVERY_PASS_PLAN_ONLY
SPEC_ONLY
IMPLEMENTED
TESTED
SMOKE_PASS
PARTIALLY_VALIDATED
REVIEW_REQUIRED
FAIL_CLOSED
ACTIVE_MATCH_EVIDENCE_PASS
RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
PRODUCTION_RELEASE
```

PASS is not release.

## Current development direction

Postmatch is the current reference product. The main development direction is ZFGV retroactive rehabilitation plus professional finding closure:

```text
Observation
→ Episode / Process
→ Context
→ Consequence
→ Successful / Failed / Deviant Variant
→ Recurrence / Variation / Deviation
→ Counterevidence
→ Safe Finding
→ Human Analyst Report
```

The success measure is not metric or module count. It is the quality of defensible analyst findings produced from admitted evidence.

## Operator rule

Before changing product code:

```text
problem
→ current producer
→ real gap
→ required observation capability
→ available surface
→ source role
→ contract
→ admission rule
→ invariants/tests
→ ACTIVE_MATCH need
→ smallest coherent change
→ engineering evidence
→ analyst evidence
→ falsification / counterevidence
→ release decision
```

A new capability is justified only when it closes a real gap in the existing evidence spine and gives the analyst a new defensible piece of football intelligence.
