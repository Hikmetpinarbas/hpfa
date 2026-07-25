# Semantic Role Router and Action Bundle Candidates Lite V1

## Purpose

This node consumes the current Evidence Atom Inventory and Match-Local Identity Candidates outputs. It assigns one downstream semantic route per visible evidence atom and groups only exact same-role action-anchor surfaces into action-bundle candidates.

## Exact grouping boundary

A bundle candidate requires equality across:

- match-surface binding;
- source role;
- match-local team candidate;
- match-local actor candidate where applicable;
- period;
- start and end candidates;
- coordinate candidates;
- exact reviewed action-family candidate.

The module does not use nearest-neighbour matching, temporal tolerance, inferred actor identity, inferred opponent identity, token-based family inference or cross-role fusion.

## Source-role separation

PLAYER, TEAM and GOALKEEPER surfaces remain separate. Exact overlap across roles creates only a cross-role relation candidate stub for the next resolver. It does not create one physical action or one event instance.

## Donor adaptation

Historical classifier and resolver code is used only as a grouping, provenance and fail-closed design donor. Current exact-reviewed semantic roles, atom classes, action-family candidates and match-local identity bindings remain the product authority.

## Claim boundary

```text
action_bundle_candidate != canonical_event
action_bundle_candidate != physical_action_truth
cross_role_relation_candidate != cross_role_equivalence
validated_event_identity=false
base_event_admission_allowed=false
event_instance_count=0
cross_role_fusion_allowed=false
metric_value_output_allowed=false
claim_allowed=false
sequence_truth=false
possession_truth=false
phase_truth=false
tactical_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

## Phone outputs

Only the flat directories below are allowed:

```text
/sdcard/Download/HPFA
/storage/emulated/0/Download/HPFA
```

Nested output directories are rejected.
