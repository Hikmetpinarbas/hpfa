# Triplex Source Alignment Guard V1 — Current-Main Capability-Equivalence Check

Status: `DISCOVERY_PASS_PLAN_ONLY`

Repository authority: `Hikmetpinarbas/hpfa`

Main SHA audited: `4df891d845c77909cab37554a046e58a8ce3822d`

Runtime authority: `runtime/active_single_match/current`

Canonical event count: `UNKNOWN`

## Purpose

Resolve whether current main already contains executable producers equivalent to parts of `Triplex Source Alignment Guard V1`, without counting donor artifacts or open pull requests as product truth.

Policy: `ADAPT_NOT_COPY`

## Corrected current-main finding

The first pass under-counted existing executable conflict-governance capability. Current main contains:

- `hpfa/modules/core/canonical_ingest_surface_manifest/src/surface_manifest.py`
- `hpfa/modules/core/source_mapping_contract_lite/src/source_mapping_contract.py`
- `hpfa/modules/core/source_conflict_registry_lite/src/source_conflict_registry.py`
- `hpfa/modules/core/source_conflict_registry_lite/tests/test_source_conflict_registry.py`
- `hpfa/modules/core/primary_surface_review_resolution_lite/src/primary_surface_review_resolution.py`
- `hpfa/modules/core/identity_review_resolution_lite/src/identity_review_resolution.py`
- `docs/governance/runtime_pack_v1/source_role_registry.json`

`source_conflict_registry_lite_v1` is executable and fail-closed. It detects, among other conditions:

- missing supported mapping surfaces;
- unmapped event-like surfaces;
- event-like versus aggregate-support role misuse;
- review-required mapping decisions;
- unknown source roles;
- schema divergence between event-like formats sharing a role;
- row-count discrepancy between event-like formats sharing a role;
- unresolved primary-surface state.

It explicitly preserves:

- `canonical_event_count=UNKNOWN`;
- `deduplicated_event_count=UNKNOWN`;
- `event_count_claim_allowed=false`;
- `production_binding_allowed=false`.

Therefore the Triplex target is not `NOT_FOUND`. The correct classification is `PARTIAL / NOT_RUNTIME_PROVEN`.

## Capability delta that remains

No current-main producer was resolved that jointly establishes all of the following:

- explicit CSV/XML/XLSX `independence_group` adjudication;
- upstream-origin lineage comparison;
- duplicate-surface detection across differently formatted exports of the same upstream stream;
- derived-output-as-source rejection based on lineage rather than path/name heuristics alone;
- canonical event identity agreement across source surfaces;
- ambiguous time-window match routing;
- unit, scope and denominator compatibility before fusion;
- a unified fusion-admissibility decision and claim-capacity downgrade;
- a typed Triplex contract/schema and deterministic end-to-end test pack.

Existing conflict detection is a reusable prerequisite. It must be extended or adapted rather than replaced by a parallel conflict registry.

## Donor boundary

The donor Triplex pack remains `SPEC_CONTRACT`, with a closed claim gate and `truth_claim=false`. It is design evidence only. No donor code or pseudocode is product truth.

## Corrected classification

```text
DIRECTIVE CAPABILITY = Triplex Source Alignment Guard V1
CURRENT-MAIN PRIMARY STATUS = PARTIAL
CURRENT-MAIN RUNTIME STATUS = NOT_RUNTIME_PROVEN
EXECUTABLE PREREQUISITE = source_conflict_registry_lite_v1
DONOR EQUIVALENCE = SPEC_CONTRACT
ACTIVE_MATCH_PROVEN = NO
PRODUCTION_RELEASE = FALSE
```

## Engineering evidence

- current-main SHA pinned: yes
- executable source-conflict producer inspected: yes
- deterministic source-conflict tests resolved: yes
- adjacent surface-manifest producer inspected: yes
- adjacent source-mapping producer inspected: yes
- source-role registry considered: yes
- tests executed in this audit: no
- runtime output written in this audit: no
- ACTIVE_MATCH execution: no

## Analyst evidence

No match was analyzed and no football-performance claim was generated.

Product value: prevents an unnecessary parallel conflict module and narrows the next implementation to lineage, independence, duplicate-origin, event-identity and unit/scope/denominator gates.

## Claim boundary

```text
canonical_event_count = UNKNOWN
source independence truth = false
canonical event identity truth = false
fusion admissibility truth = false
analytical claim capacity = not established
production release = false
```

## Smallest next implementation candidate

Build an HPFA-native Triplex compatibility adapter around existing producers, not a replacement registry. The adapter should consume surface-manifest, source-mapping and source-conflict outputs, then add only the unresolved fields and fail-closed decisions:

1. `independence_group` and `upstream_origin_id`;
2. duplicate/dependency adjudication;
3. canonical event identity compatibility;
4. time-window ambiguity state;
5. unit/scope/denominator compatibility;
6. fusion-admissibility and claim-capacity decision.

Before implementation, the adapter contract and deterministic test matrix must explicitly preserve the existing source-conflict output and ACTIVE_MATCH authority boundary.