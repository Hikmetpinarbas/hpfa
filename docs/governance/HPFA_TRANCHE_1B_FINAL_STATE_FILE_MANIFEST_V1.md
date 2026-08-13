# HPFA Tranche 1B — Final-State File Manifest V1

Status: `DISCOVERY_PASS_PLAN_ONLY / FILE_EXTRACTION_MANIFEST_READY / G16_DEFERRED_BY_CONTRACT / NO_PRODUCT_BRANCH_YET / NOT_PRODUCTION`

Date: 2026-08-13

## Purpose

Define the exact final-state capability/file families for Landing 1B:

```text
Metric Definition Policy primitives
→ Aggregate Definition Alignment
→ Provider Metric Dictionary contract pack
→ Row Nucleus Inventory
→ G01–G18 structural quality rollup
→ G07 eligibility correction
```

Landing 1B does **not** implement new football metrics and does not close G16 derivation reconciliation.

It establishes the policy/data-quality boundary needed to enter Evidence Spine without inventing provider definitions or canonical events.

This is not a chronological PR merge list and not a cherry-pick recipe.

## Authority / extraction rule

Historical PRs identify provenance and capability boundaries. For files still present at the audited development checkpoint, extraction should use the final compatible content at:

`fdb8e109daebd7a9875d6f257011cb93e0372677`

subject to per-capability audit and later correction fold-ins.

Landing base must be the then-current `main` after Tranche 0 and Landing 1A decisions.

Drive/Dropbox remain `REFERENCE_ONLY / DONOR_SUPPORT`.

## Runtime dependency finding

Current Row Nucleus ACTIVE_MATCH runner explicitly refreshes and consumes:

```text
aggregate_definition_alignment_lite.py
  --metric-config-dir configs/metrics
  --registry sportsbase_aggregate_definition_candidates_v1.json

provider_metric_dictionary_lite
  configs/metrics

row_nucleus_inventory_lite.py
  --aggregate-alignment aggregate_definition_alignment_lite_v1.json
  --metric-dictionary provider_metric_dictionary_lite_v1.json
```

Therefore the consumed Metric Definition Policy, Aggregate Definition Alignment and Provider Metric Dictionary files are real Landing 1B dependencies. They are not optional documentation merely because they do not emit metric values.

## B01 — Metric Definition Policy Lite

Historical source PR: `#178`

Historical PR head:

`9302f2a746576982e8e1a5235e627b90f23f54b0`

Candidate file family:

```text
.github/workflows/metric-definition-policy-lite-v1.yml
configs/metrics/metric_confidence_rules_v1.json
configs/metrics/metric_context_schema_v1.json
configs/metrics/metric_denominator_policy_v1.json
configs/metrics/metric_misuse_warnings_v1.json
configs/metrics/metric_registry_v1.json
docs/contracts/metric_definition_policy_lite_v1.md
hpfa/modules/core/metric_definition_policy_lite/contracts/metric_definition_policy_lite_v1.schema.json
hpfa/modules/core/metric_definition_policy_lite/src/metric_definition_policy.py
hpfa/modules/core/metric_definition_policy_lite/tests/test_metric_definition_policy.py
```

### Why all five policy/config inputs are required

`load_policy_pack()` consumes exactly:

```text
metric_registry_v1.json
metric_denominator_policy_v1.json
metric_context_schema_v1.json
metric_confidence_rules_v1.json
metric_misuse_warnings_v1.json
```

A rate/percentage/ratio/per-90 definition must resolve denominator policy and explicit denominator behaviour. Missing denominator, unresolved policy reference, zero-denominator ambiguity or missing-denominator ambiguity remains blocked/fail-closed.

### Claim boundary

This layer produces:

`metric definition candidate / eligibility policy`

It does **not** produce:

```text
metric value
metric quality truth
provider equivalence truth
tactical truth
canonical event
production release
```

No uncalibrated confidence threshold or donor default may be promoted merely because a historical research file contains one.

## B02 — Aggregate Definition Alignment Lite

Historical source PR: `#181`

Current PR metadata head at audit:

`81e4da6dac1133cd1c867c41ee1f883c68adccac`

Note: historical PR body contains older head text; current ref metadata takes precedence. Landing still uses final compatible file content rather than trusting either narrative head blindly.

Candidate file family:

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

Mandatory semantics:

```text
same label != same definition
count parity != definition equivalence
generic action family != exact derivation component
ACTIVE_MATCH execution completed != definition alignment cleared
```

The module requires Metric Definition Policy as an upstream contract and only exact reviewed semantic occurrence candidates for required components.

Unresolved provider operational definition and unresolved derivation lineage legitimately produce `REVIEW_REQUIRED`.

No metric comparison/value/claim is opened here.

## B03 — Provider Metric Dictionary Lite

Historical source PR: `#183`

Historical head:

`a29efff4ab77e15fb3d42c72cffada89bccdabe1`

Candidate file family:

```text
.github/workflows/provider-metric-dictionary-lite-v1.yml
configs/metrics/metric_conflict_queue_v1.json
configs/metrics/metric_derivation_registry_v1.json
configs/metrics/provider_alias_registry_v1.json
configs/metrics/provider_metric_dictionary_v1.json
docs/contracts/provider_metric_dictionary_lite_v1.md
hpfa/modules/core/provider_metric_dictionary_lite/src/provider_metric_dictionary.py
hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary.py
provider_metric_dictionary_lite.py
```

`provider_metric_dictionary_lite` consumes exactly:

```text
provider_metric_dictionary_v1.json
provider_alias_registry_v1.json
metric_derivation_registry_v1.json
metric_conflict_queue_v1.json
```

Mandatory preservation:

```text
provider_id + provider_version + metric_id = definition namespace key
same semantic metric != same provider definition
forward != progressive
progressive != progressive_open
provider proprietary definition gaps remain explicit
```

Rate/percentage definitions require explicit numerator/denominator and zero-denominator handling.

Tracking-only truth tokens cannot be leaked through an event-only-compatible metric declaration.

`PROVIDER_DEFINITION_REQUIRED` is a valid unresolved status, not a reason to invent a definition.

## B04 — Row Nucleus Inventory + G01–G18 structural rollup

Historical source PR: `#185`

Current PR metadata head at audit:

`366e249ea8dd39767a5a9de208f26b5f8661e657`

Candidate base file family:

```text
.github/workflows/row-nucleus-inventory-lite-v1.yml
docs/contracts/row_nucleus_inventory_lite_v1.md
hpfa/modules/core/row_nucleus_inventory_lite/contract/row_nucleus_inventory_lite_v1.json
hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py
hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory_hardened.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_row_nucleus_inventory.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_semantic_role_clearance.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_termux_row_nucleus_exact_head_gate.py
row_nucleus_inventory_lite.py
tools/bootstrap_termux_row_nucleus_inventory_v1.sh
tools/run_active_match_row_nucleus_inventory_v1.sh
```

### Mandatory final-state behaviours

- runtime source bytes rehash against inventory/reader lineage;
- same-role CSV/XML row surfaces reconciled without canonical-event promotion;
- exact duplicate reflections preserved and not double-counted;
- cross-ID collision candidates visible;
- CSV/XML row semantics separated from XLSX aggregate-label overlay;
- exact-reviewed non-action semantic roles may clear only through explicit role/eligibility contract;
- ACTION_ANCHOR still requires a unique action family;
- unknown/fallback/conflict/unregistered role remains review-required;
- row nucleus remains candidate-only.

The current development file content should be used because later corrections modify the historical #185 file state.

## B05 — G07 Coordinate Eligibility Correction

Correction source PR: `#228`

Exact correction head:

`f8ebee132034630f30b649a5223a6be0e5dd8015`

Changed capability files:

```text
hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_g07_active_match_verifier.py
hpfa/modules/core/row_nucleus_inventory_lite/tests/test_g07_coordinate_eligibility.py
tools/verify_g07_coordinate_eligibility_active_match_v1.py
```

### Final correction rule

Coordinate exemption is allowed only when:

```text
semantic_role_candidates ⊆ {
  PERIOD_OR_META,
  MATCH_BOUNDARY,
  ADMINISTRATIVE,
  ADMINISTRATIVE_MARKER
}
AND
downstream_eligibility_candidates == {ADMIN_ONLY}
```

Mixed, unknown or action-bearing nuclei remain coordinate-required.

Missing numeric coordinate and numeric zero remain distinct.

The 12 historical ADMIN_ONLY missing-coordinate nuclei remain visible evidence; they are not deleted or converted into spatial actions.

G07 PASS does not open coordinate-frame/progression gates by itself.

## G16 — intentionally excluded from Landing 1B closure

Landing 1B preserves G16 as an explicit quality gate but does not force its full derivation reconciliation to execute before Evidence Spine.

Current full G16 recheck requires:

```text
xlsx_entity_metric_row_projection_lite_v1
+ evidence_atom_inventory_lite_v1
+ match_local_identity_candidates_lite_v1
+ provider_label_value_semantics_lite_v1
+ aggregate_definition_alignment_lite_v1
→ aggregate_derivation_evidence_reconciliation_lite_v1
```

Therefore these are **excluded from Landing 1B**:

```text
xlsx_entity_metric_row_projection_lite (#232)
aggregate_derivation_evidence_reconciliation_lite (#234)
evidence_atom_inventory_lite (#188 / later correction state)
match_local_identity_candidates_lite (#190)
```

They belong to Tranche 2 / Tranche 2-exit cross-tranche quality closure.

Allowed Foundation exit state:

`G16=REVIEW_REQUIRED / RECHECK_DEFERRED_BY_DECLARED_DEPENDENCY`

This is not a bypass. It is the explicit dependency state.

`G16_RECHECK_ADMITTED != G16_PASS` remains mandatory.

## Donor/reference audit

### Dropbox — denominator rule donor

Reviewed:

`METRIC_DENOMINATOR_RULES_B06.csv`

Useful donor principle:

- volume requires observation window;
- rate requires opportunity denominator;
- sequence/consequence/restart/transition rates require an eligible denominator;
- missing denominator should block/downgrade the rate rather than permit interpretation.

This supports the current policy architecture but does not define SportsBase proprietary metrics.

### Google Drive — metric schema/encyclopedia donor

Historical Drive metric-schema material correctly reinforces that metric definitions need explicit numerator/denominator/data scope.

However Drive encyclopedic and architecture material also contains provider-generalized thresholds, tracking-derived constructs, physical/psychological models and tactical-language assumptions.

These are:

`REFERENCE_ONLY / DONOR_SUPPORT`

and must not be imported into Landing 1B as provider truth, calibrated threshold, tracking truth or tactical truth.

Current HPFA product contracts remain authoritative.

## Landing 1B validation matrix

At minimum, consolidated Landing 1B must verify:

```text
metric policy pack versions align
all metric policy references resolve or fail closed
rate definitions have explicit denominators
zero-denominator behaviour explicit
missing-denominator behaviour explicit
aggregate alignment requires metric-policy readiness
aggregate same-label/count-parity cannot promote definition equivalence
provider metric namespace key uniqueness
provider definition status vocabulary valid
provider metric rates require explicit fraction
tracking-only truth cannot leak through event-only declaration
row-nucleus runtime SHA lineage
exact duplicate suppression
cross-ID collision visibility
row-surface vs XLSX aggregate semantic separation
non-action semantic clearance contract
G07 eligibility-aware denominator
missing != zero
G16 remains explicit deferred review
sample identity leak guard
flat phone output guard
runtime authority equality
canonical_event_count=UNKNOWN
production_release=false
```

## ACTIVE_MATCH acceptance

Landing 1B must run **after Landing 1A final-state head exists** and on the exact consolidated integration head against:

`runtime/active_single_match/current`

Engineering evidence must include:

- exact product branch/head;
- refreshed 1A upstream outputs;
- metric policy/aggregate/dictionary stages;
- Row Nucleus output;
- G01–G18 rollup;
- G07 evidence;
- explicit G16 deferred dependency;
- no hard blocks unless the tranche is rejected;
- output and source-lineage integrity.

Analyst evidence must state only:

- which visible row/aggregate surfaces passed structural/semantic quality gates;
- where review/deferred gates remain;
- why any denominator/definition uncertainty prevents stronger metric claims.

No canonical event, tracking, tactical or provider-definition truth is produced.

## Next action

After Tranche 0 review decision and Landing 1A implementation/revalidation, create Landing 1B from then-current main/integration ancestry using this final-state manifest.

Do not merge historical #178/#181/#183/#185/#228 PRs as a train.

```text
LANDING_1B_FILE_MANIFEST=READY
G16_FULL_RECONCILIATION=DEFERRED_TO_TRANCHE_2_EXIT
PRODUCT_BRANCH=NOT_CREATED_YET
ACTIVE_MATCH_CONSOLIDATED_HEAD=NOT_RUN
MERGE=NOT_AUTHORIZED
canonical_event_count=UNKNOWN
production_release=false
```
