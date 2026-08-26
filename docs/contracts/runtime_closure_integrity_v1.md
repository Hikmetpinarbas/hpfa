# HPFA Runtime Closure Integrity V1

Status: `IMPLEMENTED_REVIEW_REQUIRED / NOT_PRODUCTION`

This contract hardens existing HPFA infrastructure. It does not create a new football engine.

## Reused producers

```text
core_pipeline_orchestrator_lite
content_source_role_resolver_lite
canonical_ingest_surface_manifest
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

Authority is bound to the explicitly selected execution root. The execution root may itself be resolved to its selected real root. The only admitted ACTIVE_MATCH path remains the direct lexical path:

```text
<selected_execution_root>/runtime/active_single_match/current
```

The execution root is selected independently from the ACTIVE_MATCH candidate. The candidate path cannot define its own authority root.

Admission requires all of the following:

- literal case-sensitive suffix `runtime/active_single_match/current` on the lexical candidate;
- exact lexical equality with `<selected_execution_root>/runtime/active_single_match/current` before authority-component symlinks are followed;
- no forbidden ancestry component in the lexical or resolved candidate path;
- none of `<root>/runtime`, `<root>/runtime/active_single_match`, or `<root>/runtime/active_single_match/current` may be a symlink;
- after resolution, the admitted ACTIVE_MATCH authority must still be contained beneath the selected real execution root.

The symlink rejection is not the only escape control. Resolved-path containment is an independent fail-closed invariant, so an authority escape remains rejected even if filesystem state changes between lexical/symlink inspection and final resolution.

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
runtime_authority_symlink_rejected
runtime_authority_resolved_outside_execution_root
```

A quarantine copy, archive copy, donor/reference/fixture path, sibling checkout, old checkout, symlinked reflection or any other same-suffix reflection cannot silently become ACTIVE_MATCH truth.

## Canonical root CLI execution-root binding

The canonical repository-root operator entry point is:

```text
active_match_spine_runner.py
```

It exposes an explicit:

```text
--execution-root <selected_runtime_execution_root>
```

This allows the exact-head product code checkout and the selected runtime execution root to be intentionally different without introducing a wrapper or hardcoded environment path. The CLI forwards the value directly to `run_spine_check(..., root=ROOT, execution_root=args.execution_root)`.

If `--execution-root` is omitted, the CLI passes `None` and preserves the existing safe runner default: the product checkout root is used as the execution root. No `find`, first-match selection, sibling-checkout discovery, quarantine discovery, or other implicit runtime-root selection is performed.

Therefore an ACTIVE_MATCH candidate outside the product checkout root is fail-closed when `--execution-root` is omitted. A separate runtime root is admissible only when the operator explicitly supplies that root and the existing authority, ancestry, symlink, and resolved-containment gates all pass.

## Content-based source-role admission

The canonical ACTIVE_MATCH spine reuses the existing HPFA-native `content_source_role_resolver_lite` before `canonical_ingest_surface_manifest`.

Filename text is diagnostic support only and is never sufficient for role admission. The manifest consumes only admitted resolver evidence with claim ceiling:

```text
SOURCE_ROLE_CANDIDATE_ONLY
```

Admissible role evidence remains candidate-only:

```text
PLAYER_SURFACE_CANDIDATE
TEAM_SURFACE_CANDIDATE
GOALKEEPER_SURFACE_CANDIDATE
```

The manifest does not infer these roles from `Players`, `Teams`, `Goalkeepers`, or equivalent filename tokens. A missing resolver report, non-PASS resolver report, unresolved/conflicting role, unrecognized role candidate, mismatched input root, promoted canonical-event claim, or promoted production-release claim fails closed rather than falling back to filename inference.

Role admission does not validate team, player, or event identity. The following remain false/unknown:

```text
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Runtime surface allowlist

The current `active_match_spine_runner` may execute/import only its explicitly registered product surfaces. The resolver's existing HPFA-native reader/inventory dependencies are registered as part of the same runtime dependency chain:

```text
hpfa/modules/core/content_source_role_resolver_lite
hpfa/modules/core/csv_surface_reader_lite
hpfa/modules/core/multiformat_file_inventory_lite
hpfa/modules/core/triangulated_event_reflection_resolver_lite
hpfa/modules/core/xlsx_surface_reader_lite
hpfa/modules/core/xml_surface_reader_lite
hpfa/modules/core/canonical_ingest_surface_manifest
hpfa/modules/core/composite_integration_office
```

The allowlist is deliberately narrow and versioned in code. A new runtime dependency must be reviewed and added explicitly rather than discovered permissively. Resolver dependencies are also checked against exact product origins before use. The XML reader's existing sibling compatibility modules (`xml_common`, `xml_rows`, `xml_structure`) are loaded only from the validated product XML-reader surface; cached modules from another origin fail closed. The XLSX reader package origin is bound to its product `xlsx_surface_reader/__init__.py` entrypoint.

Hard-block families:

```text
runtime_surface_outside_product_repo
unregistered_runtime_surface
archive_surface_import_attempted
donor_surface_runtime_bound
reference_only_surface_executed
fixture_surface_used_as_active_match
runtime_module_origin_mismatch
```

Drive, Dropbox, donor repositories, archives, reference-only material and fixtures cannot become executable ACTIVE_MATCH authority through this runner.

## Compatibility

The change preserves existing status, surface-manifest, boundary-score and claim-lock fields. Root-binding and candidate-role evidence is additive:

```text
execution_root
active_match_root_binding_policy
source_role_resolution
runtime_surface_policy.active_match_relative_authority_path
runtime_surface_policy.forbidden_active_match_ancestry_parts
runtime_surface_policy.authority_symlinks_allowed=false
runtime_surface_policy.resolved_authority_must_remain_within_execution_root=true
runtime_surface_policy.reflection_authority_allowed=false
surface_manifest.source_role_candidate_admission_policy=CONTENT_EVIDENCE_ONLY
surface_manifest.filename_support_used_for_admission=false
```

## Mandatory regressions

- first blocking stage remains first failure;
- initial upstream failure cannot be overwritten;
- later outputs are disclosed as blocked;
- review-only runs do not invent a failure;
- successful runs have no first failure;
- canonical root CLI accepts a direct ACTIVE_MATCH under an explicitly supplied execution root even when `PRODUCT_ROOT != EXECUTION_ROOT`;
- canonical root CLI rejects a valid same-suffix candidate when the supplied execution root is a wrong/reflection root;
- canonical root CLI omission of `--execution-root` defaults to product root and does not discover an external runtime root;
- eight neutral filenames containing none of `Players`, `Teams`, or `Goalkeepers` are admitted as exactly three goalkeeper, three player, and two team surface candidates from content/structural/relational evidence;
- filename support is never used for role admission;
- unresolved/conflicting source-role evidence fails closed at the canonical manifest/spine boundary;
- candidate role admission never promotes team/player/event identity;
- direct `<execution_root>/runtime/active_single_match/current` authority passes;
- `<root>/runtime` symlink to another checkout fails closed;
- `<root>/runtime/active_single_match` symlink to an external/reflection path fails closed;
- `<root>/runtime/active_single_match/current` symlink to an external/reflection path fails closed;
- resolved authority escape outside the selected real execution root fails closed independently of the symlink precheck;
- quarantine reflection with the same suffix fails closed;
- a same-suffix candidate in another checkout/reflection cannot become the selected truth;
- forbidden authority ancestry fails closed even if that contaminated root was explicitly selected;
- ACTIVE_MATCH authority suffix remains case-sensitive;
- no absolute phone home path is hardcoded;
- nested phone output remains rejected;
- allowed product runtime surface executes;
- imported resolver, resolver dependencies, manifest and optional runtime modules are bound to validated product origins;
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
