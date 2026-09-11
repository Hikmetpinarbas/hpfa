# HPFA — Hikmet Pınarbaş Football Analytics

HPFA is a claim-safe Football Intelligence Platform built on **Enriched Football Observation Data** (`Zenginleştirilmiş Futbol Gözlem Verisi`). Its purpose is to turn visible match evidence into defensible analyst intelligence without promoting rows, labels, timestamps, coordinates, participation tags, metric surfaces, or model outputs beyond the evidence that supports them.

`event-only` is retained only as a legacy/source-class description where historically necessary. It is **not** the product's global observation ceiling.

HPFA observation capacity is admitted construct-by-construct from the fields and relationships actually visible in the current match surfaces. Depending on upstream admission, these surfaces may expose action, temporal, spatial, relational/co-occurrence, process/context, consequence/response, and reconstructed state-transition candidates. Tracking/video remains required only for constructs whose physical or off-ball truth cannot be established from the admitted observation surface.

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
→ temporal + spatial + relational observation admission
→ partial order / time
→ consequence / response
→ context / process participation
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

## Observation capacity model

HPFA must not decide claim capacity from a binary `event-only / tracking` label. Each construct declares the minimum admitted observation surface it needs.

```text
L0  Aggregate surface
L1  Action observation
L2  Temporal observation
L3  Spatial observation
L4  Relational / co-occurrence observation
L5  Process / context observation
L6  Consequence / opponent-response observation
L7  Reconstructed state-transition candidate
L8  Tracking/video-required physical or off-ball state
```

A construct may use any admitted lower/equal layer. Higher-layer truth must not be inferred from a lower layer without an explicit gate.

Examples:
- action-location progression may be available at L3 without tracking;
- same-process multi-player participation may be available at L4/L5 when identity/reflection/time gates admit it;
- visible opponent-response latency candidates may be available at L6 when occurrence/process binding and temporal admission support them;
- true player speed, true pressure geometry, compactness, body orientation and off-ball team shape remain L8 unless an explicit tracking/video source is admitted.

## Current safety locks

Unless an explicit upstream gate proves otherwise:

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

No observation layer directly proves more than its admitted construct. In particular, current non-tracking surfaces do not directly prove true player/ball speed, team shape, defensive-line height, compactness, pitch control, off-ball structure, body orientation, scanning, physical load/fatigue, coach intention, tactical plan, dominance, or causality.

## Engineering rules

- `ADAPT_NOT_COPY`
- `REHABILITATE_BEFORE_PARALLEL_ENGINE`
- `CODE_LAST`
- current `hpfa` producer/contracts/tests before donor code
- same SHA on multiple paths is duplicate reflection/lineage, not independent evidence
- CSV/XML/XLSX reflections from the same upstream fact are not independent football votes
- numeric time is not chronology without semantic-role/unit/clock-basis/period/provenance admission
- same timestamp does not create internal order
- source row order is provenance only
- spatial coordinates require source semantics, pitch frame and direction admission before directional football claims
- multi-row/multi-surface co-occurrence requires reflection and identity reconciliation before relational truth
- upstream FAIL_CLOSED contracts downstream permission
- product code is match-agnostic; sample match identity leakage is forbidden
- do not globally block a construct merely because it is richer than a traditional event feed; instead evaluate the exact admitted observation surface it requires

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

Correctness debt that blocks downstream reasoning must be closed before capability growth. New intelligence should extend the existing evidence spine instead of creating parallel engines. Priority families are observation-capacity admission, evidence dependency/independence, temporal/spatial/relational reconstruction, counterevidence/falsification, episode reliability, change, recurrence/variation/deviation, and safe findings.

## Operator rule

Before changing product code:

```text
problem
→ current producer
→ gap
→ source role
→ observation surface / required layer
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
