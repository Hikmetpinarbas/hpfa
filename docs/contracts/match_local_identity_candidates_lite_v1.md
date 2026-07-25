# Match-Local Identity Candidates Lite V1

## Purpose

This node links visible evidence atoms to team and actor identity candidates inside one runtime-bound match surface.

It does not establish global roster, person, team or event identity.

## Input

Only `evidence_atom_inventory_lite_v1.json` is accepted.

The input must provide:

- unique evidence atom IDs;
- one consistent match-surface binding;
- source and runtime SHA lineage;
- allowed PLAYER, TEAM and GOALKEEPER source roles;
- evidence-atom count integrity;
- `canonical_event_count=UNKNOWN`;
- `production_release=false`.

## Candidate extraction

Actor candidates are extracted only for PLAYER and GOALKEEPER surface atoms when `code_raw` ends exactly with ` - {raw_label}` and leaves a non-empty subject prefix.

The prefix may expose candidate-only fields:

```text
actor_subject_raw_candidate
actor_name_raw_candidate
actor_provider_id_candidate
jersey_number_candidate
```

Team candidates are derived only from `team_raw_candidate`:

```text
team_subject_raw_candidate
team_name_raw_candidate
team_provider_id_candidate
```

Provider IDs and jersey numbers remain candidates. They are not validated identities.

## Binding rules

- TEAM surface atoms receive team-candidate bindings only.
- PLAYER and GOALKEEPER surface atoms require team and actor candidates.
- Administrative atoms may be `IDENTITY_NOT_APPLICABLE`.
- Same provider actor ID across team candidates is review-required.
- Same normalized actor/team key with multiple provider IDs is review-required.
- Same normalized team key with multiple provider IDs is review-required.
- Raw aliases are preserved separately from normalized comparison keys.
- Cross-role records are not fused into physical events.
- Match-local candidate IDs cannot persist across matches as identity truth.

## Donor use

- PR #159 contributes stable match-local candidate IDs, alias preservation and conflict patterns.
- PR #158 contributes evidence lineage patterns.
- HP-Motor and HP-Engine contribute provider-field discovery patterns only.
- Silent defaults, permissive canonical promotion, coordinate truth and global identity are not copied.
- Google Drive and Dropbox remain `REFERENCE_ONLY / DONOR_SUPPORT`.

The method is `ADAPT_NOT_COPY`.

## Outputs

```text
match_local_identity_candidates_lite_v1.json
match_local_identity_candidates_lite_v1.txt
match_local_identity_candidates_analyst_audit_v1.txt
match_local_identity_candidates_runtime_audit_v1.txt
match_local_identity_candidates_active_match_bundle_v1.zip
```

Phone outputs are written only to `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`. Nested HPFA output paths are rejected.

## Claim boundary

```text
identity_scope=MATCH_LOCAL_CANDIDATE_ONLY
identity_truth_admitted=false
global_roster_identity_admitted=false
cross_match_identity_admitted=false
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
base_event_admission_allowed=false
action_bundle_candidate_count=0
event_instance_count=0
metric_value_output_allowed=false
comparison_allowed=false
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

## Status

`SMOKE_CANDIDATE / ACTIVE_MATCH_EVIDENCE_REQUIRED / NOT_PRODUCTION`
