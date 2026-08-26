# HPFA Runtime Closure Integrity V1

Status: `IMPLEMENTED_REVIEW_REQUIRED / NOT_PRODUCTION`

This contract hardens existing HPFA infrastructure. It does not create a new football engine.

## Reused producers

```text
core_pipeline_orchestrator_lite
active_match_spine_runner
```

## First-failure disclosure

Every orchestrated run must expose:

```text
first_failed_node
first_failed_reason_code
first_failed_artifact_id
first_failed_stage_index
upstream_status
blocked_outputs
```

Rules:

- the earliest admitted failure is preserved;
- a downstream wrapper failure cannot overwrite an earlier upstream root failure;
- outputs belonging to stages not executed after a halt are listed under `blocked_outputs`;
- review-only state is not silently relabeled as failure;
- successful runs expose no first failure.

## ACTIVE_MATCH authority

The runner does not memorize an absolute Termux location as product truth and does not select authority from an arbitrary `find` result.

Authority is bound to the explicitly selected execution root. The only admitted ACTIVE_MATCH path is the direct path:

```text
<execution_root>/runtime/active_single_match/current
```

The execution root is selected independently from the ACTIVE_MATCH candidate. The candidate path cannot define its own authority root.

Admission requires all of the following:

- literal case-sensitive suffix `runtime/active_single_match/current`;
- exact equality with `<execution_root>/runtime/active_single_match/current` after path resolution;
- no forbidden ancestry component in the resolved candidate path.

Forbidden ACTIVE_MATCH ancestry components include at least:

```text
quarantine
archive
archives
donor
donors
reference_only
fixtures
```

Rejections are explicit:

```text
runtime_authority_path_invalid
runtime_authority_forbidden_ancestry
runtime_authority_root_binding_mismatch
```

A quarantine copy, archive copy, donor/reference/fixture path, sibling checkout, old checkout or any other reflection with the same final suffix cannot silently become ACTIVE_MATCH truth merely because the suffix matches.

## Runtime surface allowlist

The current `active_match_spine_runner` may execute/import only its explicitly registered product surfaces:

```text
hpfa/modules/core/canonical_ingest_surface_manifest
hpfa/modules/core/composite_integration_office
```

The allowlist is deliberately narrow and versioned in code. A new runtime dependency must be reviewed and added explicitly rather than discovered permissively.

Hard-block families:

```text
runtime_surface_outside_product_repo
unregistered_runtime_surface
archive_surface_import_attempted
donor_surface_runtime_bound
reference_only_surface_executed
fixture_surface_used_as_active_match
```

Drive, Dropbox, donor repositories, archives, reference-only material and fixtures cannot become executable ACTIVE_MATCH authority through this runner.

## Compatibility

The change preserves existing status, surface-manifest, boundary-score and claim-lock fields. Root-binding evidence is additive:

```text
execution_root
active_match_root_binding_policy
runtime_surface_policy.active_match_relative_authority_path
runtime_surface_policy.forbidden_active_match_ancestry_parts
runtime_surface_policy.reflection_authority_allowed=false
```

## Mandatory regressions

- first blocking stage remains first failure;
- initial upstream failure cannot be overwritten;
- later outputs are disclosed as blocked;
- review-only runs do not invent a failure;
- successful runs have no first failure;
- direct `<execution_root>/runtime/active_single_match/current` authority passes;
- quarantine reflection with the same suffix fails closed;
- a same-suffix candidate in another checkout/reflection cannot become the selected truth;
- forbidden authority ancestry fails closed even if that contaminated root was explicitly selected;
- ACTIVE_MATCH authority suffix remains case-sensitive;
- no absolute phone home path is hardcoded;
- nested phone output remains rejected;
- allowed product runtime surface executes;
- unregistered/archive/donor/reference/fixture surfaces fail closed;
- sample match identity leakage remains forbidden.

## Claim boundary

```text
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
phase_truth=false
possession_truth=false
sequence_truth=false
rhythm_truth=false
tactical_truth=false
production_release=false
```

This contract produces engineering integrity evidence only. It does not promote football truth or production release.
