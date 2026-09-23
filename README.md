# HPFA — Hikmet Pınarbaş Football Analytics

HPFA is a match-agnostic football intelligence system built around observable evidence, explicit semantics, dependency control and claim governance.

Its objective is not to maximize metrics or labels. It is to convert available match surfaces into defensible football knowledge for a professional analyst.

## Core doctrine

```text
EVENT ⊂ ZFGV
ROW != EVENT TRUTH
EVENT != WHOLE OBSERVATION UNIVERSE
PROVIDER LABEL != PHYSICAL / TACTICAL TRUTH
MULTIFORMAT != INDEPENDENT EVIDENCE
SAME TIMESTAMP != TOTAL ORDER
COORDINATE != TRACKING
PROCESS LABEL != COACH INTENTION
RECURRENCE != CAUSALITY
MODEL OUTPUT != FACT
LLM TEXT != EVIDENCE
ABSENCE != COUNTEREVIDENCE
NO_VISIBLE_FOLLOWUP != FAILURE
```

The canonical evidence spine is:

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

## Observation model

HPFA is observation-capability-first, not event-only.

Supported observation families may include:

- ACTION / EVENT
- ENTITY / ACTOR
- TEMPORAL
- SPATIAL
- OUTCOME / QUALIFIER
- RELATIONAL
- PROCESS / PARTICIPATION
- AGGREGATE / TABULAR
- EXTERNAL CONTEXT
- HPFA-DERIVED INTELLIGENCE

Missing required observations must fail closed or downgrade the affected construct. Optional missing observations may degrade only the relevant construct.

Tracking and video are not mandatory dependencies. When they are unavailable, HPFA must not promote event-derived proxies into tracking-derived physical or tactical truth.

## Runtime authority

The sole physical single-match runtime authority is:

```text
runtime/active_single_match/current
```

The exact absolute device path is discovered and validated at execution time.

GitHub provides code, contracts, tests and CI evidence. CI success is not ACTIVE_MATCH evidence. ACTIVE_MATCH evidence is not production release.

Drive, Dropbox, academic literature, donor repositories and historical artefacts are support sources only.

## Repository structure

```text
hpfa/
  modules/
    core/          canonical product modules
    postmatch/     postmatch product modules when admitted

canon/             canonical registries and product-level semantic assets
configs/           provider-neutral runtime/configuration assets only
docs/
  contracts/       executable/product contracts
  governance/      authority, release and claim governance
tools/             maintained operator and ACTIVE_MATCH tools
ops/               maintained installation/bootstrap operations
.github/workflows/ engineering CI
tests/             repository-level tests
```

The product repository does **not** version:

- match packages;
- generated reports or charts;
- runtime output directories;
- quarantine copies;
- diagnostic snapshots;
- temporary inboxes;
- backup files;
- local operator logs;
- historical acceptance bundles;
- nested legacy repositories;
- donor research packs.

Those belong outside the product tree.

## Engineering rules

- `WIP=1`
- `ADAPT_NOT_COPY`
- `REHABILITATE_BEFORE_PARALLEL_ENGINE`
- `CODE_LAST`
- current producer before donor
- provider differences resolved at the boundary
- no team/player/match-name hardcoding in product logic
- no fixed row/event/episode count as product truth
- no sample-match path as a runtime default
- unknown remains UNKNOWN
- unresolved remains unresolved
- release states remain explicit

Before changing product code:

```text
problem
→ current producer
→ gap
→ observation requirement
→ source role
→ contract
→ admission
→ tests
→ ACTIVE_MATCH need
→ minimal code
→ real-match evidence
→ red team
→ release decision
```

## Release boundary

Unless explicitly admitted by the relevant owner:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

PASS is not release. Open PR is not main. Main is not production without the explicit release decision required by HPFA governance.
