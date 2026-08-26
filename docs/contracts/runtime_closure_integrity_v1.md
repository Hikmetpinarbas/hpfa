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

The runner does not memorize an absolute Termux location as product truth.

The supplied runtime path must resolve to the authority suffix:

```text
runtime/active_single_match/current
```

Any other runtime suffix is rejected as:

```text
runtime_authority_path_invalid
```

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

The change is additive to current result contracts. Existing status, surface-manifest, boundary-score and claim-lock fields are preserved.

## Mandatory regressions

- first blocking stage remains first failure;
- initial upstream failure cannot be overwritten;
- later outputs are disclosed as blocked;
- review-only runs do not invent a failure;
- successful runs have no first failure;
- ACTIVE_MATCH authority suffix is enforced without hardcoding an absolute phone path;
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
