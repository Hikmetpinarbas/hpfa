# HPFA Evidence Atom Inventory Lite V1 — Current Row Nucleus Migration

## Purpose

This node adapts the historical Evidence Atom behaviour to the current content-role-bound Row Nucleus producer.

```text
current content-role authority
→ current Row Nucleus
→ Evidence Atom candidate
→ later Match-Local Identity
```

It does not copy the historical #188 schema and does not create event or physical-action truth.

## Current input authority

Only `row_nucleus_inventory_lite_v1` output produced through the current root `row_nucleus_inventory.py` runtime adapter is admitted.

Required boundaries include:

```text
content_source_role_bridge_status=PASS
filename_support_used_for_role_admission=false
filename_role_used_for_nucleus_grouping=false
xlsx_used_for_row_nucleus_identity=false
canonical_event_count=UNKNOWN
physical_action_identity_truth=false
independent_source_vote_allowed=false
production_release=false
```

## Migration rule

Historical Evidence Atom fields are not assumed to exist in Row Nucleus.

Current mapping begins with:

```text
row_nucleus_candidate_id → Evidence Atom identity seed
source_refs → current runtime source-lineage reconstruction
resolved_visible_fields.action → current reviewed provider-label semantic classification
resolved_visible_fields.{start,end,half,pos_x,pos_y,team,code} → candidate-only visible evidence
```

Semantic role and action family are derived from the current reviewed provider semantic registry; they are not read from stale Row Nucleus fields.

## One-to-one candidate rule

```text
1 current Row Nucleus candidate = 1 Evidence Atom candidate
```

This is candidate conservation only. It does not mean one Row Nucleus or one Evidence Atom equals one physical action or canonical event.

## Source independence

CSV/XML members of an admitted same-role serialization lineage remain dependent reflections.

```text
dependent reflection != independent corroboration
independent_support_vote_count=0
independent_source_vote_allowed=false
```

Provider-row IDs preserve textual representation. `001` and `1` are not numerically canonicalized into one identifier.

XLSX is aggregate/reconciliation support and cannot create row or action identity here.

## Administrative / match-boundary handling

Reviewed administrative or match-boundary labels may be routed to `ADMINISTRATIVE_ATOM` while upstream serialization discrepancy remains visible.

```text
downstream_eligibility=ADMIN_ONLY
action_eligible=false
sequence_eligible=false
spatial_eligible=false
metric_event_denominator_eligible=false
identity_not_applicable=true
reflection_discrepancy_preserved=true
```

Role admission does not erase the upstream review state and does not assert equality across serializations.

## Temporal safety

Source row index is provenance only.

```text
source_row_index_is_temporal_order_truth=false
same_time_artificial_order_allowed=false
same_time_link_allowed=false
negative_time_link_allowed=false
cross_period_link_allowed=false
```

No same-timestamp tie is broken with row order, provider ID, source format or action-family priority.

## Atom classes

Candidate classes:

- `ACTION_ANCHOR_ATOM`
- `CONTEXT_INTERVAL_ATOM`
- `PARTICIPATION_INTERVAL_ATOM`
- `DERIVED_CONSEQUENCE_ATOM`
- `TERMINAL_OUTCOME_ATOM`
- `REFERENCE_ATOM`
- `ADMINISTRATIVE_ATOM`
- `REVIEW_REQUIRED_ATOM`

A class is semantic routing evidence only.

## Output

```text
evidence_atom_inventory_lite_v1.json
evidence_atom_inventory_lite_v1.txt
evidence_atom_inventory_analyst_audit_v1.txt
```

The ACTIVE_MATCH bootstrap may package these together with current upstream Row Nucleus evidence into one flat ZIP.

## Claim boundary

Always:

```text
event_instance_allowed=false
cross_role_fusion_allowed=false
physical_action_identity_truth=false
validated_event_identity=false
validated_team_identity=false
validated_player_identity=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
comparison_allowed=false
claim_allowed=false
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
```

## Donor policy

Historical #188 Evidence Atom, #190 Identity, #192 Semantic/Action Bundle and local Termux copies are `DONOR_SUPPORT / MIGRATION_REQUIRED` unless independently revalidated against the current lineage.

Method: `ADAPT_NOT_COPY`.

## Current acceptance order

```text
contract/tests
→ exact-head CI
→ review audit
→ exact-head ACTIVE_MATCH
→ analyst audit
```

CI success is not ACTIVE_MATCH evidence. No merge, release or production binding is implied.
