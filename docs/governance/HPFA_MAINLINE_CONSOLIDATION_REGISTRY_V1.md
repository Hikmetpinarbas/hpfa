# HPFA Mainline Consolidation Registry V1

Status: `DISCOVERY_PASS_PLAN_ONLY / TRANCHE_BOUNDARIES_REFINED`

This registry classifies development work by **integration role**, not by historical PR state. A PR being open, green, closed, or merged into a dependency branch does not by itself make it `main` truth or merge-ready.

## Classification vocabulary

- `MAIN_BOUND_CAPABILITY_SOURCE` — contains product capability expected to contribute to a final mainline tranche after final-state diff/hardening audit.
- `LIVE_STACK_CORRECTION_SOURCE` — current development correction that must be folded into the capability layer it repairs; not necessarily a standalone landing unit.
- `TRANCHE_0_MAIN_BOUND_GOVERNANCE_SOURCE` — main-based governance/operator policy expected to be consolidated before product landing.
- `CROSS_TRANCHE_QUALITY_CLOSURE` — quality/recheck capability whose prerequisites cross tranche boundaries; must not create a dependency cycle.
- `SUPERSEDED_REFERENCE` — useful historical/ontology/provenance source, but not the preferred executable landing path.
- `DIAGNOSTIC_ONLY` — audit/discovery/profiler apparatus that may support validation without becoming a required production dependency.
- `SPEC_REFERENCE` — specification/research source; no automatic executable landing.
- `UNCLASSIFIED_PENDING_AUDIT` — default for any PR not listed here.

No item in this registry is merge-authorized.

## Tranche 0 — Governance / operator authority

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #180 | HPFA Coding Operator Directive (`AGENTS.md`) | TRANCHE_0_MAIN_BOUND_GOVERNANCE_SOURCE | Main-based, one-file policy source. Search-before-code, exact-head discipline, donor authority, claim safety, Git safety and explicit merge/release authorization should be consolidated with Tranche 0 rather than treated as product feature work. |
| #245 | Governance authority + development checkpoint | TRANCHE_0_MAIN_BOUND_GOVERNANCE_SOURCE | Current main-based consolidation PR. Draft/open; no runtime change and no merge authorization. |

## Tranche 1 — Data Foundation Core

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #164 | Multiformat File Inventory | MAIN_BOUND_CAPABILITY_SOURCE | Foundation entry. Current PR head has later hardening and differs from the historical stack ancestry commit. Use final-state capability diff, not the old ancestry snapshot. |
| #166 | CSV Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Runtime-proven reader capability. Rebuild on integration head after #164 final-state extraction. |
| #170 | XLSX Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Preserves count vs percentage surfaces and aggregate-only boundary. |
| #171 | XML Surface Reader | MAIN_BOUND_CAPABILITY_SOURCE | Temporal/action surface reader; XML rows remain non-canonical and not tracking authority. |
| #172 | Provider Alias / Field Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Field/path classification only; must remain separate from label-value semantics. |
| #175 | Provider Label Value Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Historical label-value implementation source, but not final authority because later hardening/corrections exist. |
| #173 | Cross-Format Reconciliation | SUPERSEDED_REFERENCE | Important historical implementation/audit source, but its own audit exposed unresolved signature/SHA/XML-registry/status defects. Prefer #177 final hardening. |
| #177 | Provider Semantic Provenance / Reconciliation Hardening | MAIN_BOUND_CAPABILITY_SOURCE | Preferred final reconciliation/provenance source. Runtime-byte SHA binding, candidate-signature correction, versioned XML group semantics and proper PASS/review separation. |
| #178 | Metric Definition Policy | MAIN_BOUND_CAPABILITY_SOURCE | Include only primitives consumed by final foundation/aggregate contracts; does not create metric truth. |
| #181 | Aggregate Definition Alignment | MAIN_BOUND_CAPABILITY_SOURCE | Keeps provider-definition uncertainty explicit; REVIEW_REQUIRED is a valid analyst state. |
| #183 | Provider Metric Dictionary | MAIN_BOUND_CAPABILITY_SOURCE | Include only where current aggregate/quality contracts actually consume it. Unresolved provider definitions remain unresolved. |
| #185 | Row Nucleus + G01–G18 structural rollup | MAIN_BOUND_CAPABILITY_SOURCE | Foundation exit into Evidence Spine. Final snapshot must fold later semantic-clearance and G07 correction; G16 may remain explicit deferred recheck. |
| #228 | G07 Coordinate Eligibility Correction | LIVE_STACK_CORRECTION_SOURCE | Belongs inside the final Row Nucleus/G01–G18 snapshot; must not land as a detached late feature. |
| #243 | SportsBase Surface-Role Semantic Collision Guard — provider-label portion | LIVE_STACK_CORRECTION_SOURCE | TEAM goal-kick-length labels must remain controlled reference/distance candidates, never literal TEAM restart action bundles. Provider-label registry/test correction folds into Tranche 1. |

### Tranche 1 boundary correction

G16 full derivation recheck is **not** a strict prerequisite for entering Tranche 2 because its current implementation requires Evidence Atom + Match-Local Identity, which live in Tranche 2.

Foundation may therefore exit with:

```text
G16=REVIEW_REQUIRED / RECHECK_DEFERRED
```

provided the structural rollup is internally valid and the deferred dependency is explicit.

## Tranche 2 — Evidence Spine

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #188 | Evidence Atom Inventory | MAIN_BOUND_CAPABILITY_SOURCE | Preferred current evidence-atom lineage over older pre-row-nucleus ontology path. |
| #190 | Match-Local Identity Candidates | MAIN_BOUND_CAPABILITY_SOURCE | Preferred current match-local identity lineage. |
| #192 | Semantic Role / Action Bundle Candidates | MAIN_BOUND_CAPABILITY_SOURCE | Core football-action routing source. Must consume final evidence routing after #243 correction. |
| #194 | Multi-Family Review Taxonomy | MAIN_BOUND_CAPABILITY_SOURCE | Classification support for multi-family action-core ambiguity. |
| #196 | Cross-Role Relation Candidate Resolver | MAIN_BOUND_CAPABILITY_SOURCE | Relation/double-count candidate layer; final suppression semantics remain candidate-safe. |
| #198 | Cross-Role Relation Review Profiler | DIAGNOSTIC_ONLY | Useful for explaining unresolved relations; not automatically a required product dependency. |
| #243 | SportsBase Surface-Role Semantic Collision Guard — evidence-routing portion | LIVE_STACK_CORRECTION_SOURCE | `ATTRIBUTE_REFERENCE → REFERENCE_ATOM → REFERENCE_ROUTE`; TEAM distance-reference surfaces must never create action bundles. Fold into Evidence Spine implementation/tests. |

## Tranche 2 exit — Cross-Tranche Quality Closure

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #232 | XLSX Entity-Metric Row Projection | CROSS_TRANCHE_QUALITY_CLOSURE | Row-aligned aggregate evidence support. Recommended after core Evidence Spine is available rather than bloating Foundation Core. |
| #234 | G16 Aggregate Derivation Evidence Reconciliation | CROSS_TRANCHE_QUALITY_CLOSURE | Requires Evidence Atom + Match-Local Identity + XLSX row projection + provider semantics + aggregate alignment. Must run as post-Evidence-Spine quality recheck, not create a pre-Evidence dependency cycle. |

`G16_RECHECK_ADMITTED != G16_PASS` remains mandatory.

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
| #219 | Outcome Support Bridge | MAIN_BOUND_CAPABILITY_SOURCE | Outcome-support dependency source; exact ACTIVE_MATCH status must be re-established on consolidated integration head. |

## Tranche 4 — Coordinate / Progression Preconditions

| PR | Capability | Integration role | Current integration reading |
|---|---|---|---|
| #223 | Coordinate Frame Precondition | MAIN_BOUND_CAPABILITY_SOURCE | Base coordinate-direction admission gate. |
| #237 | Coordinate Anchor Family Discovery | DIAGNOSTIC_ONLY | Discovery/audit source. Findings may justify product rules, but discovery itself need not be production dependency. |
| #239 | Provider Coordinate Attachment Semantics | MAIN_BOUND_CAPABILITY_SOURCE | Candidate attachment semantics for goalkeeper interception location evidence. |
| #241 | Coordinate Frame Anchor Recheck | MAIN_BOUND_CAPABILITY_SOURCE | Recheck capability; consolidated prerequisite head must be revalidated before progression work. |
| #243 | Surface-Role Semantic Collision Correction | LIVE_STACK_CORRECTION_SOURCE | Must already be folded into upstream Tranche 1/2 capabilities before coordinate/progression revalidation. |

`progression_metric_recheck_allowed=true` is only downstream recheck permission. It is not progression truth.

## Superseded / decomposition-required historical lineage

| PR | Historical capability | Integration role | Decision |
|---|---|---|---|
| #155 | Canonical Event Lite lossless intake | SUPERSEDED_REFERENCE | Audit useful ideas against current surface→row nucleus→evidence atom architecture; do not automatically land. |
| #157 | Event Instance Admission Guard | SUPERSEDED_REFERENCE | Important ontology correction, but current evidence spine supersedes direct historical executable path. |
| #158 | Evidence Atom Contract | SUPERSEDED_REFERENCE | Provenance/ontology donor; current Evidence Atom Inventory is preferred executable lineage. |
| #159 | Match-Local Identity Decoder | SUPERSEDED_REFERENCE | Identity design donor; current Match-Local Identity Candidates is preferred executable lineage. |
| #161 | Composite Event Diagnostic Stack | SUPERSEDED_REFERENCE | `INTEGRATION_BRANCH_ONLY`; explicitly must not merge as one composite change. Mine only narrowly useful pieces. |

## Specification/reference backlog

Older docs/spec-only branches and PRs are not automatically executable landing units. Current examples:

```text
#39 #49 #79 #86 #90 #92 #94 #104 #105 #106 #107
```

They remain `SPEC_REFERENCE` unless a current tranche dependency audit explicitly promotes a narrow capability.

## External donor assumptions

Current compatible donor rules from Dropbox SportsBase surface documentation:

```text
CSV = action/coordinate surface
XML = temporal/action conformance surface
XLSX = aggregate validation surface
raw row/instance/table row != canonical event
CSV coordinate != tracking
```

Historical Drive architecture material that assumes XML/tracking authority, automatic higher-resolution temporal truth, XLSX ground-truth validation, or pre-validated CSV↔XML foreign-key identity is classified:

`SUPERSEDED_DONOR_ASSUMPTION`

Such assumptions must not be reintroduced during consolidation.

## Critical stack-ancestry finding

The active development checkpoint descends from historical inventory commit:

`8090805c5aaa4f92fb6bc6334c4f0ff1555967f1`

The current #164 head is:

`f5a33c03d78d7c7a8c9dcfd733531d4b6125f782`

Therefore the current corrected #164 head is **not** the same snapshot that the long stacked development line originally inherited. This proves why consolidation cannot be a simple chronological PR merge train.

## Final-state extraction rule

For each landing tranche:

1. identify the capability's current product contract;
2. collect all later bug/hardening corrections that semantically modify it;
3. split cross-layer repairs by the capability they actually repair;
4. extract the smallest final-state snapshot onto a main-based integration branch;
5. run deterministic CI;
6. for runtime-relevant tranches, run fresh exact integration-head ACTIVE_MATCH;
7. separate engineering evidence from analyst evidence;
8. preserve claim boundaries;
9. require explicit user merge approval.

Detailed Tranche 1 audit:

`docs/governance/HPFA_TRANCHE_1_DATA_FOUNDATION_FINAL_STATE_AUDIT_V1.md`

## Default for unlisted PRs

Any PR not explicitly classified in this registry is:

`UNCLASSIFIED_PENDING_AUDIT`

It must not be merged merely because it is open, green, old, recent, or part of a historical stack.

`canonical_event_count=UNKNOWN`
`production_release=false`
