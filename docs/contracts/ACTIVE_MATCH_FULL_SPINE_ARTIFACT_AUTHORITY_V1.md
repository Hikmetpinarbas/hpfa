# ACTIVE_MATCH Full-Spine Artifact Authority V1

## Owner

Existing producer:
- `hpfa/modules/core/active_match_spine_runner/src/full_spine_runner.py`

Existing upstream producer:
- `hpfa/modules/core/active_match_spine_runner/src/orphan_capability_sidecars.py`

This contract rehabilitates the current full-spine consumer. It does not create a parallel report, export, story, discovery or evidence engine.

## Purpose

The full-spine output aggregates artifacts from reconstruction, episode, rich-analysis and sidecar lanes. Artifact presence is inventory evidence only. Flattening these paths into `current_invocation_artifacts` must not erase the process-story distinction between diagnostic JSON and assembly-admitted user-facing TXT.

## Invariants

1. `current_invocation_artifacts_are_publication_authority=false` is mandatory on the full-spine surface.
2. `active_match_process_story_sidecar_v1.json` is diagnostic lineage only and may never become analyst-facing publication authority because it appears in the mixed full-spine artifact inventory.
3. `active_match_process_story_sidecar_v1.txt` is the fixed process-story publication-authority artifact identity at this boundary.
4. Upstream payload values may be audited but may not redirect the full-spine authority identity. A malformed or version-skewed parent declaring the JSON diagnostic artifact as publication authority must not be mirrored as authority.
5. Presence flags report only whether the fixed diagnostic/publication artifacts are present in the current invocation. Presence is not admission and does not strengthen football evidence.
6. `process_story_parent_authority_contract_preserved=true` may be reported only when the immediate parent states all of the following:
   - `current_invocation_artifacts_are_publication_authority=false`;
   - `process_story_diagnostic_user_facing_publication_authority=false`;
   - `process_story_publication_authority_artifact=active_match_process_story_sidecar_v1.txt`.
7. Parent-contract mismatch is diagnostic evidence of authority-version skew; it does not authorize a stronger claim or alternative publication artifact.
8. Full-spine TXT must disclose that the mixed artifact inventory is not publication authority and must name the fixed process-story publication-authority artifact.

## Claim locks

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`
- artifact presence != physical-action truth
- diagnostic retention != publication admission
- CI success != physical ACTIVE_MATCH acceptance

## Test requirement

Focused regressions must demonstrate both:
- malicious/version-skewed parent authority redirect cannot promote JSON or the mixed inventory;
- a conforming parent is recognized without changing the fixed full-spine authority identity.
