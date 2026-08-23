# HPFA C0B — Foundation Final-State File Lineage — 2026-08-23

Status: `C0B_FOUNDATION_LINEAGE_CLOSED / FINAL_CAPABILITY_SNAPSHOT_EXTRACTION_READY / NOT_PRODUCTION / NOT_MERGED`

## Purpose

Fix the current final-state extraction lineage for the C1 Foundation landing without replaying historical pull requests.

This record is a file/capability extraction map. It is not merge authority, runtime truth, ACTIVE_MATCH evidence, or production release.

## Authority

```text
PRODUCT_MAIN
  main
  snapshot_head=105539970ffd0ca8b5d592a68e800da6057e3274

CURRENT_CONSOLIDATION_CONTROL
  PR #268
  branch=integration/current-spine-consolidation-preflight-v1

SOLE_ACTIVE_MATCH_RUNTIME_AUTHORITY
  runtime/active_single_match/current
```

Landing unit:

```text
FINAL_CAPABILITY_SNAPSHOT
```

Historical PR chronology is not a landing plan.

## Current Foundation extraction snapshot

The preferred coherent current Foundation extraction snapshot is:

```text
PR #254
head=a8ae2334473fb792e01c53fb0e6867e8087715c4
branch=work/reconstruct-row-nucleus-research-hardened-v1
```

Reason:
- the snapshot carries the current inherited Foundation file families;
- current content-source-role resolution is physically present in this tree;
- Row Nucleus consumes current content-role authority;
- the snapshot preserves current claim ceilings and `canonical_event_count=UNKNOWN`;
- later historical/side PRs do not need to be replayed to reconstruct C1.

This does **not** mean PR #254 itself should be merged into main. It means C1 files are extracted from the audited final-state content visible at the current snapshot, with the capability-specific provenance below.

## Capability provenance anchors

```text
Cross-Format Reconciliation
  PR #248
  head=b6c13ede9e2d3865eae24bdb3580a3ea3fd45c8e

Metric Definition Policy
  PR #249
  head=c6d0b2a5c8ff70deb917710bd7394cf68c60359e

Aggregate Definition Alignment
  PR #250
  head=6ee946dba6bb55ac12a94e4bf4967cee8099b42d

Provider Metric Dictionary
  PR #251
  head=6ccfb2ddd978ccf470105b528b8ef8637ce408b2

Triangulated Reflection Lineage
  PR #253
  head=45a6cc809ea75bfb1fa85c4788e9fc0016752536

Row Nucleus / coherent Foundation snapshot
  PR #254
  head=a8ae2334473fb792e01c53fb0e6867e8087715c4
```

## C1 final capability/file families

### F01 — Multiformat File Inventory

Final extraction source:
`#254 snapshot content`, inherited from the current Foundation line.

Include:

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

Required retained behaviour:
- multiformat inventory only;
- exact duplicate reflection lineage instead of double counting;
- unsafe XML entity/DTD rejection;
- runtime authority guard;
- flat phone output;
- no sample-match identity leak.

Historical #164 is provenance/donor history, not landing authority.

### F02 — CSV Surface Reader

Final extraction source:
`#254 snapshot content`, including current content-role bridge inherited from the #250 line.

Include:

```text
.github/workflows/csv-surface-reader-lite-v1.yml
csv_surface_reader_lite.py
hpfa/modules/core/csv_surface_reader_lite/contract/csv_surface_reader_lite_v1.json
hpfa/modules/core/csv_surface_reader_lite/src/csv_surface_reader.py
hpfa/modules/core/csv_surface_reader_lite/src/content_role_bridge.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader_regressions.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_csv_surface_reader_team_binding.py
hpfa/modules/core/csv_surface_reader_lite/tests/test_content_role_bridge.py
tools/bootstrap_termux_csv_surface_reader_v1.sh
tools/run_active_match_csv_surface_reader_v1.sh
```

Historical #166 is provenance only.

### F03 — XLSX Surface Reader

Final extraction source:
`#254 snapshot content`, retaining the native OOXML/current reader path from #250.

Include:

```text
.github/workflows/xlsx-surface-reader-lite-v1.yml
xlsx_surface_reader_lite.py
hpfa/modules/core/xlsx_surface_reader_lite/contract/xlsx_surface_reader_lite_v1.json
hpfa/modules/core/xlsx_surface_reader_lite/src/native_ooxml.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_header_semantics.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_runtime_guard.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader/__init__.py
hpfa/modules/core/xlsx_surface_reader_lite/src/xlsx_surface_reader/native_reader.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/__init__.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/ooxml_fixture.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_header_semantics.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_runtime_guard.py
hpfa/modules/core/xlsx_surface_reader_lite/tests/test_xlsx_surface_reader.py
tools/bootstrap_termux_xlsx_surface_reader_v1.sh
tools/run_active_match_xlsx_surface_reader_v1.sh
```

Boundary:
- XLSX is aggregate/table evidence;
- XLSX row is not event identity;
- metric count and percentage surfaces remain semantically distinct.

Historical #170 is provenance only.

### F04 — XML Surface Reader

Final extraction source:
`#254 snapshot content`.

Include:

```text
.github/workflows/xml-surface-reader-lite-v1.yml
xml_surface_reader_lite.py
hpfa/modules/core/xml_surface_reader_lite/contract/xml_surface_reader_lite_v1.json
hpfa/modules/core/xml_surface_reader_lite/src/xml_common.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_rows.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_structure.py
hpfa/modules/core/xml_surface_reader_lite/src/xml_surface_reader.py
hpfa/modules/core/xml_surface_reader_lite/tests/test_xml_surface_reader.py
tools/bootstrap_termux_xml_surface_reader_v1.sh
tools/run_active_match_xml_surface_reader_v1.sh
```

Boundary:
`XML temporal/action surface != tracking truth` and `XML row/instance != canonical event`.

Historical #171 is provenance only.

### F05 — Provider Alias / Field Semantics

Final extraction source:
`#254 snapshot content`.

Include:

```text
.github/workflows/provider-alias-field-semantics-v1.yml
provider_alias_field_semantics_lite.py
hpfa/modules/core/provider_alias_field_semantics_lite/contract/provider_alias_field_semantics_lite_v1.json
hpfa/modules/core/provider_alias_field_semantics_lite/src/provider_alias_field_semantics.py
hpfa/modules/core/provider_alias_field_semantics_lite/tests/test_provider_alias_field_semantics.py
tools/bootstrap_termux_provider_alias_field_semantics_v1.sh
tools/run_active_match_provider_alias_field_semantics_v1.sh
```

Boundary:
`field_mapping_coverage != provider_label_value_semantics_coverage`.

Historical #172 is provenance only.

### F06 — Provider Label / Value Semantics

Final extraction source:
`#254 snapshot content`.

Include:

```text
.github/workflows/provider-label-value-semantics-v1.yml
docs/contracts/provider_label_value_semantics_lite_v1.md
provider_label_value_semantics_lite.py
hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_reviewed_v2.csv
hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json
hpfa/modules/core/provider_label_value_semantics_lite/src/provider_label_value_semantics.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_provider_label_value_semantics_registry_safety.py
hpfa/modules/core/provider_label_value_semantics_lite/tests/test_termux_exact_head_gate.py
tools/bootstrap_termux_provider_label_value_semantics_v1.sh
tools/run_active_match_provider_label_value_semantics_v1.sh
```

The #243 collision correction is already visible in the current #254 snapshot registry:

```text
GOALKEEPER + goal-kick labels
→ scoped RESTART / GOAL_KICK candidate

TEAM + Goal kicks short/medium/long
→ ATTRIBUTE_REFERENCE
→ PASS distance-attribute candidate
→ REFERENCE_ONLY
→ no literal TEAM restart action
```

Therefore #243 is **not** replayed as a separate landing step.

Its Evidence Atom file change is not part of C1 and belongs to the C2 Evidence Spine audit.

### F07 — Content Source Role Resolver

Final extraction source:
`#254 snapshot content`.

Include:

```text
.github/workflows/content-source-role-resolver-lite-v1.yml
content_source_role_resolver.py
docs/contracts/content_source_role_resolver_lite_v1.md
hpfa/modules/core/content_source_role_resolver_lite/src/__init__.py
hpfa/modules/core/content_source_role_resolver_lite/src/content_source_role_resolver.py
hpfa/modules/core/content_source_role_resolver_lite/tests/test_content_source_role_resolver.py
hpfa/modules/core/content_source_role_resolver_lite/tests/test_current_reflection_compat.py
hpfa/modules/core/content_source_role_resolver_lite/tools/active_match_role_diagnostic.py
```

Current #254 tree was directly verified to contain the resolver implementation.

Standalone PR #256 is **not** the extraction authority because its current branch is based on an older #254 head and is presently non-mergeable. Its useful behaviour survives in the coherent current #254 snapshot and is extracted from there.

Required boundary:
- filename may be weak support but cannot admit source role;
- PLAYER / GOALKEEPER / TEAM remain candidate roles;
- CSV/XML same-provider reflection support is not an independent vote;
- no validated team/player/event identity is created.

### F08 — Cross-Format Reconciliation

Capability provenance anchor:
`#248 @ b6c13ede9e2d3865eae24bdb3580a3ea3fd45c8e`.

Final extraction content:
`#254 snapshot`, unless a byte-level comparison before C1 shows a later inherited correction; current capability behaviour must remain equivalent to or stricter than #248.

Include:

```text
.github/workflows/cross-format-reconciliation-v1.yml
cross_format_reconciliation_lite.py
docs/contracts/cross_format_reconciliation_lite_v1.md
hpfa/modules/core/cross_format_reconciliation_lite/contract/cross_format_reconciliation_lite_v1.json
hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json
hpfa/modules/core/cross_format_reconciliation_lite/src/cross_format_reconciliation.py
hpfa/modules/core/cross_format_reconciliation_lite/src/research_hardening.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_cross_format_reconciliation.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_identifier_representation_runtime_guard.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_research_hardening.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_source_role_reason_provenance.py
hpfa/modules/core/cross_format_reconciliation_lite/tests/test_termux_reconciliation_exact_head_gate.py
tools/bootstrap_termux_cross_format_reconciliation_v1.sh
tools/run_active_match_cross_format_reconciliation_v1.sh
```

Required retained behaviour:
- no transitive promotion;
- no cross-role bare-ID join;
- no automatic format winner/majority vote;
- missing counterpart is not contradiction without admitted expectation;
- start/end remain source-timeline evidence only;
- provider identifier representation preserved;
- exact duplicate reflections do not add support volume;
- `canonical_event_count=UNKNOWN`.

### F09 — Metric Definition Policy

Capability provenance anchor:
`#249 @ c6d0b2a5c8ff70deb917710bd7394cf68c60359e`.

Final extraction content:
`#254 snapshot`, with #249 behaviour preserved.

Include:

```text
.github/workflows/metric-definition-policy-lite-v1.yml
configs/metrics/metric_confidence_rules_v1.json
configs/metrics/metric_context_schema_v1.json
configs/metrics/metric_denominator_policy_v1.json
configs/metrics/metric_exposure_policy_v1.json
configs/metrics/metric_misuse_warnings_v1.json
configs/metrics/metric_registry_v1.json
docs/contracts/metric_definition_policy_lite_v1.md
hpfa/modules/core/metric_definition_policy_lite/contracts/metric_definition_policy_lite_v1.schema.json
hpfa/modules/core/metric_definition_policy_lite/src/metric_definition_policy.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_metric_definition_policy.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_metric_definition_policy_r19_adversarial.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_r19_edge_cases.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_r22_postmatch_exposure_semantics.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_runner_duplicate_group_evidence.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_termux_metric_definition_policy_gate.py
hpfa/modules/core/metric_family_registry_lite/src/metric_family_registry.py
hpfa/modules/core/metric_family_registry_lite/tests/test_metric_family_registry.py
tools/bootstrap_termux_metric_definition_policy_v1.sh
tools/run_active_match_metric_definition_policy_v1.sh
```

Do not make `postmatch_analyst_report_lite` or `event_physical_cost_surface_lite` automatic C1 dependencies solely because #249 touched them. Those are separate product/support surfaces and require independent landing need.

### F10 — Aggregate Definition Alignment

Capability provenance anchor:
`#250 @ 6ee946dba6bb55ac12a94e4bf4967cee8099b42d`.

Final extraction content:
`#254 snapshot`, with current source-role compatibility preserved.

Include:

```text
.github/workflows/aggregate-definition-alignment-lite-v1.yml
aggregate_definition_alignment_lite.py
docs/contracts/aggregate_definition_alignment_lite_v1.md
hpfa/modules/core/aggregate_definition_alignment_lite/contract/aggregate_definition_alignment_lite_v1.schema.json
hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json
hpfa/modules/core/aggregate_definition_alignment_lite/src/aggregate_definition_alignment.py
hpfa/modules/core/aggregate_definition_alignment_lite/tests/test_aggregate_definition_alignment.py
hpfa/modules/core/aggregate_definition_alignment_lite/tests/test_termux_aggregate_alignment_exact_head_gate.py
tools/bootstrap_termux_aggregate_definition_alignment_v1.sh
tools/run_active_match_aggregate_definition_alignment_v1.sh
```

Current expected safe state may remain `REVIEW_REQUIRED`; definition candidate is not definition equivalence or measurement invariance truth.

### F11 — Provider Metric Dictionary

Capability provenance anchor:
`#251 @ 6ccfb2ddd978ccf470105b528b8ef8637ce408b2`.

Final extraction content:
`#254 snapshot`, with #251 semantics preserved.

Include:

```text
.github/workflows/provider-metric-dictionary-lite-v1.yml
configs/metrics/metric_conflict_queue_v1.json
configs/metrics/metric_derivation_registry_v1.json
configs/metrics/provider_alias_registry_v1.json
configs/metrics/provider_metric_dictionary_v1.json
docs/contracts/provider_metric_dictionary_lite_v1.md
provider_metric_dictionary_lite.py
hpfa/modules/core/provider_metric_dictionary_lite/src/_provider_metric_dictionary_impl_v7.py
hpfa/modules/core/provider_metric_dictionary_lite/src/provider_metric_dictionary.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round3.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round4.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round5.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round6.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round7.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round8.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round9.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_review_round10.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary_runtime_tools.py
tools/bootstrap_termux_provider_metric_dictionary_v1.sh
tools/run_active_match_provider_metric_dictionary_v1.sh
```

Current safe state remains compatible with provider-definition uncertainty. Candidate metric labels do not create provider-definition truth or comparison permission.

### F12 — Triangulated Reflection Lineage

Capability provenance anchor:
`#253 @ 45a6cc809ea75bfb1fa85c4788e9fc0016752536`.

Final extraction content:
`#254 snapshot`, which consumes this layer directly.

Include:

```text
.github/workflows/triangulated-event-reflection-resolver-lite-v1.yml
triangulated_event_reflection_resolver_lite.py
docs/contracts/triangulated_event_reflection_resolver_lite_v1.md
hpfa/modules/core/triangulated_event_reflection_resolver_lite/src/triangulated_event_reflection_resolver.py
hpfa/modules/core/triangulated_event_reflection_resolver_lite/tests/test_content_role_bridge.py
hpfa/modules/core/triangulated_event_reflection_resolver_lite/tests/test_triangulated_event_reflection_resolver.py
tools/bootstrap_termux_triangulated_event_reflection_resolver_v1.sh
```

Boundary:
- serialization reflection control only;
- CSV/XML are not independent votes;
- same upstream origin and physical-action identity remain ungranted;
- XLSX is not row/action identity.

### F13 — Row Nucleus / G01–G18 Rollup

Final extraction source:
`#254 @ a8ae2334473fb792e01c53fb0e6867e8087715c4`.

Include:

```text
.github/workflows/row-nucleus-inventory-lite-v1.yml
docs/contracts/row_nucleus_inventory_lite_v1.md
row_nucleus_inventory.py
hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_content_role_bridge.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_row_nucleus_inventory.py
tools/bootstrap_termux_row_nucleus_inventory_v1.sh
```

Current claim boundary:

```text
row_nucleus_is_canonical_event=false
physical_action_identity_truth=false
independent_source_vote_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
sequence_truth=false
possession_truth=false
phase_truth=false
production_release=false
```

## Correction / side-branch decisions

### PR #228 — G07 coordinate eligibility

Decision:

```text
DO_NOT_FOLD_INTO_C1_CURRENT_ROW_NUCLEUS
REASSESS_AFTER_CURRENT_SEMANTIC_ROLE_EVIDENCE_EXISTS
```

Reason:
- #228 introduces an administrative coordinate exemption based on semantic-role/downstream-eligibility fields;
- current #254 Row Nucleus intentionally has no reviewed semantic-role producer stacked at that layer;
- current #254 therefore keeps missing coordinates review-bounded and explicitly sets `admin_exemption_admitted=false`;
- importing #228 into C1 would reintroduce a dependency on stale semantic-role assumptions.

This is not deletion of the idea. The exemption concept may be reassessed at C2 once current Evidence Atom / Semantic Role evidence exists.

### PR #232 — XLSX Entity-Metric Row Projection

Decision:

```text
OUTSIDE_C1_FOUNDATION_LANDING
DEFER_TO_LATER_METRIC_EVIDENCE_SLICE
```

Reason: projection/metric-row interpretation is downstream of the Foundation reader/definition boundary and must not turn XLSX into row/action identity.

### PR #234 — Aggregate Derivation Evidence Reconciliation

Decision:

```text
OUTSIDE_C1_FOUNDATION_LANDING
DEFER_TO_EVIDENCE_QUALITY_CLOSURE
```

Reason: it is a downstream aggregate/evidence reconciliation capability, not required to establish the core Foundation file/semantic/source-authority spine.

### PR #243 — Surface-role semantic collision guard

Decision:

```text
LABEL_SEMANTICS_BEHAVIOUR_ALREADY_PRESENT_IN_CURRENT_#254_SNAPSHOT
NO_SEPARATE_C1_REPLAY
EVIDENCE_ATOM_CHANGE_DEFER_TO_C2
```

### PR #256 — standalone Content Source Role Resolver

Decision:

```text
DO_NOT_USE_STANDALONE_PR_AS_EXTRACTION_AUTHORITY
USE_CURRENT_#254_SNAPSHOT_CONTENT
```

Reason: #256 is based on an older #254 head and its current PR mergeability is false, while the resolver implementation and current behaviour are present in the coherent #254 snapshot.

### PR #180

Decision:
`GOVERNANCE_ONLY / NOT_C1_PRODUCT_RUNTIME`.

### PR #258 and other side capabilities

Decision:
`DONOR_OR_DEFERRED_SIDE_CAPABILITY`; do not copy parallel apparatus into C1 when the current producer already carries the required behaviour.

## C1 extraction invariant

For each file family above:

1. extract final content, not historical PR chronology;
2. compare the source blob against the chosen current snapshot before landing;
3. if a later correction is stricter, fold only that correction into the final capability file;
4. never import a stale module wholesale when a current producer exists;
5. keep tests/workflow/runtime runner only where they validate the retained capability contract;
6. do not promote old ACTIVE_MATCH evidence to the future C1 integration head;
7. after C1 is assembled, run exact-head CI and fresh ACTIVE_MATCH where product/runtime behaviour is affected.

## C1 acceptance boundary

Engineering evidence must establish:

```text
one coherent main-based integration head
all required Foundation capability files present
no duplicate parallel implementation selected as authority
current contracts/tests pass
flat phone-output policy retained
sample-match identity leak guard retained
runtime/source authority binding retained
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

Analyst evidence must describe only visible/surface/definition/reconciliation/row-nucleus candidate evidence. It may not claim canonical event identity, physical-action identity, provider-definition truth, measurement invariance, possession, sequence, phase, spatial or tactical truth.

## C0B progress

```text
C0A authority + open-PR classification = CLOSED
C0B Foundation final-state file lineage = CLOSED
C0B Evidence Spine final-state file lineage = NEXT
C0B Reconstruction + Intelligence final-state file lineage = PENDING
```

No merge, auto-merge, release or production binding is authorized by this record.
