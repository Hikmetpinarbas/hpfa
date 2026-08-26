# HPFA — Hikmet Pınarbaş Football Analytics

HPFA is an event-only, claim-safe Football Intelligence Platform. Its purpose is to turn visible match evidence into defensible analyst intelligence without promoting rows, labels, timestamps, metrics, or model outputs beyond the evidence that supports them.

## Authority

- Product repository: `Hikmetpinarbas/hpfa`
- ACTIVE_MATCH truth: `runtime/active_single_match/current`
- The absolute Termux path is discovered and verified at execution time; it is not product authority.
- Drive, Dropbox, donor repositories, PDFs, academic sources, historical PRs and old runtime artefacts are support/reference sources only.

## Core product model

```text
RAW / SURFACE
→ source authority
→ ACTIVE_MATCH
→ readers / provider semantics
→ reflection control
→ Row Nucleus
→ Evidence Atom
→ match-local identity candidates
→ semantic roles / action candidates
→ partial order / time
→ consequence
→ context
→ Analyst Episode
→ Episode Features
→ Change
→ Recurrence / Variation / Deviation
→ Counterevidence / Falsifier
→ Metric / Model candidates
→ Defeasible Finding
→ Analyst Report Block
```

This is a conceptual DAG. A node that is not implemented and admitted must not be presented as current product truth.

## Current safety locks

Unless an explicit upstream gate proves otherwise:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Event-only evidence does not directly prove team shape, defensive-line height, compactness, pitch control, off-ball structure, body orientation, scanning, physical load/fatigue, coach intention, tactical plan, dominance, or causality.

## Engineering rules

- `ADAPT_NOT_COPY`
- `REHABILITATE_BEFORE_PARALLEL_ENGINE`
- `CODE_LAST`
- current `hpfa` producer/contracts/tests before donor code
- same SHA on multiple paths is duplicate reflection/lineage, not independent evidence
- CSV/XML reflections from the same upstream fact are not independent football votes
- numeric time is not chronology without semantic-role/unit/clock-basis/period/provenance admission
- same timestamp does not create internal order
- source row order is provenance only
- upstream FAIL_CLOSED contracts downstream permission
- product code is match-agnostic; sample match identity leakage is forbidden

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

**Analyst evidence** records what is visible, where/when it is visible, supporting evidence, counterevidence, safe meaning, forbidden inference and analyst action.

`CI SUCCESS != ACTIVE_MATCH EVIDENCE` and `MERGED != PRODUCTION_RELEASE`.

## Release vocabulary

Use explicit states such as:

```text
DISCOVERY_PASS_PLAN_ONLY
SPEC_ONLY
SMOKE_PASS
REVIEW_REQUIRED
FAIL_CLOSED
RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND
ACTIVE_MATCH_EVIDENCE_PASS
PRODUCTION_RELEASE
```

PASS is not release.

## Current development direction

Correctness debt that blocks downstream reasoning must be closed before capability growth. New intelligence should extend the existing evidence spine instead of creating parallel engines. Priority families are evidence dependency/independence, counterevidence/falsification, episode reliability, change, recurrence/variation/deviation, and safe findings.

## Operator rule

Before changing product code:

```text
problem
→ current producer
→ gap
→ source role
→ contract
→ admission rule
→ invariants/tests
→ ACTIVE_MATCH need
→ smallest coherent change
→ engineering evidence
→ analyst evidence
→ red-team
→ release decision
```

A new capability is justified only when it closes a real gap in the existing evidence spine and gives the analyst a new defensible piece of football intelligence.
