# HPFA Mainline Consolidation Registry V1

Status: `DISCOVERY_PASS_PLAN_ONLY`

This registry classifies development work by **integration role**, not by historical PR state. A PR being open, green, closed, or merged into a dependency branch does not by itself make it `main` truth or merge-ready.

## Classification vocabulary

- `MAIN_BOUND_CAPABILITY_SOURCE` — contains product capability that is expected to contribute to a final mainline tranche, after final-state diff/hardening audit.
- `LIVE_STACK_CORRECTION_SOURCE` — current development correction that must be folded into the capability layer it repairs; not necessarily a standalone landing unit.
- `SUPERSEDED_REFERENCE` — useful historical/ontology/provenance source, but not the preferred executable landing path.
- `DIAGNOSTIC_ONLY` — audit/discovery/profiler apparatus that may support validation without becoming a required production dependency.
- `SPEC_REFERENCE` — specification/research source; no automatic executable landing.
- `UNCLASSIFIED_PENDING_AUDIT` — default for any PR not listed here.

No item in this registry is merge-authorized.

## Tranche 1 — Data Foundation

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #164 | Multiformat File Inventory | MAIN_BOUND_CAPABILITY_SOURCE | Foundation entry. Current PR head has later hardening and differs from the historical stack ancestry commit. Use final-state capability diff, not the old ancestry snapshot. |
| #166 | CSV Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Runtime-proven reader capability. Rebuild on integration head after #164 final-state extraction. |
| #170 | XLSX Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Preserves count vs percentage surfaces and aggregate-only boundary. |
| #171 | XML Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Temporal/action surface reader; XML rows remain non-canonical. |
| #172 | Provider Alias / Field Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Field/path classification only; must be paired with later label-value semantics. |
| #175 | Provider Label Value Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Label-value classification source, but historical snapshot is not final authority because later semantic corrections exist. |
| #177 | Provider Semantic Provenance / Reconciliation Hardening | MAIN_BOUND_CAPABILITY_SOURCE | Important final-state provenance and fail-closed hardening source. |
| #178 | Metric Definition Policy | MAIN_BOUND_CAPABILITY_SOURCE | Policy dependency where row-quality/aggregate gates require metric-definition structure; does not create metric truth. |
| #181 | Aggregate Definition Alignment | MAIN_BOUND_CAPABILITY_SOURCE | Keeps provider-definition uncertainty explicit; REVIEW_REQUIRED is valid analyst state. |
| #183 | Provider Metric Dictionary | MAIN_BOUND_CAPABILITY_SOURCE | Required only where current row-quality/aggregate contracts consume it; final dependency audit required. |
| #185 | Row Nucleus + G01–G18 | MAIN_BOUND_CAPABILITY_SOURCE | Foundation exit into evidence spine. Historical head/runtime states are not sufficient; later G07/G16 corrections must be folded in. |
| #228 | G07 Coordinate Eligibility Correction | LIVE_STACK_CORRECTION_SOURCE | Fix belongs to Row Nucleus / G01–G18 final snapshot; should not land as a detached late feature. |
| #232 | XLSX Entity-Metric Row Projection | MAIN_BOUND_CAPABILITY_SOURCE | Row-aligned aggregate evidence support; include only if G16/foundation final contract requires it. |
| #234 | G16 Aggregate Derivation Reconciliation | MAIN_BOUND_CAPABILITY_SOURCE | Arithmetic/lineage evidence is useful; provider definition remains separate and unresolved. |
| #243 | SportsBase Surface-Role Semantic Collision Guard | LIVE_STACK_CORRECTION_SOURCE | Final-state correction to provider-label semantics + evidence routing. TEAM goal-kick-length records must remain reference evidence, never literal TEAM restart action bundles. Fold into Tranche 1/2 snapshots. |

## Tranche 2 — Evidence Spine

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #188 | Evidence Atom Inventory | MAIN_BOUND_CAPABILITY_SOURCE | Preferred current evidence-atom lineage over older pre-row-nucleus ontology path. |
| #190 | Match-Local Identity Candidates | MAIN_BOUND_CAPABILITY_SOURCE | Preferred current match-local identity lineage. |
| #192 | Semantic Role / Action Bundle Candidates | MAIN_BOUND_CAPABILITY_SOURCE | Core football-action routing source; must include later `ATTRIBUTE_REFERENCE → REFERENCE_ATOM → REFERENCE_ROUTE` correction. |
| #194 | Multi-Family Review Taxonomy | MAIN_BOUND_CAPABILITY_SOURCE | Classification support for multi-family action-core ambiguity. |
| #196 | Cross-Role Relation Candidate Resolver | MAIN_BOUND_CAPABILITY_SOURCE | Relation/double-count candidate layer; final suppression semantics must remain candidate-safe. |
| #198 | Cross-Role Relation Review Profiler | DIAGNOSTIC_ONLY | Useful for explaining unresolved relations; not automatically a required product dependency. |

## Tranche 3 — Behaviour / Sequence / Context Intelligence

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #199 | Selected Action Consequence Surface | MAIN_BOUND_CAPABILITY_SOURCE | First visible action→consequence product layer. |
| #201 | Consequence Field Semantics Closure | MAIN_BOUND_CAPABILITY_SOURCE | Clarifies follow-up/retention/breakdown/displacement fields without promoting tactical truth. |
| #203 | Selected Event Consequence Surface | MAIN_BOUND_CAPABILITY_SOURCE | Adds zone/consequence candidate context; coordinate claims remain bounded. |
| #205 | Visible Action Sequence Candidates | MAIN_BOUND_CAPABILITY_SOURCE | Same-team strictly ordered visible chains; no possession/sequence truth promotion. |
| #206 | Event-Derived Phase State | MAIN_BOUND_CAPABILITY_SOURCE | Event-derived phase candidates; not tactical phase truth. |
| #207 | Phase-Aware Sequence Refinement | MAIN_BOUND_CAPABILITY_SOURCE | Preserves source phases and review-bounded refinements. |
| #208 | Match Context Slicer | MAIN_BOUND_CAPABILITY_SOURCE | Closed/merged to dependency branch only; not main. Match-time/goal/score-context candidate capability source. |
| #209 | Micro-Action Phase Overlay | MAIN_BOUND_CAPABILITY_SOURCE | Closed/merged into dependency branch; representation-layer correction that preserves source phase. |
| #213 | Event-Only Sequence Consequence Engine | MAIN_BOUND_CAPABILITY_SOURCE | Closed/merged to dependency branch only; metric-candidate support where denominator gates are satisfied. |
| #218 | Structural Progression Evidence | MAIN_BOUND_CAPABILITY_SOURCE | Existing component-first progression evidence source; rate/metric truth remains blocked until later gates. |
| #219 | Outcome Support Bridge | MAIN_BOUND_CAPABILITY_SOURCE | Outcome-support dependency source; exact ACTIVE_MATCH status must be re-established on integration head. |

## Tranche 4 — Coordinate / Progression Preconditions

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #223 | Coordinate Frame Precondition | MAIN_BOUND_CAPABILITY_SOURCE | Base coordinate-direction admission gate. |
| #237 | Coordinate Anchor Family Discovery | DIAGNOSTIC_ONLY | Discovery/audit source. Its findings may justify a later product rule, but discovery itself need not be a production dependency. |
| #239 | Provider Coordinate Attachment Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Candidate attachment semantics for goalkeeper interception location evidence. |
| #241 | Coordinate Frame Anchor Recheck | MAIN_BOUND_CAPABILITY_SOURCE | Corrected ACTIVE_MATCH evidence later reached 4/4 team-period support with zero primary conflicts. Historical PR head text alone is not the final runtime authority. |
| #243 | Surface-Role Semantic Collision Correction | LIVE_STACK_CORRECTION_SOURCE | Must already be folded upstream before coordinate/progression revalidation. |

`progression_metric_recheck_allowed=true` is only a downstream recheck permission. It is not progression truth.

## Superseded / decomposition-required historical lineage

| PR | Historical capability | Integration role | Decision |
|---|---|---|---|
| #155 | Canonical Event Lite lossless intake | SUPERSEDED_REFERENCE | Audit useful ideas against current surface→row nucleus→evidence atom architecture; do not automatically land. |
| #157 | Event Instance Admission Guard | SUPERSEDED_REFERENCE | Important ontology correction, but current evidence spine supersedes direct historical executable path. |
| #158 | Evidence Atom Contract | SUPERSEDED_REFERENCE | Provenance/ontology donor; current Evidence Atom Inventory is preferred executable lineage. |
| #159 | Match-Local Identity Decoder | SUPERSEDED_REFERENCE | Identity design donor; current Match-Local Identity Candidates is preferred executable lineage. |
| #161 | Composite Event Diagnostic Stack | SUPERSEDED_REFERENCE | `INTEGRATION_BRANCH_ONLY`; explicitly must not merge as one composite change. Mine only narrowly useful pieces. |

## Specification/reference backlog

Older docs/spec-only branches and PRs are not automatically executable landing units. Examples include #39, #49, #79, #86, #90, #92, #94 and #104–#107. They remain `SPEC_REFERENCE` unless a current tranche dependency audit explicitly promotes a narrow capability.

## Critical stack-ancestry finding

The active development checkpoint descends from historical inventory commit:

`8090805c5aaa4f92fb6bc6334c4f0ff1555967f1`

The current #164 head is:

`f5a33c03d78d7c7a8c9dcfd733531d4b6125f782`

Therefore the current corrected #164 head is **not** the same snapshot that the long stacked development line originally inherited. This proves why the consolidation process cannot be a simple chronological PR merge train.

## Final-state extraction rule

For each landing tranche:

1. identify the capability's current product contract;
2. collect all later bug/hardening corrections that semantically modify it;
3. extract the smallest final-state snapshot onto a main-based integration branch;
4. run deterministic CI;
5. for runtime-relevant tranches, run fresh exact integration-head ACTIVE_MATCH;
6. separate engineering evidence from analyst evidence;
7. preserve claim boundaries;
8. require explicit user merge approval.

## Default for unlisted PRs

Any PR not explicitly classified in this registry is:

`UNCLASSIFIED_PENDING_AUDIT`

It must not be merged merely because it is open, green, old, recent, or part of a historical stack.

`canonical_event_count=UNKNOWN`
`production_release=false`
