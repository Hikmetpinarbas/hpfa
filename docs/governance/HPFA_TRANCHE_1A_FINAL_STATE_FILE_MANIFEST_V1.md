# HPFA Tranche 1A — Final-State File Manifest V1

Status: `DISCOVERY_PASS_PLAN_ONLY / FILE_EXTRACTION_MANIFEST_READY / NO_PRODUCT_BRANCH_YET / NOT_PRODUCTION`

Date: 2026-08-13

## Purpose

Define the exact **capability/file families** to extract for Landing 1A:

```text
Multiformat Inventory
→ CSV Reader
→ XLSX Reader
→ XML Reader
→ Provider Field Semantics
→ Provider Label/Value Semantics
→ Hardened Cross-Format Reconciliation
```

This is not a cherry-pick list and not a historical PR merge list.

For files that still exist at the active development checkpoint, the extraction source should be the **current final-state file content at the audited development checkpoint**, not blindly the historical PR blob.

Development extraction reference:

`fdb8e109daebd7a9875d6f257011cb93e0372677`

Main landing base remains the current main lineage after Tranche 0 decision.

## Global inclusion policy

For each capability include, where present and still contract-relevant:

```text
root CLI wrapper
module src
machine contract/schema
reviewed registry/config
focused regression tests
exact-head workflow
Termux bootstrap
ACTIVE_MATCH runner
analyst/contract documentation required to explain claim boundary
```

Do not include unrelated descendants simply because they exist in the same stacked branch.

## A01 — Multiformat File Inventory

Historical source PR: `#164`

Candidate file family:

```text
.github/workflows/multiformat-file-inventory-lite-v1.yml
docs/contracts/multiformat_file_inventory_lite_v1.md
hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory.py
hpfa/modules/core/multiformat_file_inventory_lite/src/multiformat_file_inventory_impl.py
hpfa/modules/core/multiformat_file_inventory_lite/tests/test_multiformat_file_inventory.py
hpfa/modules/core/multiformat_file_inventory_lite/tests/test_review_regressions.py
multiformat_file_inventory.py
tools/bootstrap_termux_multiformat_inventory_v1.sh
tools/run_active_match_multiformat_inventory_v1.sh
```

Required final-state behaviours:

- count-semantics correction;
- encoded XML DTD/entity rejection;
- exact duplicate reflection lineage;
- runtime authority guard;
- flat phone output;
- sample identity leak guard.

Extraction source rule:

`CURRENT_CORRECTED_#164_CAPABILITY`, not historical stack ancestor `8090805c...`.

## A02 — CSV Surface Reader

Historical source PR: `#166`

Candidate file family:

```text
.github/workflows/csv-surface-reader-lite-v1.yml
csv_surface_reader_lite.py
hpfa/modules/core/csv_surface_reader_lite/contract/csv_surface_reader_lite_v1.json
hpfa/modules/core/csv_surface_reader_lite/src/csv_surface_reader.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader_regressions.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader_team_binding.py
tools/bootstrap_termux_csv_surface_reader_v1.sh
tools/run_active_match_csv_surface_reader_v1.sh
```

No other downstream action/identity module should enter through this capability.

## A03 — XLSX Surface Reader

Historical source PR: `#170`

Candidate file family:

```text
.github/workflows/xlsx-surface-reader-lite-v1.yml
hpfa/modules/core/xlsx_surface_reader_lite/contract/xlsx_surface_reader_lite_v1.json
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_header_semantics.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_runtime_guard.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_header_semantics.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_runtime_guard.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_surface_reader.py
tools/bootstrap_termux_xlsx_surface_reader_v1.sh
tools/run_active_match_xlsx_surface_reader_v1.sh
xlsx_surface_reader_lite.py
```

Required retained behaviour:

`Passes accurate` and `Passes accurate, %` remain distinct semantic surfaces.

XLSX remains aggregate/table evidence, never event order.

## A04 — XML Surface Reader

Historical source PR: `#171`

Candidate file family:

```text
.github/workflows/xml-surface-reader-lite-v1.yml
hpfa/modules/core/xml_surface_reader_lite/contract/xml_surface_reader_lite_v1.json
hpfa/modules/core/xml_surface_reader_lite/src/xml_common.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_rows.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_structure.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_surface_reader.py
hpfa/modules/core/xml_surface_reader_lite/tests/test_xml_surface_reader.py
tools/bootstrap_termux_xml_surface_reader_v1.sh
tools/run_active_match_xml_surface_reader_v1.sh
xml_surface_reader_lite.py
```

Critical rejection:

```text
XML temporal/action surface != tracking
XML instance != canonical event
XML != automatic higher-resolution truth authority
```

## A05 — Provider Alias / Field Semantics

Historical source PR: `#172`

Candidate file family:

```text
.github/workflows/provider-alias-field-semantics-v1.yml
hpfa/modules/core/provider_alias_field_semantics_lite/contract/provider_alias_field_semantics_lite_v1.json
hpfa/modules/core/provider_alias_field_semantics_lite/src/provider_alias_field_semantics.py
hpfa/modules/core/provider_alias_field_semantics_lite/tests/test_provider_alias_field_semantics.py
provider_alias_field_semantics_lite.py
tools/bootstrap_termux_provider_alias_field_semantics_v1.sh
tools/run_active_match_provider_alias_field_semantics_v1.sh
```

Mandatory boundary:

`field_mapping_coverage != provider_label_value_semantics_coverage`.

## A06 — Provider Label / Value Semantics — final-state composite

Historical base source PR: `#175`

Base file family:

```text
.github/workflows/provider-label-value-semantics-v1.yml
docs/contracts/provider_label_value_semantics_lite_v1.md
hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_reviewed_v2.csv
hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json
hpfa/modules/core/provider_label_value_semantics_lite/src/provider_label_value_semantics.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics_registry_safety.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_termux_exact_head_gate.py
provider_label_value_semantics_lite.py
tools/bootstrap_termux_provider_label_value_semantics_v1.sh
tools/run_active_match_provider_label_value_semantics_v1.sh
```

### Mandatory fold-in from PR #243

PR #243 changes these relevant files:

```text
hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_reviewed_v2.csv
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics.py
```

These **must use final corrected content**, not #175 historical content.

Correct final behaviour:

```text
GOALKEEPER + goal-kick labels
→ reviewed RESTART / GOAL_KICK candidate where scoped

TEAM + Goal kicks short/medium/long
→ ATTRIBUTE_REFERENCE
→ PASS/distance attribute candidate context
→ REFERENCE_ONLY
→ no literal TEAM restart action
```

### Explicitly excluded from Landing 1A from PR #243

```text
hpfa/modules/core/evidence_atom_inventory_lite/src/evidence_atom_inventory.py
```

Reason: Evidence Atom belongs to Tranche 2.

Also not automatically permanent Landing 1A dependencies:

```text
.github/workflows/sportsbase-surface-role-semantic-collision-guard-v1.yml
tools/run_active_match_sportsbase_surface_role_semantic_collision_guard_v1.sh
tools/tests/test_sportsbase_surface_role_semantic_collision_guard_v1.py
docs/research/eventonly/sportsbase_surface_role_semantic_collision_guard_v1.md
```

These are classified as integration/audit support unless a focused landing test audit proves one is required permanently.

The behaviour they test must still be covered by the final integration validation.

## A07 — Cross-Format Reconciliation — hardened final state

Historical PR #173 is not landing authority.

Preferred hardening source PR: `#177`

Candidate file family:

```text
.github/workflows/cross-format-reconciliation-v1.yml
cross_format_reconciliation_lite.py
docs/contracts/cross_format_reconciliation_lite_v1.md
hpfa/modules/core/cross_format_reconciliation_lite/contract/cross_format_reconciliation_lite_v1.json
hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json
hpfa/modules/core/cross_format_reconciliation_lite/src/cross_format_reconciliation.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_cross_format_reconciliation.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_termux_reconciliation_exact_head_gate.py
tools/bootstrap_termux_cross_format_reconciliation_v1.sh
tools/run_active_match_cross_format_reconciliation_v1.sh
```

Mandatory final hardening:

- current runtime bytes rehashed and matched to reader/inventory SHA;
- versioned candidate-only XML group semantics;
- field semantics and label semantics separate prerequisites;
- cross-ID collision detection not neutralized by identity in digest;
- present/present vs both-missing support separated;
- upstream duplicate reflections separated from local duplicates;
- review state cannot masquerade as ACTIVE_MATCH PASS;
- XLSX is not independent occurrence confirmation.

## Files/capabilities explicitly outside Landing 1A

Do not pull these into 1A merely because they exist at the development checkpoint:

```text
row_nucleus_inventory_lite
metric_definition_policy_lite
aggregate_definition_alignment_lite
provider_metric_dictionary_lite
xlsx_entity_metric_row_projection_lite
aggregate_derivation_evidence_reconciliation_lite
evidence_atom_inventory_lite
match_local_identity_candidates_lite
semantic_role_action_bundle_candidates_lite
sequence / phase / context / coordinate / progression modules
```

Their later tranche positions are separately governed.

## Landing 1A validation surface

Landing 1A integration branch should have one coherent validation matrix covering at minimum:

```text
inventory exact duplicate semantics
CSV parser + team-candidate safety
XLSX header/count-percent semantics
XML structural parser + no tracking promotion
field/path semantics separation
provider label exact-rule + role scope
TEAM goal-kick-length collision regression
cross-format runtime SHA lineage
cross-ID collision regression
XML group semantics registry
present/missing support separation
review-vs-PASS runtime evidence rule
flat phone output
runtime authority equality
no sample identity leak
canonical_event_count=UNKNOWN
production_release=false
```

## ACTIVE_MATCH acceptance for Landing 1A

The consolidated head must freshly execute on:

`runtime/active_single_match/current`

Engineering evidence must establish:

- exact integration head used;
- all seven capability stages executed as applicable;
- no hard block;
- expected flat outputs written;
- no source SHA drift;
- no double count of exact duplicate reflections;
- semantic collision regression holds on current match surface.

Analyst evidence must state only what the visible surfaces establish, including format availability, row-level/label-level evidence, semantic candidate coverage, reconciliation support and unresolved claim ceilings.

No event count, identity truth, tracking truth or tactical truth is admitted.

## Next action after Tranche 0 decision

Create one main-based integration branch for Landing 1A and populate it from this manifest using **final-state file content**.

Do not merge historical PRs into it.

```text
LANDING_1A_FILE_MANIFEST=READY
PRODUCT_BRANCH=NOT_CREATED_YET
ACTIVE_MATCH_CONSOLIDATED_HEAD=NOT_RUN
MERGE=NOT_AUTHORIZED
canonical_event_count=UNKNOWN
production_release=false
```
