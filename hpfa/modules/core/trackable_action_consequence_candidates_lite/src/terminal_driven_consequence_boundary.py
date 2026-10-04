from __future__ import annotations

from typing import Any

ANCHOR_TERMINAL = "ANCHOR_TERMINAL_SUPPORT_VISIBLE"
ENSUING_TERMINAL = "ENSUING_TERMINAL_SUPPORT_LAYER_VISIBLE"
NO_TERMINAL = "NO_ADMITTED_TERMINAL_BOUNDARY_VISIBLE"
UNRESOLVED = "UNRESOLVED_TERMINAL_LINEAGE"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean(item) for item in value if _clean(item)]


def _layer_list(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    layers: list[list[str]] = []
    for layer in value:
        if not isinstance(layer, list):
            return []
        layers.append([_clean(item) for item in layer if _clean(item)])
    return layers


def apply_terminal_driven_consequence_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    """Stop consequence continuation at the first admitted terminal-support layer.

    This does not invent terminal type, possession truth, tactical truth or causality. A
    terminal-support anchor closes its own continuation search. Otherwise only an
    AFTER_CONFIRMED follow-up whose own consequence record carries visible terminal support
    may create a boundary. If multiple traces share that first terminal time layer, the whole
    layer is retained because same-time internal order is not admitted.
    """
    result = dict(payload)
    if result.get("status") == "FAIL_CLOSED":
        return result

    records = result.get("trackable_action_consequence_candidates")
    if not isinstance(records, list):
        records = []

    anchor_counts: dict[str, int] = {}
    terminal_anchor_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        anchor_id = _clean(record.get("anchor_trackable_action_trace_candidate_id"))
        if anchor_id:
            anchor_counts[anchor_id] = anchor_counts.get(anchor_id, 0) + 1
            if record.get("terminal_outcome_support_visible") is True:
                terminal_anchor_ids.add(anchor_id)

    duplicate_anchor_ids = {key for key, count in anchor_counts.items() if count > 1}
    adapted: list[dict[str, Any]] = []
    bounded_count = 0
    anchor_terminal_count = 0
    ensuing_terminal_count = 0
    unresolved_count = 0
    excluded_visible_count = 0
    excluded_admitted_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue
        row = dict(record)
        anchor_id = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        raw_layers = _layer_list(row.get("follow_up_trace_ids_by_layer"))
        raw_visible = _text_list(row.get("visible_follow_up_trace_ids"))
        raw_admitted = _text_list(row.get("admitted_after_follow_up_trace_ids"))
        raw_relations = row.get("temporal_relation_states_by_trace_id")
        relation_map = dict(raw_relations) if isinstance(raw_relations, dict) else {}

        row["pre_terminal_search_follow_up_trace_ids_by_layer"] = [list(layer) for layer in raw_layers]
        row["pre_terminal_search_visible_follow_up_trace_ids"] = list(raw_visible)
        row["pre_terminal_search_admitted_after_follow_up_trace_ids"] = list(raw_admitted)
        row["pre_terminal_search_temporal_relation_states_by_trace_id"] = dict(relation_map)
        row["terminal_search_boundary_source"] = "TERMINAL_OUTCOME_SUPPORT_VISIBLE_ONLY"
        row["terminal_search_boundary_same_time_layer_inclusive"] = True
        row["terminal_search_boundary_orders_same_time_action"] = False
        row["terminal_search_boundary_is_terminal_type_truth"] = False
        row["terminal_search_boundary_is_possession_truth"] = False
        row["terminal_search_boundary_is_causal_truth"] = False
        row["terminal_search_boundary_is_tactical_truth"] = False
        row["terminal_search_boundary_can_authorize_claim"] = False
        row["legacy_window_counts_are_pre_terminal_diagnostic_provenance"] = True

        if not anchor_id or anchor_id in duplicate_anchor_ids:
            unresolved_count += 1
            row["terminal_search_boundary_state"] = UNRESOLVED
            row["terminal_search_boundary_trace_ids"] = []
            row["terminal_search_boundary_layer_index"] = None
            row["terminal_boundary_excluded_visible_follow_up_trace_ids"] = []
            row["terminal_boundary_excluded_admitted_after_trace_ids"] = []
            adapted.append(row)
            continue

        if row.get("terminal_outcome_support_visible") is True:
            allowed_ids: set[str] = set()
            row["follow_up_trace_ids_by_layer"] = []
            row["follow_up_layer_count"] = 0
            row["visible_follow_up_trace_ids"] = []
            row["admitted_after_follow_up_trace_ids"] = []
            row["temporal_relation_states_by_trace_id"] = {}
            row["terminal_search_boundary_state"] = ANCHOR_TERMINAL
            row["terminal_search_boundary_trace_ids"] = [anchor_id]
            row["terminal_search_boundary_layer_index"] = -1
            row["terminal_boundary_excluded_visible_follow_up_trace_ids"] = list(raw_visible)
            row["terminal_boundary_excluded_admitted_after_trace_ids"] = list(raw_admitted)
            bounded_count += 1
            anchor_terminal_count += 1
            excluded_visible_count += len(raw_visible)
            excluded_admitted_count += len(raw_admitted)
            adapted.append(row)
            continue

        if (raw_visible or raw_admitted) and not raw_layers:
            unresolved_count += 1
            row["terminal_search_boundary_state"] = UNRESOLVED
            row["terminal_search_boundary_trace_ids"] = []
            row["terminal_search_boundary_layer_index"] = None
            row["terminal_boundary_excluded_visible_follow_up_trace_ids"] = []
            row["terminal_boundary_excluded_admitted_after_trace_ids"] = []
            adapted.append(row)
            continue

        admitted_set = set(raw_admitted)
        boundary_index: int | None = None
        boundary_trace_ids: list[str] = []
        for index, layer in enumerate(raw_layers):
            terminal_ids = sorted(
                trace_id
                for trace_id in layer
                if trace_id in admitted_set and trace_id in terminal_anchor_ids
            )
            if terminal_ids:
                boundary_index = index
                boundary_trace_ids = terminal_ids
                break

        if boundary_index is None:
            row["terminal_search_boundary_state"] = NO_TERMINAL
            row["terminal_search_boundary_trace_ids"] = []
            row["terminal_search_boundary_layer_index"] = None
            row["terminal_boundary_excluded_visible_follow_up_trace_ids"] = []
            row["terminal_boundary_excluded_admitted_after_trace_ids"] = []
            adapted.append(row)
            continue

        active_layers = raw_layers[: boundary_index + 1]
        allowed_ids = {trace_id for layer in active_layers for trace_id in layer}
        active_visible = [trace_id for trace_id in raw_visible if trace_id in allowed_ids]
        active_admitted = [trace_id for trace_id in raw_admitted if trace_id in allowed_ids]
        excluded_visible = [trace_id for trace_id in raw_visible if trace_id not in allowed_ids]
        excluded_admitted = [trace_id for trace_id in raw_admitted if trace_id not in allowed_ids]

        row["follow_up_trace_ids_by_layer"] = [list(layer) for layer in active_layers]
        row["follow_up_layer_count"] = len(active_layers)
        row["visible_follow_up_trace_ids"] = active_visible
        row["admitted_after_follow_up_trace_ids"] = active_admitted
        row["temporal_relation_states_by_trace_id"] = {
            trace_id: state
            for trace_id, state in relation_map.items()
            if trace_id in allowed_ids
        }
        row["terminal_search_boundary_state"] = ENSUING_TERMINAL
        row["terminal_search_boundary_trace_ids"] = boundary_trace_ids
        row["terminal_search_boundary_layer_index"] = boundary_index
        row["terminal_boundary_excluded_visible_follow_up_trace_ids"] = excluded_visible
        row["terminal_boundary_excluded_admitted_after_trace_ids"] = excluded_admitted
        bounded_count += 1
        ensuing_terminal_count += 1
        excluded_visible_count += len(excluded_visible)
        excluded_admitted_count += len(excluded_admitted)
        adapted.append(row)

    review_hits = {
        _clean(item)
        for item in (result.get("review_hits") or [])
        if _clean(item)
    }
    if unresolved_count:
        review_hits.add("terminal_driven_consequence_boundary_unresolved")

    result["trackable_action_consequence_candidates"] = adapted
    result["terminal_driven_consequence_search_enabled"] = True
    result["terminal_driven_consequence_boundary_count"] = bounded_count
    result["anchor_terminal_boundary_count"] = anchor_terminal_count
    result["ensuing_terminal_boundary_count"] = ensuing_terminal_count
    result["terminal_boundary_unresolved_count"] = unresolved_count
    result["terminal_boundary_excluded_visible_follow_up_trace_count"] = excluded_visible_count
    result["terminal_boundary_excluded_admitted_after_trace_count"] = excluded_admitted_count
    result["terminal_search_boundary_source"] = "TERMINAL_OUTCOME_SUPPORT_VISIBLE_ONLY"
    result["terminal_search_boundary_orders_same_time_action"] = False
    result["terminal_search_boundary_is_terminal_type_truth"] = False
    result["terminal_search_boundary_is_possession_truth"] = False
    result["terminal_search_boundary_is_causal_truth"] = False
    result["terminal_search_boundary_is_tactical_truth"] = False
    result["terminal_search_boundary_can_authorize_claim"] = False
    result["legacy_window_counts_are_pre_terminal_diagnostic_provenance"] = True
    result["review_hits"] = sorted(review_hits)
    hard_blocks = result.get("hard_block_hits") or []
    result["status"] = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else result.get("status", "PASS"))
    result["module_status"] = result["status"]
    result["canonical_event_count"] = "UNKNOWN"
    result["true_action_count"] = "UNKNOWN"
    result["production_release"] = False
    return result
