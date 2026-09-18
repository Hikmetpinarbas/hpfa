# HPFA Research Package Adoption Ledger — 2026-09-16

Status: CURRENT FRONTIER SUPPORT / WIP=1 GOVERNANCE
Repository: `Hikmetpinarbas/hpfa`
Frontier inspected before this ledger: PR #359 / `feature/zfgv-action-grammar-synced-v1` @ `a25dbe2365d2b68cc556a2f16a00b9ed4882e066`
Reference product: single-match POSTMATCH

This ledger converts the supplied research package into product work without treating donor text, external models, one-match thresholds or generated code as product truth.

Canonical locks remain unchanged:
- `EVENT ⊂ ZFGV`; `EVENT != ZFGV`
- `ROW != EVENT TRUTH`
- `PROVIDER LABEL != PHYSICAL/TACTICAL TRUTH`
- `MULTIFORMAT != INDEPENDENT EVIDENCE`
- `SAME TIMESTAMP != TOTAL ORDER`
- `COORDINATE != TRACKING`
- `PROCESS LABEL != COACH INTENTION`
- `RECURRENCE != CAUSALITY`
- `MODEL OUTPUT != FACT`
- `LLM TEXT != EVIDENCE`
- `ABSENCE != COUNTEREVIDENCE`
- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

## Collision check against current frontier

The research package contains useful ideas, but several reported gaps are already closed or partially closed on the current frontier and must not be reimplemented.

### ALREADY_FIXED / DO NOT DUPLICATE

1. Same-time label collapse / Action Grammar occurrence reconstruction.
   - Current Action Grammar already collapses reviewed co-located semantic labels into occurrence candidates.
   - Same timestamp does not create total order.

2. Right-censoring baseline and `NO_VISIBLE_FOLLOWUP != FAILURE`.
   - `occurrence_consequence_projection_v1` already distinguishes observation-boundary censoring, complete-to-horizon no-followup and unresolved follow-up.
   - Safe Finding challenge logic already treats unresolved horizon/censoring as downgrade material.

3. Process/participation as non-event context.
   - Current ZFGV doctrine and process participation adapters already reject global event-only routing.
   - Any remaining route-specific leakage must be fixed in the current owner, not by a new process engine.

4. Spatial provider attack-axis convention.
   - Physical ACTIVE_MATCH already admitted provider team-relative attack direction `ATTACK_POS_X` on the accepted spatial slice.
   - `pitch_frame` remains `UNKNOWN`; no fixed-pitch mirror transform is admitted.

5. Safe Finding evidence-profile binding.
   - Eligible denominator, independent-support state, episode/context/actor spread and challenge surface are now directly validated before EMIT consideration.

## NOW — current WIP=1

### R1 — Construct-specific temporal consequence contract

**Real gap**

Current consequence production still carries one global search grid:
`WINDOW_SECONDS = (5.0, 8.0, 12.0)` with a fixed follow-up layer cap. The current downstream projection can test sensitivity and censoring, but the upstream producer still applies the same temporal search envelope to every action family.

The supplied research package independently converges on the same structural conclusion: a global fixed-time horizon is not a valid universal football contract. However, the package is single-match evidence and therefore does **not** authorize a production numeric threshold per family.

**Product objective**

Rehabilitate the existing consequence producer so temporal admissibility is construct-aware and auditable:

`ANCHOR FAMILY -> TEMPORAL CONTRACT CLASS -> ELIGIBLE FOLLOW-UP SEMANTICS -> TERMINAL RULE -> CENSORING STATE -> SENSITIVITY EVIDENCE -> CLAIM CEILING`

**No new engine.** Current owners first:
- `hpfa/modules/core/trackable_action_consequence_candidates_lite/`
- `hpfa/modules/core/active_match_spine_runner/src/occurrence_consequence_projection.py`
- existing temporal-relation and episode-boundary producers.

**First implementation rule**

Do not hard-code the research package's single-match observed windows as production truth. The first rehabilitation should separate:
- pre-specified diagnostic sensitivity grid,
- construct-specific temporal contract requirement,
- event/terminal-driven stop conditions,
- observation cutoff/censoring,
- production-calibrated horizon (currently `UNAVAILABLE` / `CALIBRATION_REQUIRED`).

A missing construct contract may preserve diagnostic visibility but cannot silently authorize a stronger claim.

**Tests required before runtime**
- one global grid cannot be represented as a production-authoritative contract for every construct;
- changing a diagnostic grid cannot silently increase claim ceiling;
- same-time rows still cannot create order;
- period/match boundary remains censoring, not failure;
- terminal condition stops eligible consequence search where the construct contract says it is terminal;
- missing construct contract fails closed or downgrades without deleting visible evidence;
- no numeric family threshold is admitted from this single match.

**Analyst gain**

The analyst can distinguish “no visible consequence inside this construct's admitted observation process” from “failure”, and avoid attaching a later, different football process to the original action merely because it fell inside a universal time window.

## NEXT

### R2 — Explicit dependency/reflection burden, not only independence booleans

Current Safe Finding carries `dependency_independence_proven` / `statistical_independence_proven`, but the research package correctly identifies analyst value in seeing the burden itself.

Inspect the current evidence graph / reflection / sequence lineage first. If no equivalent field already exists, add an explicit non-compensating burden profile such as:
- reflection-group burden,
- derived-from-same-occurrence burden,
- aggregate-reconciliation burden,
- unresolved dependency-group burden.

This profile must never be converted into a single confidence score.

### R3 — Censoring/unresolved burden propagation into the evidence profile

Basic censoring semantics are already present. The remaining question is whether Safe Finding receives an explicit burden vector, rather than only downstream challenge reasons.

Inspect first; rehabilitate only if the burden is not already directly lineage-bound.

### R4 — First eligible consequence vs targeted consequence estimand

Adopt as a contract distinction, not a causal model:
- `FIRST_ELIGIBLE_CONSEQUENCE` for immediate bounded continuation / terminal resolution;
- `TARGET_CONSEQUENCE_WITHIN_H` only for explicitly declared target questions with their own eligibility and censoring contract.

Reject `ALL_ELIGIBLE_CONSEQUENCES_WITHIN_H` as a default because it can double-count downstream events and contaminate process identity.

### R5 — Terminal-driven consequence search

Research strongly supports event-driven termination over time-only search. Before coding, inspect current terminal support and `football_episode_boundary` ownership. If intervening terminal events are not actually stopping consequence eligibility, rehabilitate the existing producer.

### R6 — Provider-label semantic audit: goal-kick/deep-distribution family

Research package reports provider rows where “Goal kicks short/medium/long” labels may appear on outfield actors. Treat this as a semantics/admission audit candidate, not as proof that every such label is physically wrong.

Required before change:
- actor role admission,
- anchor coordinate semantics,
- provider label role,
- active-match evidence.

Never infer physical restart truth from label text alone.

## SUPPORT

### S1 — Minimal OpenLineage-style dependency envelope

Use only the principle: source/surface/observation/derived-object lineage and explicit dependency kind. Do not copy donor payloads or add an external runtime dependency unless a current HPFA owner cannot express the needed edges.

### S2 — Pandera/Pydantic-style contract discipline

Use the principle of explicit required fields, semantic checks, dependency prerequisites, aggregated failures and fail-closed admission. Prefer current HPFA contracts/tests; do not add a validation framework merely because the donor exists.

### S3 — Seq2Pat-style contrastive pattern principle

Constraint-based and success/failure discriminative sequence comparison is potentially useful after the single-match reference product has stable comparison eligibility, denominator, independence and Safe Finding output. Concept donor only for now.

### S4 — Exposure accounting / survival terminology

Eligible opportunity accounting and censoring terminology are useful. Full survival/hazard modelling is not justified for the current single-match product.

## LATER

- multi-match temporal calibration and stable production horizons;
- Bayesian/shrinkage priors;
- conformal uncertainty calibration;
- HMM/change-point modelling;
- xT/VAEP-style learned value models beyond provider-model support;
- Hawkes/Lomb-Scargle rhythm modelling;
- cross-match fingerprints / stability-weighted deviation;
- Seq2Pat execution after stable Gold Corpus and comparison contracts.

These may become research or model surfaces later; none are current product truth.

## REJECT / DO NOT TRANSFER AS WRITTEN

1. Full PM4Py/process-mining engine transfer.
   - Violates `REHABILITATE_BEFORE_PARALLEL_ENGINE`; donor licensing and event-log assumptions are unnecessary for the current product.

2. Z3/NetworkX/ruptures/lifelines as new NOW engines.
   - Current gaps are contract/admission/lineage gaps, not algorithm availability gaps.

3. Arbitrary family time thresholds copied from the single-match research package.
   - The observed latency bands are calibration evidence, not production truth.

4. Per-match horizon cherry-picking to maximize a preferred result.

5. Single confidence/composite score that compensates denominator, dependency, censoring, spread or counterevidence against each other.

6. Deterministic fixed-pitch mirror transform from the research package while `pitch_frame=UNKNOWN`.
   - Current accepted capability is provider attack-axis convention, not pitch-absolute geometry.

7. Supplied `zgfv_pipeline.py` as a product code donor.
   - It contains exploratory assumptions (including naive PPDA/event counting) that do not satisfy current occurrence/dependency/spatial admission contracts. Conceptual experiments may be mined, code is not product-admissible.

## STALE / HISTORICAL CLAIMS IN THE PACKAGE

Any statement that HPFA is globally “event-only”, lacks same-time collapse, lacks censoring semantics, or has no Safe Finding evidence-profile gate is stale against the current frontier.

Any research document that inspected an older public commit or did not have the current PR/ACTIVE_MATCH package is SUPPORT/HISTORICAL, not product authority.

## Work order

WIP remains 1.

1. `R1 Construct-specific temporal consequence contract` — NOW.
2. Re-run focused consequence/horizon/censoring regressions.
3. CI exact head.
4. If executable runtime behaviour changes, physical ACTIVE_MATCH acceptance.
5. Then inspect `R2 explicit dependency/reflection burden`.
6. Continue R3-R6 one at a time only when the current owner proves a real gap.

No merge, auto-merge, release or production binding is authorized by this ledger.
