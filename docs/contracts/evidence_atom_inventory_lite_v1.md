# Evidence Atom Inventory Lite V1

## Purpose

This node converts each cleared row nucleus into exactly one source-bound evidence atom candidate.

```text
row nucleus != canonical event
row nucleus != physical action truth
evidence atom != canonical event
evidence atom != validated identity
```

## Input

Only `row_nucleus_inventory_lite_v1.json` is accepted.

The input must preserve:

- row-nucleus count integrity;
- unique nucleus IDs;
- CSV/XML source paths;
- source and runtime SHA-256 lineage;
- same-role cross-format support;
- provider-row ID as candidate only;
- semantic-role and mapping status candidates;
- `canonical_event_count=UNKNOWN`;
- `production_release=false`.

## One-to-one rule

```text
1 row nucleus candidate = 1 evidence atom candidate
```

CSV and XML are already same-role reflections inside the row nucleus. They do not create separate atoms.

XLSX aggregate-label support is retained only as metadata overlay. It does not create an occurrence or evidence atom.

## Atom classes

```text
ACTION_ANCHOR_ATOM
CONTEXT_INTERVAL_ATOM
PARTICIPATION_INTERVAL_ATOM
DERIVED_CONSEQUENCE_ATOM
TERMINAL_OUTCOME_ATOM
REFERENCE_ATOM
ADMINISTRATIVE_ATOM
REVIEW_REQUIRED_ATOM
```

An action anchor requires exactly one action-family candidate. Exact-reviewed context, participation, derived, terminal, reference and administrative roles are allowed without inventing an action family.

Unknown, fallback, conflict, unregistered-role and role/eligibility mismatches remain review-required.

## Match-surface binding

`match_surface_binding_id` is derived deterministically from the six runtime-bound CSV/XML SHA records for the PLAYER, TEAM and GOALKEEPER surfaces.

It is a match-local source binding only. It is not match identity, roster identity, team identity or event identity.

## Outputs

```text
evidence_atom_inventory_lite_v1.json
evidence_atom_inventory_lite_v1.txt
evidence_atom_inventory_analyst_audit_v1.txt
evidence_atom_inventory_runtime_audit_v1.txt
evidence_atom_inventory_active_match_bundle_v1.zip
```

Phone outputs are written only to `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`. Nested HPFA output paths are rejected.

## Donor use

- PR #158 contributes stable atom-ID, raw/normalized-label and provenance patterns.
- PR #159 contributes match-local binding and conflict patterns for the next identity node.
- HP-Motor and HP-Engine contribute lineage and state-management patterns.
- Google Drive and Dropbox contribute event-only admission, source-role separation and claim-ceiling rules.

All donor content is adapted, not copied, and cannot override ACTIVE_MATCH evidence.

## Claim boundary

```text
evidence_atom_is_canonical_event=false
validated_event_identity=false
validated_team_identity=false
validated_player_identity=false
identity_binding_allowed=false
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
