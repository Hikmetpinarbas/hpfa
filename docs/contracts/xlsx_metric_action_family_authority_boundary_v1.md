# XLSX Metric → Action-Family Authority Boundary V1

## Purpose

Preserve XLSX aggregate metric context without manufacturing an event/action semantic relation from metric names.

## Current authority

The XLSX row projection may expose an observed aggregate cell and its provenance. It does not currently possess an admitted semantic authority that maps a metric label such as `Shots` or `Progressive passes` onto an ACTIVE_MATCH `action_family_candidate`.

Therefore every projected metric must remain:

- `action_family_relation_state=UNRESOLVED_NO_ADMITTED_SEMANTIC_AUTHORITY`
- `action_family_candidates=[]`
- `action_family_relation_basis=[]`
- `action_family_relation_is_inferred_from_metric_label=false`
- `action_family_relation_is_validated=false`
- `metric_is_action_trace_support=false`
- `metric_is_physical_action_truth=false`

Normalized metric keys are schema/navigation aids only. A key that happens to equal an existing action-family token (for example `SHOT` or `PASS`) does not create semantic identity.

## Invariants

1. Raw or normalized metric-label similarity cannot attach an XLSX aggregate cell to an individual trace candidate.
2. XLSX aggregate values remain entity-level/context surfaces unless a later explicit semantic-admission contract exists.
3. Aggregate metric presence does not add an evidence vote or an event/action count unit.
4. `canonical_event_count=UNKNOWN`.
5. `true_action_count=UNKNOWN`.
6. `production_release=false`.
7. CI SUCCESS is engineering evidence only and is not physical ACTIVE_MATCH PASS.

## Future admission prerequisite

A future relation may only be added by rehabilitating the current producer after an explicit, tested semantic mapping authority exists. Filename identity, raw labels, normalized labels, actor-name agreement, or metric-value coincidence are insufficient by themselves.
