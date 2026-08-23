# HPFA Match-Local Identity Candidates Lite V1 — Current Evidence Atom Migration

## Purpose

This node adapts the useful historical #190 identity behaviour onto the current Evidence Atom contract.

```text
current Row Nucleus
→ current Evidence Atom
→ match-local team / actor identity candidates
→ later semantic route / action bundle
```

It does not establish global roster identity, event identity or physical action truth.

## Current input authority

Only current `evidence_atom_inventory_lite_v1` output is admitted.

Required safety boundaries include:

```text
canonical_event_count=UNKNOWN
event_instance_allowed=false
cross_role_fusion_allowed=false
independent_source_vote_allowed=false
physical_action_identity_truth=false
production_release=false
```

Current structured `source_lineage_records` are authority for provenance validation. Historical positional assumptions such as exactly two ordered path/SHA list entries are not used as identity authority.

## Match-local binding

Candidate parsing is conservative:

- TEAM surface: team candidate only;
- PLAYER surface: team + actor candidate when exact visible subject evidence supports it;
- GOALKEEPER surface: team + actor candidate when exact visible subject evidence supports it;
- ADMINISTRATIVE_ATOM / `identity_not_applicable=true`: `IDENTITY_NOT_APPLICABLE`.

Actor extraction requires exact visible suffix agreement:

```text
code_raw = <subject> - <raw_label>
```

If the suffix does not match, no actor is guessed.

Team/player provider IDs remain candidates. Conflicting provider IDs, cross-team actor provider-ID reuse and ambiguous jersey aliases remain review-required.

## Review separation

Semantic uncertainty and identity uncertainty are different dimensions.

An Evidence Atom can remain semantic `REVIEW_REQUIRED` while its visible team/actor subject is safely bound as a match-local identity candidate. The identity binding preserves `atom_status` and `upstream_review_hits`; it does not erase or resolve semantic review.

Administrative atoms can be `IDENTITY_NOT_APPLICABLE` even when their upstream serialization discrepancy remains review-required.

## Conservation

```text
1 Evidence Atom = 1 identity binding record
```

This is traceability conservation only. It is not an event count or action count.

## Source safety

- XLSX cannot create match-local row/action identity here.
- CSV/XML dependent reflections do not add corroboration votes.
- source row index is provenance only, not football temporal order.
- no cross-role fusion occurs in this node.

## Outputs

```text
match_local_identity_candidates_lite_v1.json
match_local_identity_candidates_lite_v1.txt
match_local_identity_candidates_analyst_audit_v1.txt
```

## Claim boundary

Always:

```text
identity_truth_admitted=false
global_roster_identity_admitted=false
cross_match_identity_admitted=false
validated_team_identity=false
validated_player_identity=false
validated_event_identity=false
physical_action_identity_truth=false
event_instance_allowed=false
cross_role_fusion_allowed=false
independent_source_vote_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Donor decision

Historical #190 provides valuable parsing/conflict semantics but its rigid historical Evidence Atom lineage validation is not copied. Dropbox semantic/action-bundle code is downstream DONOR_SUPPORT only. Google Drive records are planning/operator evidence only.

Method: `ADAPT_NOT_COPY`.

## Acceptance order

```text
current-source audit
→ contract/tests
→ exact-head CI
→ review audit
→ exact-head ACTIVE_MATCH
→ analyst audit
```

CI success is not ACTIVE_MATCH evidence. No merge, release or production binding is implied.
