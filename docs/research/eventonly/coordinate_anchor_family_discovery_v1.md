# Coordinate Anchor Family Discovery V1

Status: `DISCOVERY_PASS_PLAN_ONLY / ACTIVE_MATCH_COVERAGE_AUDIT_REQUIRED / NOT_PRODUCTION`

## Amaç

Current coordinate-frame precondition'ı gevşetmeden, unresolved team/period gruplarında ek event-only direction anchor family adaylarının görünür kapsamasını ve bağımsızlığını ölçmek.

Bu discovery node ürün coordinate-frame contract'ını değiştirmez ve progression admission açmaz.

## Current source findings

Current hpfa reviewed SportsBase semantics içinde goalkeeper action-anchor adayları:

- `Shots saved` → `GOALKEEPER_ACTION / SUCCESS / SAVED / SAVE / object=SHOT`
- `Successful cross and pass interception attempts` → `INTERCEPTION / SUCCESS / CROSS_OR_PASS_INTERCEPTION / object=PASS_OR_CROSS`
- `Unsuccessful cross and pass interception attempts` → `INTERCEPTION / FAILURE / CROSS_OR_PASS_INTERCEPTION / object=PASS_OR_CROSS`

`Supersaves` review-limited olduğu için bu discovery admission listesine alınmaz.
`Attacks from corners` context-only olduğu için primary physical coordinate anchor olarak alınmaz.

Drive donor ontology goalkeeper SAVE'i ayrı event family olarak destekler; ancak SportsBase goalkeeper row koordinatının kalecinin fiziksel konumu olduğunu kanıtlamaz. Dropbox progression donor kayıtları ACTIVE_MATCH proof bypass ve claim shortcut kullanımını reddeder. HP-PROJELERI donor fail-closed yaklaşımı destekler fakat sample/match-specific kayıtları product truth değildir.

## Zorunlu ayrımlar

```text
semantic distinctness != evidence independence
visible goalkeeper coordinate != goalkeeper-position truth
empirical goal-side concentration != provider coordinate attachment definition
same underlying shot/pass reflection != independent primary anchor
```

## Discovery matrix

Her family ve team/period için:

```text
visible_anchor_count
coordinate_eligible_anchor_count
normalized_x_median
goal_side_direction_candidate
shot_relation
goal_kick_relation
clearance_relation
exact_object_action_surface_overlap_count
lineage_independence_status
coordinate_attachment_semantics_status
recommended_role
```

## Admission ceiling

Provider-specific coordinate attachment semantics doğrulanmadığı sürece yeni goalkeeper family için:

```text
primary_anchor_admission_allowed=false
recommended_role <= COUNTER_SUPPORT_ONLY
```

Exact object-action surface overlap veya direction conflict varsa `REJECT`.

## Claim boundary

```text
coordinate_frame_contract_change_allowed=false
threshold_relaxation_allowed=false
attack_direction_is_validated_truth=false
coordinate_frame_is_validated_provider_truth=false
progression_truth=false
line_break_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

Refs #236, #222, #226, PR #223, PR #228.
