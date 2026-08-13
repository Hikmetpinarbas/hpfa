# HPFA Tranche 2 — Evidence Spine Final-State File Manifest V1

Status: `DISCOVERY_PASS_PLAN_ONLY / EVIDENCE_SPINE_FILE_MANIFEST_READY / CROSS_TRANCHE_G16_CLOSURE_MAPPED / NO_PRODUCT_BRANCH_YET / NOT_PRODUCTION`

Date: 2026-08-13

## Purpose

Define the final-state extraction map for the Evidence Spine after Landing 1A/1B:

```text
Row Nucleus
→ Evidence Atom
→ Match-Local Identity Candidates
→ Semantic Routes / Action Bundle Candidates
→ Multi-Family Review Taxonomy
→ Cross-Role Relation Candidates
→ Tranche 2 quality closure (XLSX row projection + G16 reconciliation)
```

This tranche does not create canonical events, validated global identity, event fusion, possession truth, sequence truth or tactical truth.

Historical PRs are provenance/capability sources only. Landing uses final compatible file content after later corrections are folded into the layer they repair.

## Authority

```text
PRODUCT_MAIN = then-current main after prior approved landings
DEVELOPMENT_EXTRACTION_REFERENCE = fdb8e109daebd7a9875d6f257011cb93e0372677
ACTIVE_MATCH_RUNTIME = runtime/active_single_match/current
```

Drive/Dropbox remain `REFERENCE_ONLY / DONOR_SUPPORT`.

## T2A01 — Evidence Atom Inventory

Historical source PR: `#188`

Historical head:

`2bd95022e8fb99d22d88c6a2a642124608938928`

Primary file family:

```text
.github/workflows/evidence-atom-inventory-lite-v1.yml
docs/contracts/evidence_atom_inventory_lite_v1.md
evidence_atom_inventory_lite.py
hpfa/modules/core/evidence_atom_inventory_lite/contract/evidence_atom_inventory_lite_v1.json
hpfa/modules/core/evidence_atom_inventory_lite/src/evidence_atom_inventory.py
hpfa/modules/core/evidence_atom_inventory_lite/tests/test_evidence_atom_inventory.py
hpfa/modules/core/evidence_atom_inventory_lite/tests/test_evidence_atom_role_families.py
tools/bootstrap_termux_evidence_atom_inventory_v1.sh
tools/run_active_match_evidence_atom_inventory_v1.sh
```

Historical #188 also changed parent Row Nucleus runner/test compatibility files. Those are **not automatic duplicate landing units**. Their necessary compatibility behaviour must be reviewed against the already-landed final Row Nucleus runner rather than blindly copied.

### Mandatory final-state correction from PR #243

Final development content adds:

```text
ROW_ROLE_TO_CLASS:
ATTRIBUTE_REFERENCE → REFERENCE_ATOM

ROLE_ELIGIBILITY:
ATTRIBUTE_REFERENCE → REFERENCE_ONLY
```

This correction belongs to Evidence Atom final state.

It ensures a TEAM distance/reference semantic surface cannot be promoted merely because its provider label contains `Goal kicks`.

### Core invariant

```text
1 row nucleus candidate = 1 evidence atom candidate
```

only after Row Nucleus same-role reflection reconciliation.

Evidence Atom remains:

```text
evidence_atom_is_canonical_event=false
validated_event_identity=false
event_instance_allowed=false
```

## T2A02 — Match-Local Identity Candidates

Historical source PR: `#190`

Head:

`f78f8fbdf50a01a85a3f528a3007003e80e0cd08`

Primary file family:

```text
.github/workflows/match-local-identity-candidates-lite-v1.yml
docs/contracts/match_local_identity_candidates_lite_v1.md
hpfa/modules/core/match_local_identity_candidates_lite/contract/match_local_identity_candidates_lite_v1.json
hpfa/modules/core/match_local_identity_candidates_lite/src/match_local_identity_candidates.py
hpfa/modules/core/match_local_identity_candidates_lite/tests/test_match_local_identity_candidates.py
match_local_identity_candidates_lite.py
tools/bootstrap_termux_match_local_identity_candidates_v1.sh
tools/run_active_match_match_local_identity_candidates_v1.sh
```

Historical #190 also modified the Evidence Atom runner for child-spine compatibility. Consolidated landing should carry one final compatible Evidence Atom runner, not duplicate historical runner states.

### Identity ceiling

Match-local candidate binding may use:

- raw alias;
- normalized comparison key;
- provider-ID candidate;
- jersey-number candidate;
- exact source-role context;
- match-surface binding.

But it does not admit:

```text
validated global player identity
validated global team identity
cross-match identity
provider ID as identity truth
canonical event identity
```

Administrative atoms may be `IDENTITY_NOT_APPLICABLE`; missing identity must not be silently converted into zero/unknown actor truth.

## T2A03 — Semantic Route / Action Bundle Candidates

Historical source PR: `#192`

Head:

`fc8c540b598aff58e1827aed989e5ae9a5128bb6`

File family:

```text
.github/workflows/semantic-role-action-bundle-candidates-lite-v1.yml
docs/contracts/semantic_role_action_bundle_candidates_lite_v1.md
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/contract/semantic_role_action_bundle_candidates_lite_v1.json
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/src/semantic_role_action_bundle_candidates.py
hpfa/modules/core/semantic_role_action_bundle_candidates_lite/tests/test_semantic_role_action_bundle_candidates.py
semantic_role_action_bundle_candidates_lite.py
tools/bootstrap_termux_semantic_role_action_bundle_candidates_v1.sh
tools/run_active_match_semantic_role_action_bundle_candidates_v1.sh
```

### Final-state routing requirement after #243

Current final router accepts `REFERENCE_ATOM` and routes it to:

`REFERENCE_ROUTE`

except the explicitly separate goalkeeper opponent-reference route.

Therefore final integrated regression must assert:

```text
TEAM goal-kick-length ATTRIBUTE_REFERENCE
→ REFERENCE_ATOM
→ REFERENCE_ROUTE
→ action_bundle_candidate = forbidden
```

### Bundle rule

Action bundle candidates only arise from action-anchor atoms and exact same-role action core candidates.

Same timestamp alone is insufficient.

Missing coordinate, identity mismatch, family ambiguity or incompatible source role remains review/fail-closed.

Cross-role overlap creates relation candidates only; it does not fuse events.

## T2A04 — Multi-Family Review Taxonomy

Historical source PR: `#194`

Head:

`b65f5a99e36d852962edd23cd73e948c889d5c89`

File family:

```text
.github/workflows/action-bundle-multi-family-review-taxonomy-lite-v1.yml
action_bundle_multi_family_review_taxonomy_lite.py
docs/contracts/action_bundle_multi_family_review_taxonomy_lite_v1.md
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/contract/action_bundle_multi_family_review_taxonomy_lite_v1.json
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/src/action_bundle_multi_family_review_taxonomy.py
hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/tests/test_action_bundle_multi_family_review_taxonomy.py
tools/bootstrap_termux_action_bundle_multi_family_review_taxonomy_v1.sh
tools/run_active_match_action_bundle_multi_family_review_taxonomy_v1.sh
```

Exact family-set registry may classify review cores as candidate relationships such as:

```text
DUEL + TACKLE → hierarchical subtype candidate
PASS + CROSS → hierarchical subtype candidate
TURNOVER + CONTROL_ERROR → hierarchical subtype candidate
PASS + RESTART → restart-action coupling candidate
```

But:

```text
classification != event truth
subtype candidate != validated action
restart coupling != event fusion
```

Unregistered, compound, same-time-risk and complex family sets remain review-required.

## T2A05 — Cross-Role Relation Candidate Resolver

Historical source PR: `#196`

Head:

`37740ff74b39eab3547200405688c299e7d5ec9b`

File family:

```text
.github/workflows/cross-role-relation-candidate-resolver-lite-v1.yml
cross_role_relation_candidate_resolver_lite.py
docs/contracts/cross_role_relation_candidate_resolver_lite_v1.md
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/contract/cross_role_relation_candidate_resolver_lite_v1.json
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/src/cross_role_relation_candidate_resolver.py
hpfa/modules/core/cross_role_relation_candidate_resolver_lite/tests/test_cross_role_relation_candidate_resolver.py
tools/bootstrap_termux_cross_role_relation_candidate_resolver_v1.sh
tools/run_active_match_cross_role_relation_candidate_resolver_v1.sh
```

### Required relation integrity

A relation candidate requires exact integrity across:

```text
match_surface_binding_id
team candidate
period
start/end
x/y
family
role pair
primary actor candidate where required
```

A relation must have exactly two compatible bundles:

- one TEAM reflection surface;
- one PLAYER or GOALKEEPER primary/action surface.

Taxonomy context must match the exact supporting action core, not merely share IDs loosely.

### Double-count boundary

`double_count_suppression_candidate` is not final count truth.

It is a candidate instruction for later consumers to avoid counting a same-provider reflection twice when the relation gate is clear.

No event fusion or physical-action identity is admitted.

## T2D — Diagnostic profiler

PR #198 remains:

`DIAGNOSTIC_ONLY`

It may be used during integration review to explain unresolved relation candidates but is not automatically a permanent runtime dependency.

## T2Q01 — XLSX Entity-Metric Row Projection

Source PR: `#232`

Role:

`CROSS_TRANCHE_QUALITY_CLOSURE_SUPPORT`

This module is introduced **after core Evidence Spine exists**, because it prepares row-aligned aggregate evidence for G16 reconciliation.

Expected file family from #232:

```text
.github/workflows/xlsx-entity-metric-row-projection-lite-v1.yml
xlsx_entity_metric_row_projection_lite.py
docs/contracts/xlsx_entity_metric_row_projection_lite_v1.md
hpfa/modules/core/xlsx_entity_metric_row_projection_lite/contract/xlsx_entity_metric_row_projection_lite_v1.json
hpfa/modules/core/xlsx_entity_metric_row_projection_lite/src/xlsx_entity_metric_row_projection.py
hpfa/modules/core/xlsx_entity_metric_row_projection_lite/tests/test_active_match_runner_contract.py
hpfa/modules/core/xlsx_entity_metric_row_projection_lite/tests/test_xlsx_entity_metric_row_projection.py
tools/run_active_match_xlsx_entity_metric_row_projection_v1.sh
```

It must not turn XLSX aggregate rows into occurrence events.

## T2Q02 — G16 Aggregate Derivation Evidence Reconciliation

Source PR: `#234`

Role:

`CROSS_TRANCHE_QUALITY_CLOSURE`

Expected file family:

```text
.github/workflows/aggregate-derivation-evidence-reconciliation-lite-v1.yml
aggregate_derivation_evidence_reconciliation_lite.py
docs/contracts/aggregate_derivation_evidence_reconciliation_lite_v1.md
hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/contract/aggregate_derivation_evidence_reconciliation_lite_v1.json
hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/src/aggregate_derivation_evidence_reconciliation.py
hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/src/runtime_source_guard.py
hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/tests/test_aggregate_derivation_evidence_reconciliation.py
hpfa/modules/core/aggregate_derivation_evidence_reconciliation_lite/tests/test_runtime_source_guard.py
tools/run_active_match_aggregate_derivation_evidence_reconciliation_v1.sh
```

Prerequisites:

```text
xlsx_entity_metric_row_projection_lite_v1
+ evidence_atom_inventory_lite_v1
+ match_local_identity_candidates_lite_v1
+ provider_label_value_semantics_lite_v1
+ aggregate_definition_alignment_lite_v1
```

### G16 epistemic separation

```text
observed arithmetic evidence
!= derivation lineage evidence
!= reviewed provider-definition evidence
```

Candidate entity binding remains exact/match-local only. No fuzzy/substring/first-match/provider-ID-only identity promotion.

Same-provider arithmetic reproduction is not independent provider-definition confirmation.

`G16_RECHECK_ADMITTED != G16_PASS`.

## External donor audit

### Dropbox source-role donor

`SOURCE_ROLE_CLASSIFICATION_B02.csv` contains useful separation ideas:

- source roles should be explicit;
- XML/XLSX support should not automatically generate event truth;
- derived runtime/report artifacts must not be re-ingested as raw authority.

But the historical donor also labels one CSV role as a `PRIMARY_CANONICAL_ACTION_SURFACE` with event-generation permission.

That assumption is **superseded for current HPFA**.

Current rule:

```text
CSV visible row / Row Nucleus / Evidence Atom
!= canonical event
```

Classification:

`PARTIALLY_COMPATIBLE_DONOR / CANONICAL_PROMOTION_ASSUMPTION_REJECTED`

### Google Drive fail-closed/fusion research

Historical Drive fusion research supports general engineering principles:

- deterministic quality gates;
- fail-closed rather than silently emitting misleading output;
- provenance and auditability;
- different source modalities have different information ceilings.

But its tracking/GPS/physiology/pitch-control/formation models and numerical thresholds are outside current event-only Evidence Spine authority.

They remain:

`REFERENCE_ONLY / DONOR_SUPPORT`

and cannot promote event-only evidence into physical/tactical truth.

## Tranche 2 consolidated validation matrix

At minimum:

```text
Row Nucleus count ↔ Evidence Atom count integrity
source binding SHA lineage
unique evidence_atom_id
ATTRIBUTE_REFERENCE → REFERENCE_ATOM regression
reference atom cannot create action bundle
match-local identity only
provider ID cannot become validated identity
administrative IDENTITY_NOT_APPLICABLE preserved
semantic route count ↔ atom count integrity
same-role action-core exactness
same timestamp different actor non-fusion
multi-family exact taxonomy registry
unregistered/complex core remains review
cross-role exact relation integrity
primary vs reflection role separation
bundle reuse prevention
relation mismatch fail-closed
double-count suppression remains candidate-only
no cross-role fusion
#232 XLSX projection remains aggregate evidence
#234 source guard rehashes runtime sources
G16 arithmetic/lineage/provider-definition separation
sample match identity leak guard
flat phone output
canonical_event_count=UNKNOWN
production_release=false
```

## ACTIVE_MATCH acceptance

Run only after consolidated Landing 1A/1B prerequisites are on the exact Tranche 2 integration head.

Engineering evidence must report each stage separately:

```text
Evidence Atom
Match-Local Identity
Semantic Routes / Action Bundles
Multi-Family Taxonomy
Cross-Role Relation Resolver
T2Q XLSX projection
T2Q G16 reconciliation
```

Analyst evidence must answer:

- what evidence families are visible;
- which match-local team/actor candidates bind them;
- which surfaces are primary actions vs reflections/references;
- where multi-family ambiguity remains;
- where relation candidates support double-count suppression;
- whether G16 arithmetic is reproducible and which definition/lineage uncertainty remains.

No physical event count, canonical identity, possession truth, tactical truth or provider definition truth may be inferred.

## Exit condition

Tranche 2 may exit to Behaviour Intelligence when:

- core Evidence Spine is exact-head CI + ACTIVE_MATCH revalidated;
- #243 reference routing regression remains closed;
- relation integrity is fail-closed and no accidental fusion is introduced;
- G16 quality recheck has executed on consolidated evidence prerequisites;
- any unresolved provider-definition evidence is explicitly review-bounded rather than invented.

```text
TRANCHE_2_FILE_MANIFEST=READY
TRANCHE_2_PRODUCT_BRANCH=NOT_CREATED
G16_CROSS_TRANCHE_CLOSURE=MAPPED
MERGE=NOT_AUTHORIZED
canonical_event_count=UNKNOWN
production_release=false
```
