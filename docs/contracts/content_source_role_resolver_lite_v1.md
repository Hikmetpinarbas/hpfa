# HPFA Content Source Role Resolver Lite V1

## Purpose

Resolve supported visible file surfaces to candidate source roles using content evidence rather than filename authority.

```text
raw supported file
→ format reader evidence
→ field / row / sheet / label evidence
→ reviewed provider role semantics
→ cross-format role support
→ source_role_candidate
```

## Candidate outputs

```text
PLAYER_SURFACE_CANDIDATE
TEAM_SURFACE_CANDIDATE
GOALKEEPER_SURFACE_CANDIDATE
UNRESOLVED_SOURCE_ROLE_CANDIDATE
```

Role resolution is candidate-only. It does not validate player, team, match or event identity.

## Admission rules

Filename tokens may be recorded as weak support but can never admit a role by themselves.

### CSV / TSV

Content evidence uses:

- parsed row anatomy;
- direct `team` field presence;
- provider row `code` + exact action suffix structure;
- reviewed provider label/value role restrictions;
- roleless cross-format visible-row fingerprint support.

A surface with no direct team field may be admitted as `TEAM_SURFACE_CANDIDATE` only when row anatomy exposes a non-empty code prefix before an exact action suffix. A direct-team row surface remains `PLAYER|GOALKEEPER` until reviewed content evidence narrows it.

### XML

Content evidence uses parsed `<instance>` row candidates, flattened labels/groups, direct team presence, code/action row anatomy, reviewed provider label/value role restrictions and cross-format support. Root tag or filename alone never admits a role.

### XLSX

Content evidence uses visible sheet names, sheet/header semantics, identity-binding candidates and reviewed role-restricted metric labels. Sheet-name semantics are content evidence; workbook filename is not authority.

### Cross-format support

CSV/XML support propagates candidate role only from a content-admitted CSV surface through a unique best roleless visible-row fingerprint match. This is same-provider reflection support, not an independent vote and not physical-event identity.

If content role evidence conflicts, the result remains `REVIEW_REQUIRED` / `UNRESOLVED_SOURCE_ROLE_CANDIDATE`.

## Resolved inventory

The module writes a derived inventory in which `source_role` is replaced only after `ROLE_CANDIDATE_ADMITTED`. The original inventory role is retained in `inventory_source_role`.

Filename-derived inventory role can never override a content-admitted role.

## Safety boundaries

Always:

```text
canonical_event_count=UNKNOWN
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
independent_source_vote_allowed=false
production_release=false
claim_ceiling=SOURCE_ROLE_CANDIDATE_ONLY
```

A resolved file role is not a canonical event, physical action, team identity or player identity.

## Match-agnostic requirement

Product code must not contain or depend on match names, team names, dates, competition names, sample row counts or sample IDs.

Required regression:

```text
test_no_sample_match_identity_leak
```

Renaming a file must not change an admitted content-based role.

## Outputs

Flat phone outputs only:

```text
content_source_role_resolution_lite_v1.json
content_source_role_resolution_lite_v1.txt
resolved_input_file_inventory_v1.json
content_source_role_resolution_analyst_audit_v1.txt
```

Nested phone output directories remain forbidden.

## Release status

This node can reach `ACTIVE_MATCH_EVIDENCE_PASS` after exact-head runtime validation. It does not imply merge, production binding or release.
