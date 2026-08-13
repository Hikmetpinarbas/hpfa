# HPFA Tranche 1 — Data Foundation Final-State Audit V1

Status: `DISCOVERY_PASS_PLAN_ONLY / FINAL_STATE_EXTRACTION_MAP_READY / NO_LANDING_BRANCH_YET / NOT_PRODUCTION`

Date: 2026-08-13

## Purpose

Define the smallest safe **final-state** Data Foundation snapshot for controlled mainline consolidation.

This is not a chronological PR merge list. Historical PR heads are evidence/provenance sources. Landing authority is the final capability state after later bug/hardening corrections are folded back into the layer they repair.

No merge/release/production authorization is granted by this document.

## Authority model

```text
PRODUCT_MAIN
  branch=main
  current audited head=85507f0b2c358c6312b7e3abe1b5992e07dcb3c4

DEVELOPMENT_CHECKPOINT
  head=fdb8e109daebd7a9875d6f257011cb93e0372677
  role=final-state extraction reference only

ACTIVE_MATCH_RUNTIME
  runtime/active_single_match/current
  role=single-match runtime authority only
```

Drive/Dropbox/archive material is `REFERENCE_ONLY` or `DONOR_SUPPORT`; it cannot override product/runtime authority.

## External donor/reference cross-check

### Dropbox — compatible current donor guidance

Reviewed:

```text
/HPFA_RESEARCH_ARCHIVE/09_EVENTONLY_FOOTBALL_INTELLIGENCE_OS_WORKAROUND/
11_EVENT_BASED_PRO_ANALYSIS_LIBRARY/06_EVENT_DATA_METHODS/
SPORTSBASE_SURFACE_DICTIONARY_v1.txt

/HPFA_RESEARCH_ARCHIVE/09_EVENTONLY_FOOTBALL_INTELLIGENCE_OS_WORKAROUND/
11_EVENT_BASED_PRO_ANALYSIS_LIBRARY/06_EVENT_DATA_METHODS/
SPORTSBASE_CSV_XML_XLSX_READING_PROTOCOL_v1.txt
```

Useful donor rules, adapted not copied:

```text
CSV  = action/coordinate visible surface
XML  = temporal/action conformance visible surface
XLSX = aggregate validation visible surface

CSV row != event truth
XML instance != event truth
XLSX row != event truth
raw surface row count != true/canonical event count
CSV coordinate != tracking
TEAM_A/TEAM_B != validated team identity
```

These donor rules are compatible with current HPFA claim boundaries and support the Data Foundation split.

### Google Drive — historical architecture assumptions requiring rejection

Reviewed historical donor:

```text
Tek Mimari.docx
```

Useful high-level ideas:

- single authoritative product tree;
- centralized orchestration;
- provenance/version awareness;
- multi-format roles should be explicit;
- output should separate computation from interpretation.

But several historical assumptions are **not admissible** in current HPFA without new evidence:

```text
XML as high-frequency/tracking authority
XML higher temporal resolution => canonical timestamp truth
CSV event_id <-> XML timestamp_id foreign key assumed before validated identity
XLSX aggregate treated as ground truth validation
body orientation / tracking-derived micro truth from event-only data
```

Classification:

`SUPERSEDED_DONOR_ASSUMPTION / DO_NOT_IMPORT_AS_PRODUCT_TRUTH`

Current product contracts and ACTIVE_MATCH evidence take precedence.

## Critical architecture finding — G16 creates a cross-tranche dependency

The earlier landing sketch placed:

```text
Row Nucleus
→ G01–G18 complete
→ Evidence Atom
→ Match-Local Identity
```

This cannot be interpreted as “all G01–G18 gates must be fully closed before Evidence Spine”.

Current G16 derivation reconciliation requires:

```text
xlsx_entity_metric_row_projection_lite_v1
+ evidence_atom_inventory_lite_v1
+ match_local_identity_candidates_lite_v1
+ provider_label_value_semantics_lite_v1
+ aggregate_definition_alignment_lite_v1
→ aggregate_derivation_evidence_reconciliation_lite_v1
→ G16 recheck admission
```

Therefore G16 is a **cross-tranche recheck closure**, not a strict prerequisite for entering Evidence Spine.

Correct landing model:

```text
TRANCHE 1 FOUNDATION CORE
  inventory
  → CSV/XLSX/XML readers
  → field semantics
  → label/value semantics
  → cross-format reconciliation
  → metric-definition/aggregate policy primitives
  → row nucleus
  → G01–G18 structural rollup
     G16 may remain REVIEW_REQUIRED / RECHECK_DEFERRED

TRANCHE 2 EVIDENCE SPINE
  evidence atom
  → match-local identity
  → semantic route/action bundle
  → relation layers

TRANCHE 2 EXIT / CROSS-TRANCHE QUALITY CLOSURE
  XLSX entity-metric row projection
  + evidence atom
  + match-local identity
  + aggregate alignment
  → G16 derivation reconciliation
  → refreshed G01–G18 quality view
```

This avoids a dependency cycle while preserving fail-closed semantics.

`G16_RECHECK_ADMITTED != G16_PASS` remains mandatory.

## Final-state extraction matrix

### F01 — Multiformat File Inventory

Historical/current source:

```text
PR #164
current head=f5a33c03d78d7c7a8c9dcfd733531d4b6125f782
```

Final-state requirements:

- recursive provider-agnostic discovery;
- SHA-256 content identity;
- supported/unsupported separation;
- exact duplicate reflection lineage;
- XML DTD/entity rejection;
- count terminology correction (`surface/file path`, not event count);
- flat phone-output guard;
- runtime authority path guard;
- no sample identity leak.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE`

Important ancestry rule: use current corrected capability, not historical stack ancestor `8090805c...`.

### F02 — CSV Surface Reader

Source:

```text
PR #166
head=9163f7b28b15683df42179cb2f3853aac6a504d5
```

Final-state requirements:

- lossless CSV/TSV parsing;
- quoted multiline preservation;
- physical source-line diagnostics;
- time/period/coordinate surface checks;
- same timestamp != duplicate;
- provider team/player/GK values remain candidates;
- no clamp-based coordinate invention;
- `surface rows != canonical events`.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE`

### F03 — XLSX Surface Reader

Source:

```text
PR #170
head=cceb3bca15da6d9649ce2d03e0f03d7aab930a91
```

Final-state requirements:

- all sheets inspected;
- visible/hidden state preserved;
- deterministic bounded header detection;
- raw + normalized headers;
- count and percentage metrics remain distinct;
- cached/formula state preserved without formula computation;
- hidden rows/columns, merged cells, duplicate headers visible;
- archive/path traversal and resource guards;
- XLSX remains aggregate surface, not timeline.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE`

### F04 — XML Surface Reader

Source:

```text
PR #171
head=a56ca9668d9e738990749378be5345f2750ce50f
```

Final-state requirements:

- root/namespace/row-container discovery;
- nested field path inventory;
- raw temporal/tag instances preserved;
- no coordinate authority promotion;
- no tracking interpretation;
- no canonical event promotion.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE`

### F05 — Provider Alias / Field Semantics

Source:

```text
PR #172
head=12dd00ef6b7e32cfbba1007ec4e6488aa236198e
```

Final-state rule:

`field/path semantics != provider label/value semantics`

Field coverage may be complete while action-label semantics remain unresolved.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE`

### F06 — Provider Label / Value Semantics

Historical source:

```text
PR #175
```

Hardening source:

```text
PR #177
```

Mandatory later correction source:

```text
PR #243
```

Final-state extraction must include the current development version of:

```text
hpfa/modules/core/provider_label_value_semantics_lite/registry/
  sportsbase_label_semantics_reviewed_v2.csv

provider-label semantic tests/contracts required by that registry
```

Critical corrected behaviour:

```text
GOALKEEPER surface + Goal kicks[/short/medium/long]
  → literal RESTART / GOAL_KICK candidate allowed under reviewed scope

TEAM surface + Goal kicks short/medium/long
  → ATTRIBUTE_REFERENCE
  → PASS candidate family context
  → distance attribute candidate
  → REFERENCE_ONLY
  → never literal TEAM GOAL_KICK restart action
```

Plain `Goal kicks` remains goalkeeper-scoped; unexpected roles remain review/fail-closed.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE + LIVE_STACK_CORRECTION_FOLDED_IN`

### F07 — Cross-Format Reconciliation + Provenance Hardening

Historical source:

```text
PR #173
```

Preferred final hardening source:

```text
PR #177
head=0cdf38dbc8a244c552cc681249f77c60a30e58a8
```

PR #173 by itself is not landing authority because its own audit recorded unresolved defects.

Final-state requirements from #177:

- runtime bytes → reader SHA → inventory SHA exact lineage;
- field semantics and label semantics separate inputs;
- candidate signatures can expose cross-ID collision;
- versioned XML group candidate semantics registry;
- present/present vs both-missing vs one-missing support separated;
- upstream duplicate reflection vs local duplicate candidate separated;
- `ACTIVE_MATCH_EVIDENCE_PASS` requires actual PASS, not merely non-failure;
- XLSX remains non-independent aggregate support.

Landing role:

```text
#173 = SUPERSEDED_REFERENCE
#177 = MAIN_BOUND_CAPABILITY_SOURCE
```

### F08 — Metric Definition Policy / Aggregate Definition Alignment

Sources:

```text
PR #178 — Metric Definition Policy
PR #181 — Aggregate Definition Alignment
PR #183 — Provider Metric Dictionary
```

Landing decision:

Include only policy/dictionary primitives that are actually required by the row-quality and aggregate-alignment contracts in the final integration snapshot.

Do not import unresolved provider definitions as truth.

Mandatory distinctions:

```text
same label != same definition
count parity != derivation equivalence
observed arithmetic != provider operational definition
same provider != independent confirmation
```

Provider-definition gaps may legitimately keep records `REVIEW_REQUIRED`.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE / MINIMIZE_TO_CONSUMED_CONTRACTS`

### F09 — Row Nucleus + G01–G18 structural rollup

Base source:

```text
PR #185
```

Mandatory correction source:

```text
PR #228 — G07 coordinate eligibility
```

Final-state requirements:

- same-role CSV/XML row candidates reconciled with exact provenance;
- row nucleus != canonical event;
- reviewed non-action semantic roles can clear without invented action family;
- XLSX aggregate support does not become row occurrence;
- G07 denominator includes only coordinate-eligible evidence;
- explicitly ADMIN_ONLY semantic surfaces may be coordinate-exempt;
- missing numeric values remain distinct from zero;
- G16 may remain `REVIEW_REQUIRED / RECHECK_DEFERRED` until Evidence Spine exists.

Landing role:

`MAIN_BOUND_CAPABILITY_SOURCE + G07_CORRECTION_FOLDED_IN`

## Cross-tranche items — do not force into Foundation Core

### X01 — XLSX Entity-Metric Row Projection (#232)

Useful for G16 derivation reconciliation but not required to establish CSV/XML/XLSX reading or row-nucleus foundation.

Recommended landing:

`TRANCHE_2_EXIT_QUALITY_CLOSURE_SUPPORT`

Reason: keep Tranche 1 minimal and avoid introducing an aggregate-recheck apparatus before its identity/evidence consumers exist.

### X02 — G16 Aggregate Derivation Evidence Reconciliation (#234)

Depends on Evidence Atom and Match-Local Identity.

Recommended landing:

`TRANCHE_2_EXIT_CROSS_TRANCHE_QUALITY_CLOSURE`

It must not block entry into Tranche 2 merely because its own prerequisites live in Tranche 2.

### X03 — SportsBase Semantic Collision Guard (#243)

PR #243 spans two architectural layers and must be **split by repaired capability**, not landed as a detached late node.

Foundation portion:

```text
provider-label registry semantic correction
provider-label semantic regression tests
```

Evidence Spine portion:

```text
ATTRIBUTE_REFERENCE → REFERENCE_ATOM mapping
REFERENCE_ROUTE behaviour
no action-bundle creation from TEAM distance-reference surfaces
```

Validation-only/support portion:

```text
dedicated collision audit workflow/runner
```

The dedicated audit runner may remain integration validation apparatus rather than becoming a permanent product dependency.

## Tranche 0 adjacent item — PR #180

PR #180 contains only root `AGENTS.md` and is main-based.

It binds:

- search-before-code;
- exact repo/head/base resolution;
- donor authority restrictions;
- engineering vs analyst evidence separation;
- no destructive Git operations without authorization;
- claim boundary and sample identity leak rules;
- merge/release/production explicit authorization.

Recommended role:

`TRANCHE_0_MAIN_BOUND_GOVERNANCE_SOURCE`

It should be consolidated with the Tranche 0 authority/checkpoint work rather than treated as an unrelated product feature.

## Open historical/spec PR handling

Open PR state is not an integration role.

Current old open specs such as:

```text
#39 #49 #79 #86 #90 #92 #94 #104 #105 #106 #107
```

remain:

`SPEC_REFERENCE`

unless a later tranche audit promotes one narrow current capability.

Historical executable ontology path:

```text
#155 #157 #158 #159 #161
```

remains:

`SUPERSEDED_REFERENCE`

Current Row Nucleus → Evidence Atom → Match-Local Identity path is preferred.

## Proposed mainline landing sequence after Tranche 0 review

### Landing 1A — Foundation readers and semantics

```text
F01 inventory
→ F02 CSV
→ F03 XLSX
→ F04 XML
→ F05 field semantics
→ F06 final label/value semantics
→ F07 hardened reconciliation
```

### Landing 1B — Aggregate policy + row nucleus

```text
F08 consumed metric/aggregate policy primitives
→ F09 Row Nucleus + G01–G18 structural rollup
→ G07 final correction included
→ G16 allowed to remain explicit deferred recheck
```

Only after 1A/1B integration-head CI + ACTIVE_MATCH revalidation should Evidence Spine landing begin.

### Landing 2 — Evidence Spine

```text
Evidence Atom
→ Match-Local Identity
→ Semantic Route / Action Bundle
→ Taxonomy / Relation
```

### Landing 2Q — Cross-tranche quality closure

```text
#232 row-aligned XLSX projection
+ Evidence Atom
+ Match-Local Identity
+ aggregate alignment
→ #234 G16 reconciliation
→ refreshed quality rollup overlay/recheck
```

## Acceptance contract for Landing 1A / 1B

Before any merge decision:

```text
exact integration branch/head known
main-based ancestry confirmed
no historical stack merge/rebase shortcut
focused + relevant wider CI success
runtime-relevant modules executed on ACTIVE_MATCH exact integration head
engineering evidence collected
analyst evidence collected
claim boundaries audited
same-SHA reflections not double counted
no sample match identity leak
flat phone output policy preserved
canonical_event_count=UNKNOWN
production_release=false
explicit user merge approval required
```

## Current decision

```text
TRANCHE_1_FINAL_STATE_CAPABILITY_MAP=READY
TRANCHE_1_DEPENDENCY_CYCLE=IDENTIFIED_AND_CORRECTED_IN_PLAN
G16_STRICT_PRE_EVIDENCE_SPINE_BLOCK=REJECTED
MAIN_BASED_TRANCHE_1_INTEGRATION_BRANCH=NOT_CREATED_YET
ACTIVE_MATCH_REVALIDATION=NOT_STARTED_FOR_CONSOLIDATED_HEAD
MERGE=NOT_AUTHORIZED
PRODUCTION_RELEASE=false
canonical_event_count=UNKNOWN
```
