# HPFA Capability Closure Guard Lite V1

Status: `IMPLEMENTATION_REVIEW_REQUIRED / NOT_PRODUCTION`

Issue: `#220`

## Product Node

```text
capability_closure_guard_lite
```

## Purpose

Provide one read-only, deterministic, fail-closed repository audit for the question:

```text
Does this HPFA capability have a closed current-product chain?
```

This is a governance/integrity guard, not a football engine, registry, runtime selector, release controller or ACTIVE_MATCH runner.

## Reused authority and vocabulary

The guard reuses current product sources:

```text
docs/governance/runtime_pack_v1/module_governance_matrix.tsv
docs/governance/runtime_pack_v1/source_role_registry.json
docs/governance/runtime_pack_v1/release_status_normalizer.json
docs/contracts/*
hpfa/modules/**/src/*
hpfa/modules/**/tests/*
hpfa/modules/core/active_match_spine_runner/src/spine_runner.py
active_match_spine_runner.py
```

`module_governance_matrix.tsv` is discovery seed only. Its `current_status` field is never accepted as capability truth by itself.

`source_role_registry.json` supplies authority vocabulary. In particular:

```text
GITHUB_PRODUCT_REPO = current product code authority
ACTIVE_MATCH_RUNTIME_AUTHORITY = runtime match evidence authority
```

`release_status_normalizer.json` supplies release vocabulary. `PASS`, tests or CI do not imply ACTIVE_MATCH evidence or production release.

Historical PRs, branches, donor repositories, archives, Drive and Dropbox are not scanned as current capability truth.

## Six evidence links

Every classified capability exposes exactly six boolean evidence fields:

```text
contract
implementation
non_test_consumer
test
runtime_binding
active_match_evidence
```

### CONTRACT

`true` only when a current-main contract under `docs/contracts` directly names/covers the capability.

A governance row, issue, comment, historical PR or filename outside `docs/contracts` is not contract evidence.

### IMPLEMENTATION

`true` only when a current product module under `hpfa/modules/*/<capability>/src` contains executable Python source.

Same-content files inside the same capability are grouped by SHA-256 as reflections and do not create independent implementation count.

### NON_TEST_CONSUMER

`true` only when a different current-product Python surface imports the capability implementation.

The following never qualify:

```text
tests
CI/workflow YAML
docs
governance text
comments
fixtures
archive/reference/donor surfaces
```

### TEST

`true` when current product tests exist for the implementation or import its implementation surface.

A test is evidence of tested behavior only; it is never a non-test consumer or runtime binding.

### RUNTIME_BINDING

`true` only when the current executable runtime path binds the capability.

For current ingestion/runtime closure this is derived from the existing `active_match_spine_runner` runtime surface allowlist or the canonical root spine entrypoint. A governance `runtime_dependency` string alone is not runtime evidence.

### ACTIVE_MATCH_EVIDENCE

`true` only when a supplied machine-readable evidence envelope:

- declares `ACTIVE_MATCH_RUNTIME_AUTHORITY`;
- is bound to the exact current Git tree SHA;
- preserves `canonical_event_count=UNKNOWN`;
- preserves `true_action_count=UNKNOWN`;
- preserves `production_release=false`;
- proves target capability execution and runtime binding;
- or contains an admitted `active_match_spine_check` artifact that proves execution of the spine/resolver/manifest path.

The guard never runs ACTIVE_MATCH itself.

If no evidence envelope is supplied, every capability has:

```text
active_match_evidence=false
```

No historical PR/branch result is searched to fill that gap.

## Decisions and precedence

Precedence is deterministic:

```text
1 SUPERSEDED_CONTRACT
2 ORPHAN_CONTRACT
3 TEST_ONLY_SURFACE
4 ACTIVE_CONTRACT
5 UNBOUND_IMPLEMENTATION
```

### ACTIVE_CONTRACT

Requires all six links:

```text
contract=true
implementation=true
non_test_consumer=true
test=true
runtime_binding=true
active_match_evidence=true
```

and no corroborated supersession.

### ORPHAN_CONTRACT

```text
contract=true
implementation=false
```

unless current successor implementation corroborates supersession.

### TEST_ONLY_SURFACE

```text
implementation=true
test=true
non_test_consumer=false
runtime_binding=false
```

CI is not a consumer and cannot prevent this classification.

### UNBOUND_IMPLEMENTATION

Implementation exists but the chain is not closed and the capability is neither test-only nor superseded.

Reason codes identify missing links, including:

```text
missing:contract
missing:non_test_consumer
missing:test
missing:runtime_binding
missing:active_match_evidence
```

### SUPERSEDED_CONTRACT

A static `SUPERSEDED_BY_*` governance hint is insufficient.

The guard requires all of:

```text
current contract for predecessor
SUPERSEDED_BY_* hint
current product implementation for named successor
```

Without successor implementation the predecessor remains classified from current code reality, normally `ORPHAN_CONTRACT`.

## Golden acceptance cases

With an admitted current-tree ACTIVE_MATCH evidence envelope:

```text
active_match_spine_runner                  -> ACTIVE_CONTRACT
content_source_role_resolver_lite          -> ACTIVE_CONTRACT
canonical_ingest_surface_manifest          -> ACTIVE_CONTRACT
core_pipeline_orchestrator_lite            -> TEST_ONLY_SURFACE
support_report_concept_surface_gate_lite   -> SUPERSEDED_CONTRACT
```

Without ACTIVE_MATCH evidence, the first three must not remain `ACTIVE_CONTRACT`.

## Outputs

Machine-readable:

```text
capability_closure_guard_lite_v1.json
```

Analyst/operator summary:

```text
capability_closure_guard_lite_v1.txt
```

Outputs contain evidence paths, reflection groups, supersession corroboration, decision and reason codes.

## False-positive protections

Mandatory regressions cover:

- docs are not consumers;
- CI workflows are not consumers;
- tests are not consumers;
- governance status alone is not truth;
- stale ACTIVE_MATCH evidence tree fails closed;
- promoted canonical-event/action/release claims fail closed;
- same-SHA reflections are collapsed;
- static supersession without current successor implementation is rejected;
- ACTIVE_CONTRACT cannot exist without ACTIVE_MATCH evidence;
- current five golden cases classify as specified when admitted evidence is provided.

## Claim boundary

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
phase_truth=false
possession_truth=false
sequence_truth=false
tactical_truth=false
```

This guard produces product-closure engineering evidence only.

## Release boundary

A successful guard run is not:

```text
ACTIVE_MATCH_EVIDENCE_PASS
PRODUCTION_RELEASE
```

unless the specific evidence links separately support those statuses. The guard itself cannot merge, release, select runtime authority or promote football truth.
