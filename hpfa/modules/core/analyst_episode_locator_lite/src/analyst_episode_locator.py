from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "analyst_episode_locator_lite_v1"
MVC_MODULE_ID = "minimum_viable_context_lite_v1"
ROW_NUCLEUS_MODULE_ID = "row_nucleus_inventory_lite_v1"
SEMANTIC_MODULE_ID = "context_action_semantics_rebind_lite_v1"
CLAIM_CEILING = "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY"
OUTPUT_JSON = "analyst_episode_locator_lite_v1.json"
OUTPUT_TXT = "analyst_episode_locator_lite_v1.txt"
ANALYST_TXT = "analyst_episode_locator_analyst_audit_v1.txt"
MAX_INTER_LAYER_GAP_SECONDS = 20.0
ACTION_VOLUME_BASIS = "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY"
NAVIGATION_TIME_BASIS = "ALL_VISIBLE_CONTEXT_TIME_LAYERS_NAVIGATION_ONLY"

ADMIN_LABELS = {
    "FIRST_HALF_START": ("start of the 1st half", "start of first half", "first half start"),
    "HALFTIME": ("halftime", "half time", "end of the 1st half", "end of first half"),
    "SECOND_HALF_START": ("start of the 2nd half", "start of second half", "second half start"),
    "FULL_TIME": ("end of the match", "full time", "fulltime", "match end"),
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _norm(value: Any) -> str:
    return _clean(value).casefold()


def _number(value: Any) -> float | None:
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _period_key(value: Any) -> tuple[int, Any]:
    text = _clean(value)
    try:
        return (0, int(float(text)))
    except (TypeError, ValueError):
        return (1, text)


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"episode_input_unreadable:{source.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"episode_input_malformed:{source.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"episode_input_not_object:{source.name}")
    return payload


def _context_second(context: dict[str, Any]) -> float | None:
    if context.get("time_admission_status") != "ADMITTED":
        return None
    value = _number(context.get("time_source_value"))
    if value is not None and context.get("time_unit_status") in {"SECOND", "MIXED_ADMITTED"}:
        return value
    seconds = [
        _number(item.get("raw_value"))
        for item in (context.get("admitted_time_evidence") or [])
        if isinstance(item, dict) and item.get("unit") == "SECOND"
    ]
    unique = sorted({value for value in seconds if value is not None})
    return unique[0] if len(unique) == 1 else None


def _admin_type(semantic_record: dict[str, Any]) -> str | None:
    if semantic_record.get("provider_semantic_role_candidate") not in {"PERIOD_OR_META", "ADMINISTRATIVE_MARKER"}:
        return None
    text = _norm(semantic_record.get("raw_label"))
    for label, candidates in ADMIN_LABELS.items():
        if text in candidates:
            return label
    return None


def _review_reasons(context: dict[str, Any], semantic_record: dict[str, Any]) -> list[str]:
    preserved = context.get("_preserved_unmapped") or {}
    reasons = list(preserved.get("review_reasons") or [])
    reasons.extend(preserved.get("lineage_review_reasons") or [])
    if preserved.get("row_nucleus_status") == "REVIEW_REQUIRED" and not reasons:
        reasons.append("row_nucleus_review_required")
    if semantic_record.get("provider_semantics_review_status") != "REVIEWED_CANDIDATE":
        reasons.append("provider_semantics_review_required")
    return sorted({_clean(reason) for reason in reasons if _clean(reason)})


def _validate_inputs(
    mvc: dict[str, Any],
    row_nucleus: dict[str, Any],
    semantics: dict[str, Any],
) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if mvc.get("module_id") != MVC_MODULE_ID:
        blocks.append("mvc_module_id_mismatch")
    if row_nucleus.get("module_id") != ROW_NUCLEUS_MODULE_ID:
        blocks.append("row_nucleus_module_id_mismatch")
    if semantics.get("module_id") != SEMANTIC_MODULE_ID:
        blocks.append("semantic_rebind_module_id_mismatch")
    for name, payload in (("mvc", mvc), ("row_nucleus", row_nucleus), ("semantics", semantics)):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{name}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
    if mvc.get("time_admission_status") != "ADMITTED":
        blocks.append("mvc_time_not_admitted")
    if mvc.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("mvc_source_row_order_policy_breached")
    if mvc.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("mvc_same_time_policy_breached")
    binding = mvc.get("row_nucleus_context_binding") or {}
    if binding.get("enabled") is not True:
        blocks.append("row_nucleus_context_binding_missing")
    if binding.get("reflection_inflation_prevented") is not True:
        blocks.append("reflection_inflation_not_prevented")
    if mvc.get("context_occurrence_basis") != "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT":
        blocks.append("context_occurrence_basis_not_row_nucleus")
    if semantics.get("context_semantic_assignment_complete") is not True:
        blocks.append("semantic_context_assignment_incomplete")
    if semantics.get("reflection_inflation_prevented") is not True:
        blocks.append("semantic_reflection_inflation_not_prevented")
    if semantics.get("reference_participation_context_adds_action_volume") is not False:
        blocks.append("semantic_non_action_volume_policy_breached")
    if semantics.get("review_limited_semantics_adds_action_volume") is not False:
        blocks.append("semantic_review_limited_volume_policy_breached")
    if semantics.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("semantic_same_time_policy_breached")
    collision = semantics.get("semantic_collision_audit") or {}
    if int(collision.get("team_goal_kick_length_action_occurrence_eligible_count") or 0) != 0:
        blocks.append("team_goal_kick_length_reference_promoted_to_action")
    if int(collision.get("goalkeeper_shot_reference_action_occurrence_eligible_count") or 0) != 0:
        blocks.append("goalkeeper_shot_reference_promoted_to_action")
    if semantics.get("hard_block_hits"):
        blocks.append("semantic_rebind_hard_block_visible")

    contexts = mvc.get("context_candidates")
    nuclei = row_nucleus.get("row_nuclei")
    semantic_records = semantics.get("context_action_semantic_records")
    if not isinstance(contexts, list) or not contexts:
        blocks.append("context_candidates_empty_or_invalid")
        contexts = []
    if not isinstance(nuclei, list) or not nuclei:
        blocks.append("row_nuclei_empty_or_invalid")
        nuclei = []
    if not isinstance(semantic_records, list) or not semantic_records:
        blocks.append("semantic_records_empty_or_invalid")
        semantic_records = []
    if mvc.get("context_candidate_count") != len(contexts):
        blocks.append("context_candidate_count_mismatch")
    if row_nucleus.get("row_nucleus_candidate_count") != len(nuclei):
        blocks.append("row_nucleus_candidate_count_mismatch")
    if semantics.get("context_action_semantic_record_count") != len(semantic_records):
        blocks.append("semantic_record_count_mismatch")
    if len(contexts) != len(nuclei) or len(contexts) != len(semantic_records):
        blocks.append("episode_input_population_mismatch")
    if row_nucleus.get("status") == "FAIL_CLOSED":
        blocks.append("row_nucleus_upstream_fail_closed")
    elif row_nucleus.get("status") == "REVIEW_REQUIRED":
        reviews.append("row_nucleus_upstream_review_required")
    if semantics.get("status") == "FAIL_CLOSED":
        blocks.append("semantic_rebind_upstream_fail_closed")
    elif semantics.get("status") == "REVIEW_REQUIRED":
        reviews.append("semantic_rebind_upstream_review_required")
    return sorted(set(blocks)), sorted(set(reviews))


def _fail_payload(blocks: list[str], reviews: list[str], context_count: int) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "EPISODE_INPUT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "episode_candidates": [],
        "administrative_boundary_candidates": [],
        "episode_candidate_count": 0,
        "context_assignment_count": 0,
        "context_assignment_complete": False,
        "unassigned_context_count": context_count,
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "navigation_time_layer_basis": NAVIGATION_TIME_BASIS,
        "support_rows_add_action_volume": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def build_episode_locator(
    mvc: dict[str, Any],
    row_nucleus: dict[str, Any],
    semantics: dict[str, Any],
    *,
    max_inter_layer_gap_seconds: float = MAX_INTER_LAYER_GAP_SECONDS,
) -> dict[str, Any]:
    blocks, reviews = _validate_inputs(mvc, row_nucleus, semantics)
    contexts = mvc.get("context_candidates") if isinstance(mvc.get("context_candidates"), list) else []
    nuclei = row_nucleus.get("row_nuclei") if isinstance(row_nucleus.get("row_nuclei"), list) else []
    semantic_rows = semantics.get("context_action_semantic_records") if isinstance(semantics.get("context_action_semantic_records"), list) else []

    nucleus_by_id: dict[str, dict[str, Any]] = {}
    for index, nucleus in enumerate(nuclei):
        if not isinstance(nucleus, dict):
            blocks.append(f"row_nucleus_record_invalid:{index}")
            continue
        nucleus_id = _clean(nucleus.get("row_nucleus_candidate_id"))
        if not nucleus_id:
            blocks.append(f"row_nucleus_id_missing:{index}")
            continue
        if nucleus_id in nucleus_by_id:
            blocks.append(f"duplicate_row_nucleus_id:{nucleus_id}")
        nucleus_by_id[nucleus_id] = nucleus

    semantic_by_context: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(semantic_rows):
        if not isinstance(record, dict):
            blocks.append(f"semantic_record_invalid:{index}")
            continue
        context_id = _clean(record.get("context_id"))
        if not context_id:
            blocks.append(f"semantic_context_id_missing:{index}")
            continue
        if context_id in semantic_by_context:
            blocks.append(f"duplicate_semantic_context_id:{context_id}")
        semantic_by_context[context_id] = record

    context_records: list[dict[str, Any]] = []
    seen_context_ids: set[str] = set()
    seen_nucleus_ids: set[str] = set()
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            blocks.append(f"context_record_invalid:{index}")
            continue
        context_id = _clean(context.get("context_id"))
        if not context_id:
            blocks.append(f"context_id_missing:{index}")
            continue
        if context_id in seen_context_ids:
            blocks.append(f"duplicate_context_id:{context_id}")
        seen_context_ids.add(context_id)
        semantic_record = semantic_by_context.get(context_id)
        if not semantic_record:
            blocks.append(f"semantic_context_ref_missing:{context_id}")
            continue
        preserved = context.get("_preserved_unmapped") or {}
        nucleus_id = _clean(preserved.get("row_nucleus_candidate_id"))
        if not nucleus_id or nucleus_id not in nucleus_by_id:
            blocks.append(f"context_row_nucleus_ref_invalid:{context_id}")
            continue
        if _clean(semantic_record.get("row_nucleus_candidate_id")) != nucleus_id:
            blocks.append(f"semantic_row_nucleus_ref_mismatch:{context_id}")
        if nucleus_id in seen_nucleus_ids:
            blocks.append(f"row_nucleus_context_assignment_duplicate:{nucleus_id}")
        seen_nucleus_ids.add(nucleus_id)
        second = _context_second(context)
        if second is None:
            blocks.append(f"context_admitted_second_missing:{context_id}")
            continue
        eligible = semantic_record.get("action_occurrence_eligible") is True
        action_family = _clean(semantic_record.get("provider_action_family_candidate")) if eligible else ""
        context_records.append({
            "context_id": context_id,
            "row_nucleus_candidate_id": nucleus_id,
            "period_candidate": _clean(context.get("period")),
            "second_candidate": second,
            "minute_candidate": round(second / 60.0, 3),
            "action_occurrence_eligible": eligible,
            "eligible_action_family": action_family or "UNKNOWN",
            "semantic_role_candidate": _clean(semantic_record.get("provider_semantic_role_candidate")) or "UNKNOWN_UNREVIEWED",
            "non_action_context_or_reference": semantic_record.get("non_action_context_or_reference") is True,
            "semantic_review_status": _clean(semantic_record.get("provider_semantics_review_status")),
            "team_candidate": _clean(context.get("team_label")),
            "zone_candidate": _clean(context.get("zone_candidate")) or "UNKNOWN_ZONE",
            "channel_candidate": _clean(context.get("channel_candidate")) or "UNKNOWN_CHANNEL",
            "review_reasons": _review_reasons(context, semantic_record),
            "admin_type": _admin_type(semantic_record),
        })

    if set(nucleus_by_id) != seen_nucleus_ids:
        blocks.append("row_nucleus_context_assignment_coverage_mismatch")
    if set(semantic_by_context) != seen_context_ids:
        blocks.append("semantic_context_assignment_coverage_mismatch")
    if blocks:
        return _fail_payload(blocks, reviews, len(contexts))

    grouped: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    for record in context_records:
        grouped[(record["period_candidate"], record["second_candidate"])].append(record)

    time_layers: list[dict[str, Any]] = []
    admin_boundaries: list[dict[str, Any]] = []
    for (period, second), members in grouped.items():
        members = sorted(members, key=lambda row: row["context_id"])
        admin_members = [row for row in members if row.get("admin_type")]
        visible_members = [row for row in members if not row.get("admin_type")]

        if admin_members:
            by_admin: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in admin_members:
                by_admin[str(row["admin_type"])].append(row)
            for admin_type, boundary_members in sorted(by_admin.items()):
                context_ids = [row["context_id"] for row in boundary_members]
                debt = [
                    {"context_id": row["context_id"], "reason": reason}
                    for row in boundary_members
                    for reason in row["review_reasons"]
                ]
                admin_boundaries.append({
                    "administrative_boundary_candidate_id": "aeb_" + _digest(period, second, admin_type, context_ids)[:24],
                    "boundary_type": admin_type,
                    "period_candidate": period,
                    "second_candidate": second,
                    "minute_candidate": round(second / 60.0, 3),
                    "context_refs": context_ids,
                    "row_nucleus_refs": [row["row_nucleus_candidate_id"] for row in boundary_members],
                    "context_count": len(context_ids),
                    "review_debt_refs": debt,
                    "review_debt_count": len(debt),
                    "boundary_is_football_action_truth": False,
                    "boundary_is_phase_truth": False,
                    "same_timestamp_internal_ordering_allowed": False,
                    "claim_ceiling": CLAIM_CEILING,
                })

        if visible_members:
            context_ids = [row["context_id"] for row in visible_members]
            eligible_members = [row for row in visible_members if row["action_occurrence_eligible"]]
            support_members = [row for row in visible_members if not row["action_occurrence_eligible"]]
            action_counts = Counter(row["eligible_action_family"] for row in eligible_members)
            action_zone_counts = Counter(row["zone_candidate"] for row in eligible_members)
            visible_zone_counts = Counter(row["zone_candidate"] for row in visible_members)
            channel_counts = Counter(row["channel_candidate"] for row in eligible_members)
            teams = sorted({
                row["team_candidate"] for row in visible_members
                if row["team_candidate"] not in {"", "unknown", "none", "null"}
            })
            debt = [
                {"context_id": row["context_id"], "reason": reason}
                for row in visible_members
                for reason in row["review_reasons"]
            ]
            time_layers.append({
                "episode_time_layer_candidate_id": "ael_" + _digest(period, second, context_ids)[:24],
                "period_candidate": period,
                "second_candidate": second,
                "minute_candidate": round(second / 60.0, 3),
                "context_refs": context_ids,
                "row_nucleus_refs": [row["row_nucleus_candidate_id"] for row in visible_members],
                "visible_context_count": len(visible_members),
                "action_occurrence_eligible_context_refs": [row["context_id"] for row in eligible_members],
                "action_occurrence_eligible_context_count": len(eligible_members),
                "support_only_context_refs": [row["context_id"] for row in support_members],
                "support_only_context_count": len(support_members),
                "unresolved_semantics_context_count": sum(1 for row in support_members if row["semantic_review_status"] != "REVIEWED_CANDIDATE"),
                "eligible_action_family_counts": dict(sorted(action_counts.items())),
                "eligible_action_zone_candidate_counts": dict(sorted(action_zone_counts.items())),
                "visible_zone_candidate_counts": dict(sorted(visible_zone_counts.items())),
                "eligible_action_channel_candidate_counts": dict(sorted(channel_counts.items())),
                "team_candidates": teams,
                "restart_visible": action_counts.get("RESTART", 0) > 0,
                "terminal_action_visible": action_counts.get("SHOT", 0) > 0,
                "ball_loss_visible": action_counts.get("TURNOVER", 0) > 0,
                "recovery_visible": action_counts.get("RECOVERY", 0) > 0,
                "review_debt_refs": debt,
                "same_time_unordered": len(context_ids) > 1,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "action_volume_basis": ACTION_VOLUME_BASIS,
            })

    time_layers.sort(key=lambda row: (_period_key(row["period_candidate"]), row["second_candidate"], row["episode_time_layer_candidate_id"]))
    admin_boundaries.sort(key=lambda row: (_period_key(row["period_candidate"]), row["second_candidate"], row["boundary_type"]))

    boundaries_by_period_time: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    layers_by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    boundary_times_by_period: dict[str, list[float]] = defaultdict(list)
    for boundary in admin_boundaries:
        boundaries_by_period_time[(boundary["period_candidate"], boundary["second_candidate"])].append(boundary)
        boundary_times_by_period[boundary["period_candidate"]].append(boundary["second_candidate"])
    for layer in time_layers:
        layers_by_period[layer["period_candidate"]].append(layer)

    episodes: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []

    def build_episode(temp: dict[str, Any], end_reason: str) -> dict[str, Any]:
        layers = list(temp["layers"])
        context_refs = [ctx for layer in layers for ctx in layer["context_refs"]]
        eligible_refs = [ctx for layer in layers for ctx in layer["action_occurrence_eligible_context_refs"]]
        support_refs = [ctx for layer in layers for ctx in layer["support_only_context_refs"]]
        action_counts: Counter[str] = Counter()
        action_zone_counts: Counter[str] = Counter()
        visible_zone_counts: Counter[str] = Counter()
        channel_counts: Counter[str] = Counter()
        for layer in layers:
            action_counts.update({k: int(v) for k, v in layer["eligible_action_family_counts"].items()})
            action_zone_counts.update({k: int(v) for k, v in layer["eligible_action_zone_candidate_counts"].items()})
            visible_zone_counts.update({k: int(v) for k, v in layer["visible_zone_candidate_counts"].items()})
            channel_counts.update({k: int(v) for k, v in layer["eligible_action_channel_candidate_counts"].items()})
        teams = sorted({team for layer in layers for team in layer["team_candidates"]})
        review_debt = [debt for layer in layers for debt in (layer.get("review_debt_refs") or [])]
        restart_count = sum(1 for layer in layers if layer.get("restart_visible"))
        terminal_count = sum(1 for layer in layers if layer.get("terminal_action_visible"))
        loss_count = sum(1 for layer in layers if layer.get("ball_loss_visible"))
        recovery_count = sum(1 for layer in layers if layer.get("recovery_visible"))
        unresolved_count = sum(int(layer.get("unresolved_semantics_context_count") or 0) for layer in layers)
        selection_reasons = {f"START:{temp['start_reason']}", f"END:{end_reason}"}
        if restart_count:
            selection_reasons.add("RESTART_ELIGIBLE_ACTION_VISIBLE")
        if terminal_count:
            selection_reasons.add("SHOT_ELIGIBLE_ACTION_VISIBLE")
        if loss_count:
            selection_reasons.add("TURNOVER_ELIGIBLE_ACTION_VISIBLE")
        if recovery_count:
            selection_reasons.add("RECOVERY_ELIGIBLE_ACTION_VISIBLE")
        if len(action_counts) > 1:
            selection_reasons.add("MULTI_ELIGIBLE_ACTION_FAMILY_VISIBLE")
        if not eligible_refs:
            selection_reasons.add("NO_ELIGIBLE_ACTION_SIGNAL")
        if terminal_count and (restart_count or (loss_count and recovery_count)):
            priority = "HIGH_REVIEW_PRIORITY_CANDIDATE"
        elif terminal_count or restart_count or (loss_count and recovery_count):
            priority = "MEDIUM_REVIEW_PRIORITY_CANDIDATE"
        else:
            priority = "NORMAL_REVIEW_PRIORITY_CANDIDATE"
        status = "EPISODE_CANDIDATE_WITH_REVIEW_DEBT" if review_debt else "EPISODE_CANDIDATE_ADMITTED"
        episode_id = "aep_" + _digest(
            temp["period_candidate"],
            layers[0]["second_candidate"],
            layers[-1]["second_candidate"],
            [layer["episode_time_layer_candidate_id"] for layer in layers],
        )[:24]
        return {
            "episode_candidate_id": episode_id,
            "status": status,
            "period_candidate": temp["period_candidate"],
            "start_second_candidate": layers[0]["second_candidate"],
            "end_second_candidate": layers[-1]["second_candidate"],
            "start_minute_candidate": layers[0]["minute_candidate"],
            "end_minute_candidate": layers[-1]["minute_candidate"],
            "duration_candidate_seconds": round(layers[-1]["second_candidate"] - layers[0]["second_candidate"], 6),
            "boundary_start_reason": temp["start_reason"],
            "boundary_end_reason": end_reason,
            "time_layer_refs": [layer["episode_time_layer_candidate_id"] for layer in layers],
            "context_refs": context_refs,
            "row_nucleus_refs": [ref for layer in layers for ref in layer["row_nucleus_refs"]],
            "visible_context_count": len(context_refs),
            "action_occurrence_eligible_context_refs": eligible_refs,
            "action_occurrence_eligible_count": len(eligible_refs),
            "support_only_context_refs": support_refs,
            "support_only_context_count": len(support_refs),
            "unresolved_semantics_context_count": unresolved_count,
            "action_family_distribution": dict(sorted(action_counts.items())),
            "team_scope_candidate": teams[0] if len(teams) == 1 else ("MULTI_TEAM_VISIBLE" if teams else "UNKNOWN_TEAM"),
            "team_candidates": teams,
            "eligible_action_zone_surface": dict(sorted(action_zone_counts.items())),
            "visible_context_zone_surface": dict(sorted(visible_zone_counts.items())),
            "eligible_action_channel_surface": dict(sorted(channel_counts.items())),
            "restart_layer_count": restart_count,
            "terminal_layer_count": terminal_count,
            "ball_loss_layer_count": loss_count,
            "recovery_layer_count": recovery_count,
            "same_time_unordered_refs": [layer["episode_time_layer_candidate_id"] for layer in layers if layer.get("same_time_unordered")],
            "review_debt_refs": review_debt,
            "review_debt_count": len(review_debt),
            "selection_reason": sorted(selection_reasons),
            "analyst_review_priority_candidate": priority,
            "action_volume_basis": ACTION_VOLUME_BASIS,
            "support_rows_add_action_volume": False,
            "episode_is_possession_truth": False,
            "episode_is_sequence_truth": False,
            "episode_is_phase_truth": False,
            "episode_is_rhythm_truth": False,
            "episode_is_tactical_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        }

    all_periods = sorted(set(layers_by_period) | set(boundary_times_by_period), key=_period_key)
    for period in all_periods:
        timeline: list[tuple[float, int, str, Any]] = []
        for second in sorted(set(boundary_times_by_period.get(period, []))):
            timeline.append((second, 0, "BOUNDARY", boundaries_by_period_time[(period, second)]))
        for layer in layers_by_period.get(period, []):
            timeline.append((layer["second_candidate"], 1, "LAYER", layer))
        timeline.sort(key=lambda item: (item[0], item[1]))
        current: dict[str, Any] | None = None
        pending_start_reason = "PERIOD_FIRST_VISIBLE_LAYER"

        def close_current(reason: str) -> None:
            nonlocal current
            if current is not None and current["layers"]:
                episodes.append(build_episode(current, reason))
            current = None

        for second, _rank, kind, payload in timeline:
            if kind == "BOUNDARY":
                close_current("ADMINISTRATIVE_MATCH_BOUNDARY")
                boundary_types = sorted({row["boundary_type"] for row in payload})
                pending_start_reason = "AFTER_ADMIN_BOUNDARY:" + "+".join(boundary_types)
                continue
            layer = payload
            if current is not None:
                previous_second = current["layers"][-1]["second_candidate"]
                gap = second - previous_second
                if gap < 0:
                    blocks.append(f"negative_visible_time_gap:{layer['episode_time_layer_candidate_id']}")
                    close_current("NEGATIVE_TIME_GAP_REVIEW")
                    pending_start_reason = "AFTER_NEGATIVE_TIME_GAP"
                elif gap > max_inter_layer_gap_seconds:
                    close_current("VISIBLE_TIME_GAP_BOUNDARY")
                    pending_start_reason = "AFTER_VISIBLE_TIME_GAP"
            if current is None:
                current = {"period_candidate": period, "start_reason": pending_start_reason, "layers": []}
            current["layers"].append(layer)
            pending_start_reason = "CONTINUATION"
        close_current("PERIOD_LAST_VISIBLE_LAYER")

    assigned_context_ids: set[str] = set()
    for boundary in admin_boundaries:
        for context_id in boundary["context_refs"]:
            if context_id in assigned_context_ids:
                blocks.append(f"context_assignment_duplicate:{context_id}")
            assignments.append({"context_id": context_id, "assignment_type": "ADMINISTRATIVE_BOUNDARY_MEMBER", "target_candidate_id": boundary["administrative_boundary_candidate_id"]})
            assigned_context_ids.add(context_id)
    for episode in episodes:
        for context_id in episode["context_refs"]:
            if context_id in assigned_context_ids:
                blocks.append(f"context_assignment_duplicate:{context_id}")
            assignments.append({"context_id": context_id, "assignment_type": "EPISODE_MEMBER", "target_candidate_id": episode["episode_candidate_id"]})
            assigned_context_ids.add(context_id)

    expected_context_ids = {row["context_id"] for row in context_records}
    unassigned = sorted(expected_context_ids - assigned_context_ids)
    if unassigned:
        blocks.append("context_assignment_coverage_mismatch")

    episode_action_counts: Counter[str] = Counter()
    for episode in episodes:
        episode_action_counts.update({k: int(v) for k, v in episode["action_family_distribution"].items()})
    upstream_action_counts = {str(k): int(v) for k, v in (semantics.get("eligible_action_family_candidate_counts") or {}).items()}
    if dict(sorted(episode_action_counts.items())) != dict(sorted(upstream_action_counts.items())):
        blocks.append("episode_action_family_reconciliation_mismatch")

    episode_eligible_count = sum(int(ep.get("action_occurrence_eligible_count") or 0) for ep in episodes)
    upstream_eligible_count = int(semantics.get("action_occurrence_eligible_count") or 0)
    if episode_eligible_count != upstream_eligible_count:
        blocks.append("episode_action_occurrence_eligible_count_mismatch")

    blocks = sorted(set(blocks))
    admin_review_debt_count = sum(boundary.get("review_debt_count", 0) for boundary in admin_boundaries)
    episode_review_debt_count = sum(episode.get("review_debt_count", 0) for episode in episodes)
    if admin_review_debt_count:
        reviews.append("administrative_boundary_review_debt_visible")
    if episode_review_debt_count:
        reviews.append("episode_review_debt_visible")
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    assignment_complete = not blocks and len(assigned_context_ids) == len(expected_context_ids)
    priority_counts = Counter(episode["analyst_review_priority_candidate"] for episode in episodes)
    episode_status_counts = Counter(episode["status"] for episode in episodes)
    boundary_type_counts = Counter(boundary["boundary_type"] for boundary in admin_boundaries)
    zero_duration_count = sum(episode.get("duration_candidate_seconds") == 0 for episode in episodes)

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "ANALYST_EPISODE_CANDIDATES_ONLY" if not blocks else "EPISODE_INPUT_OR_ASSIGNMENT_REJECTED",
        "claim_ceiling": CLAIM_CEILING,
        "input_context_count": len(context_records),
        "input_row_nucleus_count": len(nucleus_by_id),
        "input_semantic_record_count": len(semantic_by_context),
        "episode_time_layer_candidates": time_layers,
        "episode_time_layer_candidate_count": len(time_layers),
        "eligible_action_time_layer_count": sum(1 for layer in time_layers if layer.get("action_occurrence_eligible_context_count", 0) > 0),
        "support_only_time_layer_count": sum(1 for layer in time_layers if layer.get("action_occurrence_eligible_context_count", 0) == 0),
        "same_time_unordered_layer_count": sum(1 for layer in time_layers if layer.get("same_time_unordered")),
        "administrative_boundary_candidates": admin_boundaries,
        "administrative_boundary_candidate_count": len(admin_boundaries),
        "administrative_boundary_context_count": sum(boundary["context_count"] for boundary in admin_boundaries),
        "administrative_boundary_review_debt_count": admin_review_debt_count,
        "episode_candidates": episodes,
        "episode_candidate_count": len(episodes),
        "zero_duration_episode_candidate_count": zero_duration_count,
        "episode_status_counts": dict(sorted(episode_status_counts.items())),
        "analyst_review_priority_counts": dict(sorted(priority_counts.items())),
        "administrative_boundary_type_counts": dict(sorted(boundary_type_counts.items())),
        "episode_review_debt_count": episode_review_debt_count,
        "episode_action_occurrence_eligible_count": episode_eligible_count,
        "episode_support_only_context_count": sum(int(ep.get("support_only_context_count") or 0) for ep in episodes),
        "episode_unresolved_semantics_context_count": sum(int(ep.get("unresolved_semantics_context_count") or 0) for ep in episodes),
        "episode_eligible_action_family_candidate_counts": dict(sorted(episode_action_counts.items())),
        "semantic_action_occurrence_eligible_count": upstream_eligible_count,
        "semantic_non_action_context_or_reference_count": semantics.get("non_action_context_or_reference_count"),
        "semantic_unresolved_or_review_required_count": semantics.get("provider_semantics_unresolved_or_review_required_count"),
        "semantic_collision_audit": semantics.get("semantic_collision_audit"),
        "context_assignments": assignments,
        "context_assignment_count": len(assignments),
        "context_assignment_complete": assignment_complete,
        "unassigned_context_count": len(unassigned),
        "unassigned_context_refs": unassigned,
        "reflection_inflation_prevented": True,
        "context_occurrence_basis": "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT",
        "action_volume_basis": ACTION_VOLUME_BASIS,
        "navigation_time_layer_basis": NAVIGATION_TIME_BASIS,
        "support_rows_add_action_volume": False,
        "max_inter_layer_gap_seconds": max_inter_layer_gap_seconds,
        "soft_boundary_rules": ["VISIBLE_TIME_GAP_BOUNDARY"],
        "hard_boundary_rule": "ADMINISTRATIVE_MATCH_BOUNDARY",
        "restart_boundary_authority": False,
        "terminal_action_boundary_authority": False,
        "action_family_labels_are_boundary_authority": False,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "episode_is_navigation_truth_only": True,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "possession_truth": False,
        "sequence_truth": False,
        "phase_truth": False,
        "rhythm_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "fatigue_truth": False,
        "production_release": False,
    }


def _summary_text(report: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA ANALYST EPISODE LOCATOR LITE V1",
        "=====================================",
        f"status={report.get('status')}",
        f"input_context_count={report.get('input_context_count')}",
        f"episode_candidate_count={report.get('episode_candidate_count')}",
        f"episode_action_occurrence_eligible_count={report.get('episode_action_occurrence_eligible_count')}",
        f"episode_support_only_context_count={report.get('episode_support_only_context_count')}",
        f"zero_duration_episode_candidate_count={report.get('zero_duration_episode_candidate_count')}",
        f"administrative_boundary_candidate_count={report.get('administrative_boundary_candidate_count')}",
        f"context_assignment_complete={str(report.get('context_assignment_complete')).lower()}",
        f"action_volume_basis={report.get('action_volume_basis')}",
        f"review_hits={report.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "rhythm_truth=false",
        "production_release=false",
        "",
    ])


def _analyst_text(report: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — EPISODE LOCATOR",
        f"Episode candidates: {report.get('episode_candidate_count', 0)}",
        f"Eligible action evidence assigned to episodes: {report.get('episode_action_occurrence_eligible_count', 0)}",
        f"Support/context rows retained without adding action volume: {report.get('episode_support_only_context_count', 0)}",
        f"Administrative boundary candidates: {report.get('administrative_boundary_candidate_count', 0)}",
        "",
        "Review-priority episode sample:",
    ]
    for episode in (report.get("episode_candidates") or [])[:20]:
        lines.append(
            "- "
            f"{episode.get('start_minute_candidate')}–{episode.get('end_minute_candidate')} min | "
            f"eligible_actions={episode.get('action_occurrence_eligible_count')} | "
            f"support={episode.get('support_only_context_count')} | "
            f"{episode.get('analyst_review_priority_candidate')} | "
            f"{','.join(episode.get('selection_reason') or [])}"
        )
    lines.extend([
        "",
        "Safe meaning: episode boundaries are analyst navigation candidates.",
        "Only reviewed action-occurrence-eligible evidence contributes to action-family volume and review priority.",
        "Context/reference/participation rows remain visible support but add no action volume.",
        "No possession, sequence, phase, rhythm, dominance or tactical truth is produced.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    max_inter_layer_gap_seconds: float = MAX_INTER_LAYER_GAP_SECONDS,
) -> dict[str, Any]:
    source = Path(input_dir).expanduser().resolve(strict=False)
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    mvc = _load_json(source / "minimum_viable_context_lite_v1.json")
    row_nucleus = _load_json(source / "row_nucleus_inventory_lite_v1.json")
    semantics = _load_json(source / "context_action_semantics_rebind_lite_v1.json")
    report = build_episode_locator(mvc, row_nucleus, semantics, max_inter_layer_gap_seconds=max_inter_layer_gap_seconds)
    report["outputs"] = {
        "json": str(output / OUTPUT_JSON),
        "summary": str(output / OUTPUT_TXT),
        "analyst": str(output / ANALYST_TXT),
    }
    (output / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / OUTPUT_TXT).write_text(_summary_text(report), encoding="utf-8")
    (output / ANALYST_TXT).write_text(_analyst_text(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA Analyst Episode Locator Lite V1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-inter-layer-gap-seconds", type=float, default=MAX_INTER_LAYER_GAP_SECONDS)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir, max_inter_layer_gap_seconds=args.max_inter_layer_gap_seconds)
    print(json.dumps({
        "status": report.get("status"),
        "decision": report.get("decision"),
        "episode_candidate_count": report.get("episode_candidate_count"),
        "episode_action_occurrence_eligible_count": report.get("episode_action_occurrence_eligible_count"),
        "episode_support_only_context_count": report.get("episode_support_only_context_count"),
        "administrative_boundary_candidate_count": report.get("administrative_boundary_candidate_count"),
        "context_assignment_complete": report.get("context_assignment_complete"),
        "action_volume_basis": report.get("action_volume_basis"),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "outputs": report.get("outputs"),
    }, ensure_ascii=False, sort_keys=True))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
