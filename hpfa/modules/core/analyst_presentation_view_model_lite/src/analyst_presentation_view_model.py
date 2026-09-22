from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "analyst_presentation_view_model_lite_v1"
OUTPUT_JSON = "analyst_presentation_view_model_lite_v1.json"
SCHEMA_VERSION = "1.0"

SURFACE_KEYS = [
    "analyst_report",
    "match_story",
    "six_phase_match_view",
    "mechanism_cards",
    "player_process_cards",
    "counterevidence_cards",
    "observed_replay",
    "traceback_evidence_drawer",
    "broadcast_summary",
    "unknown_unobservable_register",
]

def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _number_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _artifact(root: Path, name: str, *, current: bool = True) -> dict[str, Any]:
    path = root / name
    if not path.is_file():
        return {"name": name, "state": "MISSING"}
    if not current:
        return {"name": name, "state": "STALE_NOT_CURRENT_INVOCATION"}
    return {
        "name": name,
        "state": "AVAILABLE",
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }

def _surface(state: str, source_artifacts: list[str], note: str, claim_ceiling: str) -> dict[str, Any]:
    return {
        "state": state,
        "source_artifacts": source_artifacts,
        "note": note,
        "claim_ceiling": claim_ceiling,
    }

def _episode_cards(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for item in payload.get("episode_candidates") or []:
        if not isinstance(item, dict):
            continue
        cards.append({
            "id": item.get("episode_candidate_id"),
            "start_second_candidate": item.get("start_second_candidate"),
            "end_second_candidate": item.get("end_second_candidate"),
            "period_candidate": item.get("period_candidate"),
            "team_scope_candidate": item.get("team_scope_candidate"),
            "action_family_distribution": item.get("action_family_distribution") or {},
            "zone_surface": item.get("eligible_action_zone_surface") or {},
            "channel_surface": item.get("eligible_action_channel_surface") or {},
            "boundary_start_reason": item.get("boundary_start_reason"),
            "boundary_end_reason": item.get("boundary_end_reason"),
            "status": item.get("status"),
            "review_debt_count": item.get("review_debt_count"),
            "same_timestamp_internal_ordering_allowed": False,
            "claim_ceiling": item.get("claim_ceiling"),
        })
    return cards

def _phase_cards(full: dict[str, Any]) -> list[dict[str, Any]]:
    rich = full.get("rich_multiformat_analysis_lattice")
    if not isinstance(rich, dict):
        return []
    return [item for item in (rich.get("phase_state_candidates") or []) if isinstance(item, dict)]

def _counterevidence_cards(full: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for chain in full.get("intelligence_chains") or []:
        if not isinstance(chain, dict):
            continue
        argument = chain.get("argument")
        fusion = chain.get("fusion")
        safe = chain.get("safe_sentence")
        argument = argument if isinstance(argument, dict) else {}
        fusion = fusion if isinstance(fusion, dict) else {}
        safe = safe if isinstance(safe, dict) else {}
        counter = list(argument.get("counter_scenarios") or [])
        withdrawal = list(argument.get("withdrawal_conditions") or [])
        contradicting = list(fusion.get("contradicting_refs") or [])
        if not (counter or withdrawal or contradicting):
            continue
        cards.append({
            "argument_id": argument.get("argument_id"),
            "argument_family": argument.get("argument_family"),
            "status": argument.get("status"),
            "safe_sentence_candidate_tr": safe.get("safe_sentence_candidate_tr"),
            "counter_scenarios": counter,
            "withdrawal_conditions": withdrawal,
            "contradicting_refs": contradicting,
            "independence_state": fusion.get("independence_state"),
            "claim_ceiling": argument.get("claim_ceiling"),
        })
    return cards

def _mechanism_key(argument: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(argument.get("argument_family") or "UNKNOWN_ARGUMENT_FAMILY"),
        str(argument.get("relation_scope") or "UNKNOWN_RELATION_SCOPE"),
        str(argument.get("analysis_route") or "UNKNOWN_ANALYSIS_ROUTE"),
    )

def _mechanism_display_tr(family: str) -> str:
    labels = {
        "progression_without_terminal_value": "İlerleme ile terminal değer arasındaki görünür kopukluk adayı",
    }
    return labels.get(family, family.replace("_", " "))

def _mechanism_where_when(
    root: Path,
    full: dict[str, Any],
    declared: set[str],
) -> dict[str, Any]:
    sequence_name = "visible_action_sequence_candidates_lite_v1.json"
    trace_name = "trackable_action_trace_candidates_lite_v1.json"
    if not {sequence_name, trace_name}.issubset(declared):
        return {}

    sequence_payload = _load(root / sequence_name)
    trace_payload = _load(root / trace_name)

    sequences = {
        str(item.get("visible_action_sequence_candidate_id")): item
        for item in (sequence_payload.get("visible_action_sequence_candidates") or [])
        if isinstance(item, dict) and item.get("visible_action_sequence_candidate_id")
    }
    traces = {
        str(item.get("trackable_action_trace_candidate_id")): item
        for item in (trace_payload.get("trackable_action_trace_candidates") or [])
        if isinstance(item, dict) and item.get("trackable_action_trace_candidate_id")
    }

    out: dict[str, Any] = {}
    for chain in full.get("intelligence_chains") or []:
        if not isinstance(chain, dict):
            continue
        argument = chain.get("argument") or {}
        packet = chain.get("packet") or {}
        if not isinstance(argument, dict) or not isinstance(packet, dict):
            continue
        family, relation_scope, analysis_route = _mechanism_key(argument)
        mechanism_id = f"mechanism:{family}:{relation_scope}:{analysis_route}"
        entry = out.setdefault(mechanism_id, {
            "time_anchors": [],
            "spatial_anchors": [],
            "source_sequence_candidate_ids": [],
            "source_window_refs": [],
            "same_timestamp_internal_ordering_allowed": False,
            "path_or_trajectory_truth": False,
            "claim_ceiling": "MECHANISM_WHERE_WHEN_REFERENCE_BINDING_ONLY",
        })

        seen_windows = {x["window_ref"] for x in entry["time_anchors"]}
        for window in packet.get("input_window_records") or []:
            if not isinstance(window, dict):
                continue
            ref = str(window.get("ref_id") or window.get("window_id") or "")
            if not ref or ref in seen_windows:
                continue
            entry["time_anchors"].append({
                "window_ref": ref,
                "period_candidate": window.get("period_candidate"),
                "start_second_candidate": _number_or_none(window.get("start_candidate")),
                "layer_state": window.get("layer_state"),
            })
            entry["source_window_refs"].append(ref)
            seen_windows.add(ref)

        seen_sequences = set(entry["source_sequence_candidate_ids"])
        seen_spatial = {
            (x.get("trace_candidate_id"), x.get("pos_x_candidate"), x.get("pos_y_candidate"))
            for x in entry["spatial_anchors"]
        }
        for seq_record in packet.get("input_sequence_records") or []:
            if not isinstance(seq_record, dict):
                continue
            seq_id = str(seq_record.get("sequence_id") or seq_record.get("ref_id") or "")
            if not seq_id:
                continue
            if seq_id not in seen_sequences:
                entry["source_sequence_candidate_ids"].append(seq_id)
                seen_sequences.add(seq_id)
            seq = sequences.get(seq_id) or {}
            for trace_id in seq.get("trackable_action_trace_candidate_ids") or []:
                trace = traces.get(str(trace_id)) or {}
                x = _number_or_none(trace.get("pos_x_candidate"))
                y = _number_or_none(trace.get("pos_y_candidate"))
                if x is None or y is None:
                    continue
                key = (str(trace_id), x, y)
                if key in seen_spatial:
                    continue
                entry["spatial_anchors"].append({
                    "trace_candidate_id": str(trace_id),
                    "period_candidate": trace.get("period_candidate"),
                    "start_second_candidate": _number_or_none(trace.get("start_candidate")),
                    "pos_x_candidate": x,
                    "pos_y_candidate": y,
                    "team_identity_candidate_id": trace.get("team_identity_candidate_id"),
                    "actor_identity_candidate_id": trace.get("actor_identity_candidate_id"),
                    "action_family_candidates": trace.get("action_family_candidates") or [],
                    "coordinate_evidence_status": trace.get("coordinate_evidence_status"),
                })
                seen_spatial.add(key)

    for entry in out.values():
        entry["time_anchors"].sort(key=lambda x: (
            str(x.get("period_candidate")),
            float(x.get("start_second_candidate") or 0.0),
            str(x.get("window_ref")),
        ))
        entry["spatial_anchors"].sort(key=lambda x: (
            str(x.get("period_candidate")),
            float(x.get("start_second_candidate") or 0.0),
            str(x.get("trace_candidate_id")),
        ))
        full_time = entry["time_anchors"]
        full_spatial = entry["spatial_anchors"]
        entry["time_anchor_count"] = len(full_time)
        entry["spatial_anchor_count"] = len(full_spatial)
        period_time_counts: dict[str, int] = {}
        period_spatial_counts: dict[str, int] = {}
        team_spatial_counts: dict[str, int] = {}
        for anchor in full_time:
            period = str(anchor.get("period_candidate") or "UNKNOWN_PERIOD")
            period_time_counts[period] = period_time_counts.get(period, 0) + 1
        for anchor in full_spatial:
            period = str(anchor.get("period_candidate") or "UNKNOWN_PERIOD")
            period_spatial_counts[period] = period_spatial_counts.get(period, 0) + 1
            team_id = str(anchor.get("team_identity_candidate_id") or "UNKNOWN_TEAM")
            team_spatial_counts[team_id] = team_spatial_counts.get(team_id, 0) + 1
        entry["period_time_anchor_counts"] = dict(sorted(period_time_counts.items()))
        entry["period_spatial_anchor_counts"] = dict(sorted(period_spatial_counts.items()))
        entry["team_spatial_anchor_counts"] = dict(sorted(team_spatial_counts.items()))
        entry["period_candidates"] = sorted({
            str(x.get("period_candidate"))
            for x in [*full_time, *full_spatial]
            if x.get("period_candidate") not in [None, ""]
        })
        status_counts: dict[str, int] = {}
        for anchor in full_spatial:
            status = str(anchor.get("coordinate_evidence_status") or "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        entry["coordinate_evidence_status_counts"] = dict(sorted(status_counts.items()))
        entry["time_anchor_sample"] = full_time[:12]
        entry["spatial_anchor_sample"] = full_spatial[:12]
        entry["delivery_mode"] = "LAZY_REFERENCE_JOIN"
        entry["lazy_graph_sources"] = {
            "when": {
                "source_artifact": "active_match_full_spine_v1.json",
                "join_path": "intelligence_chains[*].packet.input_window_records",
                "mechanism_join_key": "argument_family+relation_scope+analysis_route",
            },
            "where": {
                "sequence_artifact": "visible_action_sequence_candidates_lite_v1.json",
                "trace_artifact": "trackable_action_trace_candidates_lite_v1.json",
                "join_path": "packet.input_sequence_records.sequence_id -> visible_action_sequence_candidate_id -> trackable_action_trace_candidate_ids",
                "coordinate_fields": ["pos_x_candidate", "pos_y_candidate"],
            },
        }
        entry["coverage_is_independent_recurrence"] = False
        del entry["time_anchors"]
        del entry["spatial_anchors"]
    return out

def _mechanism_cards(full: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for chain in full.get("intelligence_chains") or []:
        if not isinstance(chain, dict):
            continue
        argument = chain.get("argument")
        argument = argument if isinstance(argument, dict) else {}
        if not argument or argument.get("hard_block_hits"):
            continue
        groups.setdefault(_mechanism_key(argument), []).append(chain)

    cards: list[dict[str, Any]] = []
    for (family, relation_scope, analysis_route), chains in groups.items():
        state_counts: dict[str, int] = {}
        context_refs: set[str] = set()
        supporting_refs: set[str] = set()
        contradiction_refs: set[str] = set()
        packet_ids: set[str] = set()
        counter_counts: dict[str, int] = {}
        withdrawal_counts: dict[str, int] = {}
        independence_states: set[str] = set()
        safe_examples: list[str] = []
        for chain in chains:
            argument = chain.get("argument") or {}
            route = chain.get("route") or {}
            fusion = chain.get("fusion") or {}
            safe = chain.get("safe_sentence") or {}
            state = str(route.get("defeasible_state") or safe.get("defeasible_state") or argument.get("status") or "UNKNOWN")
            state_counts[state] = state_counts.get(state, 0) + 1
            context_refs.update(str(x) for x in (argument.get("context_refs") or []) if x)
            supporting_refs.update(str(x) for x in (argument.get("supporting_refs") or []) if x)
            contradiction_refs.update(str(x) for x in (route.get("counter_evidence_refs") or argument.get("contradicting_refs") or []) if x)
            packet_id = fusion.get("packet_id")
            if packet_id:
                packet_ids.add(str(packet_id))
            independence_states.add(str(fusion.get("independence_state") or "UNKNOWN"))
            for value in argument.get("counter_scenarios") or []:
                key = str(value)
                counter_counts[key] = counter_counts.get(key, 0) + 1
            for value in argument.get("withdrawal_conditions") or []:
                key = str(value)
                withdrawal_counts[key] = withdrawal_counts.get(key, 0) + 1
            text = str(safe.get("safe_sentence_candidate_tr") or "").strip()
            if text and text not in safe_examples and len(safe_examples) < 3:
                safe_examples.append(text)

        top_counter = sorted(counter_counts.items(), key=lambda x: (-x[1], x[0]))[:5]
        top_withdrawal = sorted(withdrawal_counts.items(), key=lambda x: (-x[1], x[0]))[:5]
        cards.append({
            "mechanism_candidate_id": f"mechanism:{family}:{relation_scope}:{analysis_route}",
            "process_family": family,
            "display_tr": _mechanism_display_tr(family),
            "relation_scope": relation_scope,
            "analysis_route": analysis_route,
            "nominal_chain_count": len(chains),
            "distinct_packet_count": len(packet_ids),
            "distinct_context_ref_count": len(context_refs),
            "distinct_support_ref_count": len(supporting_refs),
            "explicit_contradiction_ref_count": len(contradiction_refs),
            "defeasible_state_counts": dict(sorted(state_counts.items())),
            "independence_states": sorted(independence_states),
            "counter_scenarios": [{"id": k, "nominal_mentions": v} for k, v in top_counter],
            "withdrawal_conditions": [{"id": k, "nominal_mentions": v} for k, v in top_withdrawal],
            "safe_sentence_examples_tr": safe_examples,
            "selection_basis": "COVERAGE_COMPRESSION_NOT_EVIDENCE_STRENGTH",
            "nominal_counts_are_independent_support": False,
            "claim_ceiling": "MECHANISM_FAMILY_PRESENTATION_CANDIDATE_ONLY",
            "cannot_say": [
                "causality",
                "coach_intention",
                "off_ball_structure",
                "pressure_geometry",
                "dominance",
                "independent_recurrence_strength_without_admitted_independence",
            ],
        })
    cards.sort(key=lambda x: (-int(x["nominal_chain_count"]), str(x["mechanism_candidate_id"])))
    return cards[:limit]

def _match_story(mechanisms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "target_mechanism_count": "3-5_WHEN_DISTINCT_ADMITTED_FAMILIES_EXIST",
        "emitted_mechanism_count": len(mechanisms),
        "forced_minimum_disabled": True,
        "selection_basis": "DISTINCT_ADMITTED_MECHANISM_FAMILY_COVERAGE",
        "cards": mechanisms,
        "claim_ceiling": "MATCH_STORY_PRESENTATION_CANDIDATE_ONLY",
    }

def _broadcast_groups(full: dict[str, Any], max_groups: int = 6) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for chain in full.get("intelligence_chains") or []:
        if not isinstance(chain, dict):
            continue
        argument = chain.get("argument") or {}
        safe = chain.get("safe_sentence") or {}
        route = chain.get("route") or {}
        if not isinstance(argument, dict) or not isinstance(safe, dict):
            continue
        text = str(safe.get("safe_sentence_candidate_tr") or "").strip()
        if not text:
            continue
        family = str(argument.get("argument_family") or "UNKNOWN_ARGUMENT_FAMILY")
        state = str(route.get("defeasible_state") or safe.get("defeasible_state") or safe.get("status") or "UNKNOWN")
        key = (family, state)
        bucket = grouped.setdefault(key, {
            "argument_family": family,
            "defeasible_state": state,
            "nominal_candidate_count": 0,
            "representative_sentence_candidate_tr": text,
            "representative_sentence_length": len(text),
            "review_required_count": 0,
        })
        bucket["nominal_candidate_count"] += 1
        if safe.get("review_required") is True or safe.get("status") == "REVIEW_REQUIRED":
            bucket["review_required_count"] += 1
        if len(text) < bucket["representative_sentence_length"]:
            bucket["representative_sentence_candidate_tr"] = text
            bucket["representative_sentence_length"] = len(text)

    groups = []
    for bucket in grouped.values():
        groups.append({
            "argument_family": bucket["argument_family"],
            "defeasible_state": bucket["defeasible_state"],
            "nominal_candidate_count": bucket["nominal_candidate_count"],
            "representative_sentence_candidate_tr": bucket["representative_sentence_candidate_tr"],
            "review_required_count": bucket["review_required_count"],
            "selection_basis": "DETERMINISTIC_SHORTEST_SAFE_SENTENCE_WITHIN_FAMILY_STATE",
            "nominal_candidate_count_is_independent_support": False,
            "claim_ceiling": "BROADCAST_COMPRESSION_CANDIDATE_ONLY",
        })
    groups.sort(key=lambda x: (-int(x["nominal_candidate_count"]), str(x["argument_family"]), str(x["defeasible_state"])))
    return groups[:max_groups]

def _broadcast_candidates(full: dict[str, Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for chain in full.get("intelligence_chains") or []:
        safe = chain.get("safe_sentence") if isinstance(chain, dict) else None
        safe = safe if isinstance(safe, dict) else {}
        text = str(safe.get("safe_sentence_candidate_tr") or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result

def _player_process_cards(root: Path, declared: set[str]) -> list[dict[str, Any]]:
    identity_name = "match_local_identity_candidates_lite_v1.json"
    trace_name = "trackable_action_trace_candidates_lite_v1.json"
    consequence_name = "trackable_action_consequence_candidates_lite_v1.json"
    required = {identity_name, trace_name, consequence_name}
    if not required.issubset(declared):
        return []

    identity = _load(root / identity_name)
    traces = _load(root / trace_name)
    consequences = _load(root / consequence_name)
    actors = {
        str(item.get("actor_identity_candidate_id")): item
        for item in (identity.get("actor_identity_candidates") or [])
        if isinstance(item, dict) and item.get("actor_identity_candidate_id")
    }

    consequence_by_trace: dict[str, dict[str, Any]] = {}
    for item in consequences.get("trackable_action_consequence_candidates") or []:
        if not isinstance(item, dict):
            continue
        trace_id = item.get("anchor_trackable_action_trace_candidate_id")
        if trace_id:
            consequence_by_trace[str(trace_id)] = item

    grouped: dict[str, dict[str, Any]] = {}
    for item in traces.get("trackable_action_trace_candidates") or []:
        if not isinstance(item, dict):
            continue
        actor_id = item.get("actor_identity_candidate_id")
        if not actor_id:
            continue
        actor_id = str(actor_id)
        bucket = grouped.setdefault(actor_id, {
            "trace_candidate_count": 0,
            "action_family_candidate_counts": {},
            "source_role_counts": {},
            "period_candidate_counts": {},
            "consequence_candidate_counts": {},
            "visible_follow_up_support_record_count": 0,
            "representative_trace_candidate_ids": [],
        })
        bucket["trace_candidate_count"] += 1
        for family in item.get("action_family_candidates") or []:
            family = str(family)
            bucket["action_family_candidate_counts"][family] = bucket["action_family_candidate_counts"].get(family, 0) + 1
        role = str(item.get("source_role") or "UNKNOWN_SOURCE_ROLE")
        bucket["source_role_counts"][role] = bucket["source_role_counts"].get(role, 0) + 1
        period = str(item.get("period_candidate") or "UNKNOWN_PERIOD")
        bucket["period_candidate_counts"][period] = bucket["period_candidate_counts"].get(period, 0) + 1
        trace_id = str(item.get("trackable_action_trace_candidate_id") or "")
        if trace_id and len(bucket["representative_trace_candidate_ids"]) < 5:
            bucket["representative_trace_candidate_ids"].append(trace_id)
        consequence = consequence_by_trace.get(trace_id)
        if consequence:
            primary = str(consequence.get("primary_consequence_candidate") or "UNKNOWN_CONSEQUENCE_CANDIDATE")
            bucket["consequence_candidate_counts"][primary] = bucket["consequence_candidate_counts"].get(primary, 0) + 1
            if consequence.get("visible_follow_up_trace_ids"):
                bucket["visible_follow_up_support_record_count"] += 1

    cards: list[dict[str, Any]] = []
    for actor_id, counts in grouped.items():
        actor = actors.get(actor_id, {})
        aliases = actor.get("actor_aliases_raw") or []
        display = aliases[0] if aliases else actor.get("actor_normalized_key") or actor_id
        cards.append({
            "actor_identity_candidate_id": actor_id,
            "actor_display_candidate": display,
            "team_identity_candidate_id": actor.get("team_identity_candidate_id"),
            "team_normalized_key": actor.get("team_normalized_key"),
            "identity_scope": actor.get("identity_scope", "MATCH_LOCAL_CANDIDATE_ONLY"),
            "validated_player_identity": bool(actor.get("validated_player_identity")),
            "trace_candidate_count": counts["trace_candidate_count"],
            "action_family_candidate_counts": dict(sorted(counts["action_family_candidate_counts"].items())),
            "source_role_counts": dict(sorted(counts["source_role_counts"].items())),
            "period_candidate_counts": dict(sorted(counts["period_candidate_counts"].items())),
            "consequence_candidate_record_counts": dict(sorted(counts["consequence_candidate_counts"].items())),
            "visible_follow_up_support_record_count": counts["visible_follow_up_support_record_count"],
            "representative_trace_candidate_ids": counts["representative_trace_candidate_ids"],
            "trace_candidate_count_is_physical_action_count": False,
            "process_participation_is_off_ball_tactical_role": False,
            "claim_ceiling": "RECORDED_ACTION_PARTICIPATION_CANDIDATE_ONLY",
            "cannot_say": [
                "off_ball_tactical_role",
                "positioning_truth",
                "pressure_geometry",
                "physical_load",
                "speed_or_distance_truth",
                "coach_intention",
                "player_quality_from_trace_volume_alone",
            ],
        })
    cards.sort(key=lambda x: (-int(x["trace_candidate_count"]), str(x["actor_identity_candidate_id"])))
    return cards

def _traceback_index(root: Path, full: dict[str, Any], episode: dict[str, Any], declared: set[str]) -> dict[str, Any]:
    episode_index: dict[str, Any] = {}
    for item in episode.get("episode_candidates") or []:
        if not isinstance(item, dict) or not item.get("episode_candidate_id"):
            continue
        episode_index[str(item["episode_candidate_id"])] = {
            "context_refs": [str(x) for x in (item.get("context_refs") or [])],
            "row_nucleus_refs": [str(x) for x in (item.get("row_nucleus_refs") or [])],
            "action_occurrence_eligible_context_refs": [str(x) for x in (item.get("action_occurrence_eligible_context_refs") or [])],
            "support_only_context_refs": [str(x) for x in (item.get("support_only_context_refs") or [])],
            "review_debt_refs": [str(x) for x in (item.get("review_debt_refs") or [])],
            "source_artifact": "analyst_episode_locator_lite_v1.json",
        }

    mechanism_index: dict[str, Any] = {}
    for chain in full.get("intelligence_chains") or []:
        if not isinstance(chain, dict):
            continue
        argument = chain.get("argument") or {}
        fusion = chain.get("fusion") or {}
        if not isinstance(argument, dict) or not argument:
            continue
        family, relation_scope, analysis_route = _mechanism_key(argument)
        mechanism_id = f"mechanism:{family}:{relation_scope}:{analysis_route}"
        entry = mechanism_index.setdefault(mechanism_id, {
            "argument_ids": [],
            "packet_ids": [],
            "context_refs": [],
            "supporting_refs": [],
            "contradicting_refs": [],
            "source_artifact": "active_match_full_spine_v1.json",
        })
        for key, source in [
            ("argument_ids", [argument.get("argument_id")]),
            ("packet_ids", [fusion.get("packet_id")]),
            ("context_refs", argument.get("context_refs") or []),
            ("supporting_refs", argument.get("supporting_refs") or []),
            ("contradicting_refs", argument.get("contradicting_refs") or []),
        ]:
            seen = set(entry[key])
            for value in source:
                if value not in [None, ""] and str(value) not in seen:
                    entry[key].append(str(value))
                    seen.add(str(value))

    player_index: dict[str, Any] = {}
    trace_name = "trackable_action_trace_candidates_lite_v1.json"
    consequence_name = "trackable_action_consequence_candidates_lite_v1.json"
    if {trace_name, consequence_name}.issubset(declared):
        traces = _load(root / trace_name)
        consequences = _load(root / consequence_name)
        for item in traces.get("trackable_action_trace_candidates") or []:
            if not isinstance(item, dict) or not item.get("actor_identity_candidate_id"):
                continue
            actor_id = str(item["actor_identity_candidate_id"])
            entry = player_index.setdefault(actor_id, {
                "trace_candidate_ids": [],
                "supporting_evidence_atom_ids": [],
                "source_artifacts": [trace_name, consequence_name],
            })
            trace_id = item.get("trackable_action_trace_candidate_id")
            if trace_id:
                entry["trace_candidate_ids"].append(str(trace_id))
            entry["supporting_evidence_atom_ids"].extend(
                str(x) for x in (item.get("supporting_evidence_atom_ids") or []) if x
            )

        consequence_map: dict[str, list[str]] = {}
        for item in consequences.get("trackable_action_consequence_candidates") or []:
            if not isinstance(item, dict):
                continue
            trace_id = item.get("anchor_trackable_action_trace_candidate_id")
            consequence_id = item.get("trackable_action_consequence_candidate_id")
            if trace_id and consequence_id:
                consequence_map.setdefault(str(trace_id), []).append(str(consequence_id))
        for entry in player_index.values():
            entry["consequence_candidate_ids_by_trace"] = {
                trace_id: consequence_map.get(trace_id, [])
                for trace_id in entry["trace_candidate_ids"]
            }
            entry["supporting_evidence_atom_ids"] = sorted(set(entry["supporting_evidence_atom_ids"]))

    return {
        "scope": "REFERENCE_ID_GRAPH_ONLY_NOT_RAW_ROW_RENDER",
        "episodes": episode_index,
        "mechanisms": mechanism_index,
        "players": player_index,
        "claim_ceiling": "TRACEBACK_REFERENCE_INDEX_ONLY",
    }

def _count_labels(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        values = item.get(key)
        values = values if isinstance(values, list) else [values] if values not in [None, ""] else []
        for value in values:
            label = str(value)
            counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))

def _six_phase_lens(phase_cards: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts = _count_labels(phase_cards, "labels")
    phase_specs = [
        {
            "phase": "YERLESIK_HUCUM",
            "status": "PROXY_LENS_ONLY" if any(label_counts.get(x, 0) for x in [
                "CIRCULATION_ACTIVITY_CANDIDATE",
                "ADVANCED_ACCESS_ACTIVITY_CANDIDATE",
                "TERMINAL_ACTIVITY_CANDIDATE",
            ]) else "NOT_EVALUATED",
            "source_activity_labels": [
                "CIRCULATION_ACTIVITY_CANDIDATE",
                "ADVANCED_ACCESS_ACTIVITY_CANDIDATE",
                "TERMINAL_ACTIVITY_CANDIDATE",
            ],
        },
        {
            "phase": "GECIS_HUCUMU",
            "status": "PROXY_LENS_ONLY" if label_counts.get("RECOVERY_TRANSITION_ACTIVITY_CANDIDATE", 0) else "NOT_EVALUATED",
            "source_activity_labels": ["RECOVERY_TRANSITION_ACTIVITY_CANDIDATE"],
        },
        {
            "phase": "YERLESIK_SAVUNMA",
            "status": "NOT_EVALUATED",
            "source_activity_labels": [],
        },
        {
            "phase": "GECIS_SAVUNMASI",
            "status": "PROXY_LENS_ONLY" if label_counts.get("LOSS_TRANSITION_ACTIVITY_CANDIDATE", 0) else "NOT_EVALUATED",
            "source_activity_labels": ["LOSS_TRANSITION_ACTIVITY_CANDIDATE"],
        },
        {
            "phase": "DURAN_TOP_HUCUMU",
            "status": "NOT_EVALUATED",
            "source_activity_labels": [],
        },
        {
            "phase": "DURAN_TOP_SAVUNMASI",
            "status": "NOT_EVALUATED",
            "source_activity_labels": [],
        },
    ]
    for spec in phase_specs:
        spec["source_activity_label_mention_count"] = sum(label_counts.get(label, 0) for label in spec["source_activity_labels"])
        spec["phase_truth"] = False
        spec["possession_truth"] = False
        spec["tactical_truth"] = False
        spec["claim_ceiling"] = "SIX_PHASE_PRESENTATION_PROXY_LENS_ONLY"
    return {
        "mapping_policy": "CANONICAL_PHASE_SLOTS_WITH_PROXY_LENS_OR_NOT_EVALUATED",
        "phase_truth": False,
        "phases": phase_specs,
        "unresolved_activity_state_count": label_counts.get("UNRESOLVED_ACTIVITY_STATE", 0),
    }

def _comparative_views(
    mechanism_cards: list[dict[str, Any]],
    episode_cards: list[dict[str, Any]],
    player_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    team_labels = {
        str(card.get("team_identity_candidate_id")): card.get("team_normalized_key")
        for card in player_cards
        if card.get("team_identity_candidate_id") and card.get("team_normalized_key")
    }

    period_rows: list[dict[str, Any]] = []
    team_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    for card in mechanism_cards:
        mechanism_id = card.get("mechanism_candidate_id")
        where_when = card.get("where_when") or {}

        period_time = where_when.get("period_time_anchor_counts") or {}
        period_spatial = where_when.get("period_spatial_anchor_counts") or {}
        periods = sorted(set(period_time) | set(period_spatial))
        for period in periods:
            period_rows.append({
                "mechanism_candidate_id": mechanism_id,
                "period_candidate": str(period),
                "time_anchor_count": int(period_time.get(period, 0)),
                "spatial_anchor_count": int(period_spatial.get(period, 0)),
                "eligible_time_anchor_denominator": int(where_when.get("time_anchor_count") or 0),
                "eligible_spatial_anchor_denominator": int(where_when.get("spatial_anchor_count") or 0),
                "counts_are_independent_recurrence": False,
            })

        for team_id, count in sorted((where_when.get("team_spatial_anchor_counts") or {}).items()):
            team_rows.append({
                "mechanism_candidate_id": mechanism_id,
                "team_identity_candidate_id": team_id,
                "team_display_candidate": team_labels.get(team_id, team_id),
                "spatial_anchor_count": int(count),
                "eligible_spatial_anchor_denominator": int(where_when.get("spatial_anchor_count") or 0),
                "team_identity_is_candidate_only": True,
                "counts_are_independent_recurrence": False,
            })

        for state, count in sorted((card.get("defeasible_state_counts") or {}).items()):
            state_rows.append({
                "mechanism_candidate_id": mechanism_id,
                "defeasible_state": str(state),
                "nominal_chain_count": int(count),
                "eligible_denominator_nominal_chain_count": int(card.get("nominal_chain_count") or 0),
                "independence_admitted": False,
            })

    zone_by_period: dict[tuple[str, str], int] = {}
    channel_by_period: dict[tuple[str, str], int] = {}
    eligible_zone_mentions_by_period: dict[str, int] = {}
    eligible_channel_mentions_by_period: dict[str, int] = {}
    for episode in episode_cards:
        period = str(episode.get("period_candidate") or "UNKNOWN_PERIOD")
        for zone, count in (episode.get("zone_surface") or {}).items():
            value = int(count)
            zone_by_period[(period, str(zone))] = zone_by_period.get((period, str(zone)), 0) + value
            eligible_zone_mentions_by_period[period] = eligible_zone_mentions_by_period.get(period, 0) + value
        for channel, count in (episode.get("channel_surface") or {}).items():
            value = int(count)
            channel_by_period[(period, str(channel))] = channel_by_period.get((period, str(channel)), 0) + value
            eligible_channel_mentions_by_period[period] = eligible_channel_mentions_by_period.get(period, 0) + value

    zone_rows = [
        {
            "period_candidate": period,
            "zone_candidate": zone,
            "eligible_action_zone_mention_count": count,
            "eligible_denominator_zone_mentions": eligible_zone_mentions_by_period.get(period, 0),
            "share_not_emitted": True,
        }
        for (period, zone), count in sorted(zone_by_period.items())
    ]
    channel_rows = [
        {
            "period_candidate": period,
            "channel_candidate": channel,
            "eligible_action_channel_mention_count": count,
            "eligible_denominator_channel_mentions": eligible_channel_mentions_by_period.get(period, 0),
            "share_not_emitted": True,
        }
        for (period, channel), count in sorted(channel_by_period.items())
    ]

    return {
        "policy": "COMPARE_ONLY_ON_DECLARED_CANDIDATE_UNITS_WITH_VISIBLE_DENOMINATORS",
        "period_mechanism_comparison": {
            "state": "EXACT_NOMINAL_COUNTS_WITH_ELIGIBLE_DENOMINATORS",
            "rows": period_rows,
            "note": "Counts cover the exact reference-linked anchor population but do not represent independent recurrence.",
        },
        "team_coordinate_comparison": {
            "state": "EXACT_NOMINAL_COUNTS_WITH_ELIGIBLE_DENOMINATOR",
            "rows": team_rows,
            "note": "Team identities remain match-local candidates; anchor counts are nominal reference-linked counts.",
        },
        "defeasible_state_comparison": {
            "state": "COUNT_WITH_ELIGIBLE_DENOMINATOR",
            "rows": state_rows,
        },
        "zone_mentions_by_period": {
            "state": "COUNT_WITH_ELIGIBLE_DENOMINATOR",
            "rows": zone_rows,
            "count_unit": "eligible_action_zone_mentions",
        },
        "channel_mentions_by_period": {
            "state": "COUNT_WITH_ELIGIBLE_DENOMINATOR",
            "rows": channel_rows,
            "count_unit": "eligible_action_channel_mentions",
        },
        "forbidden_inference": [
            "preview_sample_as_full_population",
            "candidate_team_identity_as_validated_identity",
            "zone_or_channel_mentions_as_time_share",
            "zone_or_channel_mentions_as_possession_share",
            "nominal_chain_count_as_independent_recurrence",
            "count_difference_as_causal_effect",
        ],
    }

def _football_dynamics_surface(
    root: Path,
    declared: set[str],
    player_cards: list[dict[str, Any]],
    mechanism_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    trace_name = "trackable_action_trace_candidates_lite_v1.json"
    consequence_name = "trackable_action_consequence_candidates_lite_v1.json"
    if not {trace_name, consequence_name}.issubset(declared):
        return {
            "state": "NOT_EVALUATED",
            "reason": "required_current_invocation_surfaces_missing",
            "claim_ceiling": "NO_DYNAMICS_CLAIM",
        }

    traces = (_load(root / trace_name).get("trackable_action_trace_candidates") or [])
    consequences = (_load(root / consequence_name).get("trackable_action_consequence_candidates") or [])
    team_labels = {
        str(card.get("team_identity_candidate_id")): card.get("team_normalized_key")
        for card in player_cards
        if card.get("team_identity_candidate_id")
    }
    actor_labels = {
        str(card.get("actor_identity_candidate_id")): card.get("actor_display_candidate")
        for card in player_cards
        if card.get("actor_identity_candidate_id")
    }

    rhythm_bins: dict[tuple[str, int], int] = {}
    rhythm_detail_windows: dict[tuple[str, int], dict[str, dict[str, int]]] = {}
    player_points: dict[str, list[tuple[float, float]]] = {}
    trace_team: dict[str, str] = {}
    trace_families: dict[str, list[str]] = {}
    for item in traces:
        if not isinstance(item, dict):
            continue
        trace_id = str(item.get("trackable_action_trace_candidate_id") or "")
        team_id = str(item.get("team_identity_candidate_id") or "UNKNOWN_TEAM")
        actor_id = str(item.get("actor_identity_candidate_id") or "UNKNOWN_ACTOR")
        trace_team[trace_id] = team_id
        trace_families[trace_id] = [str(x) for x in item.get("action_family_candidates") or []]
        try:
            start = float(item.get("start_candidate"))
        except (TypeError, ValueError):
            start = None
        period = str(item.get("period_candidate") or "UNKNOWN_PERIOD")
        if start is not None and start >= 0:
            bin_start = int(start // 300) * 5
            key = (period, bin_start)
            rhythm_bins[key] = rhythm_bins.get(key, 0) + 1
            detail = rhythm_detail_windows.setdefault(key, {"team": {}, "actor": {}, "family": {}})
            detail["team"][team_id] = detail["team"].get(team_id, 0) + 1
            detail["actor"][actor_id] = detail["actor"].get(actor_id, 0) + 1
            for family in trace_families.get(trace_id) or []:
                detail["family"][family] = detail["family"].get(family, 0) + 1
        try:
            x = float(item.get("pos_x_candidate"))
            y = float(item.get("pos_y_candidate"))
        except (TypeError, ValueError):
            continue
        player_points.setdefault(actor_id, []).append((x, y))

    rhythm_rows: list[dict[str, Any]] = []
    by_period_counts: dict[str, list[int]] = {}
    for (period, bin_start), count in sorted(rhythm_bins.items()):
        by_period_counts.setdefault(period, []).append(count)
    period_medians: dict[str, float] = {}
    for period, values in by_period_counts.items():
        ordered = sorted(values)
        n = len(ordered)
        if not n:
            continue
        mid = n // 2
        period_medians[period] = float(ordered[mid]) if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    for (period, bin_start), count in sorted(rhythm_bins.items()):
        median = period_medians.get(period)
        relation = "UNKNOWN"
        if median is not None:
            relation = "ABOVE_PERIOD_MEDIAN" if count > median else "BELOW_PERIOD_MEDIAN" if count < median else "AT_PERIOD_MEDIAN"
        rhythm_rows.append({
            "period_candidate": period,
            "window_start_minute_candidate": bin_start,
            "window_end_minute_candidate": bin_start + 5,
            "nominal_trace_candidate_count": count,
            "period_median_nominal_trace_candidate_count": median,
            "relative_activity_state": relation,
            "trace_count_is_physical_action_count": False,
            "tempo_truth": False,
        })

    consequence_rows: dict[tuple[str, str, str], int] = {}
    consequence_windows: dict[tuple[str, int], dict[str, int]] = {}
    consequence_detail_windows: dict[tuple[str, int], dict[str, dict[str, int]]] = {}
    for item in consequences:
        if not isinstance(item, dict):
            continue
        trace_id = str(item.get("anchor_trackable_action_trace_candidate_id") or "")
        family_set = set(trace_families.get(trace_id) or [])
        anchor_kind = None
        if "TURNOVER" in family_set:
            anchor_kind = "TURNOVER"
        elif "RECOVERY" in family_set:
            anchor_kind = "RECOVERY"
        if not anchor_kind:
            continue
        try:
            anchor_start = float(item.get("anchor_start_candidate"))
        except (TypeError, ValueError):
            anchor_start = None
        period = str(item.get("period_candidate") or "UNKNOWN_PERIOD")
        team_id = str(item.get("team_identity_candidate_id") or trace_team.get(trace_id) or "UNKNOWN_TEAM")
        primary = str(item.get("primary_consequence_candidate") or "UNKNOWN_CONSEQUENCE_CANDIDATE")
        if anchor_start is not None and anchor_start >= 0:
            bin_start = int(anchor_start // 300) * 5
            key = (period, bin_start)
            bucket = consequence_windows.setdefault(key, {"TURNOVER": 0, "RECOVERY": 0})
            bucket[anchor_kind] = bucket.get(anchor_kind, 0) + 1
            detail = consequence_detail_windows.setdefault(key, {"team": {}, "primary": {}, "team_primary": {}})
            detail["team"][team_id] = detail["team"].get(team_id, 0) + 1
            detail["primary"][primary] = detail["primary"].get(primary, 0) + 1
            tp_key = f"{team_id}|{primary}"
            detail["team_primary"][tp_key] = detail["team_primary"].get(tp_key, 0) + 1
        key = (team_id, anchor_kind, primary)
        consequence_rows[key] = consequence_rows.get(key, 0) + 1
    loss_recovery_rows = [
        {
            "team_identity_candidate_id": team_id,
            "team_display_candidate": team_labels.get(team_id, team_id),
            "anchor_action_family": anchor_kind,
            "primary_consequence_candidate": primary,
            "nominal_consequence_candidate_count": count,
            "consequence_candidate_is_causal_truth": False,
            "team_response_is_tactical_truth": False,
        }
        for (team_id, anchor_kind, primary), count in sorted(consequence_rows.items())
    ]

    turning_point_rows: list[dict[str, Any]] = []
    previous_state_by_period: dict[str, str] = {}
    for row in rhythm_rows:
        period = str(row.get("period_candidate") or "UNKNOWN_PERIOD")
        current_state = str(row.get("relative_activity_state") or "UNKNOWN")
        previous_state = previous_state_by_period.get(period)
        previous_state_by_period[period] = current_state
        window_start = int(row.get("window_start_minute_candidate") or 0)
        consequence_counts = consequence_windows.get((period, window_start), {"TURNOVER": 0, "RECOVERY": 0})
        transition_anchor_count = int(consequence_counts.get("TURNOVER", 0)) + int(consequence_counts.get("RECOVERY", 0))
        rhythm_state_changed = previous_state is not None and current_state != previous_state
        if rhythm_state_changed and transition_anchor_count > 0:
            rhythm_detail = rhythm_detail_windows.get((period, window_start), {"team": {}, "actor": {}, "family": {}})
            consequence_detail = consequence_detail_windows.get((period, window_start), {"team": {}, "primary": {}, "team_primary": {}})
            team_trace_rows = [
                {
                    "team_identity_candidate_id": team_id,
                    "team_display_candidate": team_labels.get(team_id, team_id),
                    "nominal_trace_candidate_count": int(count),
                }
                for team_id, count in sorted(
                    rhythm_detail.get("team", {}).items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )
            ]
            player_trace_rows = [
                {
                    "actor_identity_candidate_id": actor_id,
                    "actor_display_candidate": actor_labels.get(actor_id, actor_id),
                    "nominal_trace_candidate_count": int(count),
                    "ranking_basis": "NAVIGATION_VOLUME_ONLY_NOT_PLAYER_QUALITY",
                }
                for actor_id, count in sorted(
                    rhythm_detail.get("actor", {}).items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )[:5]
            ]
            action_family_rows = [
                {
                    "action_family_candidate": family,
                    "nominal_mention_count": int(count),
                }
                for family, count in sorted(
                    rhythm_detail.get("family", {}).items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )
            ]
            consequence_rows_window = [
                {
                    "primary_consequence_candidate": primary,
                    "nominal_consequence_candidate_count": int(count),
                }
                for primary, count in sorted(
                    consequence_detail.get("primary", {}).items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )
            ]
            turning_point_rows.append({
                "period_candidate": period,
                "window_start_minute_candidate": window_start,
                "window_end_minute_candidate": int(row.get("window_end_minute_candidate") or (window_start + 5)),
                "previous_activity_state": previous_state,
                "current_activity_state": current_state,
                "turnover_anchor_consequence_count": int(consequence_counts.get("TURNOVER", 0)),
                "recovery_anchor_consequence_count": int(consequence_counts.get("RECOVERY", 0)),
                "change_signal_count": 2,
                "team_trace_candidate_counts": team_trace_rows,
                "top_player_trace_candidate_counts": player_trace_rows,
                "action_family_candidate_counts": action_family_rows,
                "primary_consequence_candidate_counts": consequence_rows_window,
                "candidate_reason": "RHYTHM_STATE_CHANGE_PLUS_LOSS_RECOVERY_CONSEQUENCE_ACTIVITY",
                "is_match_turning_point_truth": False,
                "is_causal_break": False,
                "claim_ceiling": "TURNING_POINT_CANDIDATE_ONLY",
            })

    mechanism_variant_rows: list[dict[str, Any]] = []
    for card in mechanism_cards:
        mechanism_id = card.get("mechanism_candidate_id")
        denominator = int(card.get("nominal_chain_count") or 0)
        for state, count in sorted((card.get("defeasible_state_counts") or {}).items()):
            state_text = str(state)
            normalized_state = {
                "ARGUMENT_SUPPORTED": "SUPPORTED",
                "ARGUMENT_WEAKENED": "WEAKENED",
            }.get(state_text, state_text)
            mechanism_variant_rows.append({
                "mechanism_candidate_id": mechanism_id,
                "mechanism_display_tr": card.get("display_tr"),
                "reading_variant_state": normalized_state,
                "source_reading_variant_state": state_text,
                "nominal_chain_count": int(count),
                "eligible_nominal_chain_denominator": denominator,
                "is_distinct_football_mechanism_variant_truth": False,
                "independence_admitted": False,
                "claim_ceiling": "MECHANISM_READING_VARIANT_ONLY",
            })

    player_location_rows: list[dict[str, Any]] = []
    for actor_id, points in sorted(player_points.items()):
        if not points:
            continue
        xs = sorted(p[0] for p in points)
        ys = sorted(p[1] for p in points)
        def med(values: list[float]) -> float:
            n = len(values)
            m = n // 2
            return values[m] if n % 2 else (values[m - 1] + values[m]) / 2.0
        player_location_rows.append({
            "actor_identity_candidate_id": actor_id,
            "actor_display_candidate": actor_labels.get(actor_id, actor_id),
            "recorded_coordinate_anchor_count": len(points),
            "median_action_x_candidate": med(xs),
            "median_action_y_candidate": med(ys),
            "is_player_position": False,
            "is_off_ball_role_truth": False,
            "claim_ceiling": "RECORDED_ACTION_LOCATION_CANDIDATE_ONLY",
        })

    return {
        "state": "AVAILABLE",
        "activity_rhythm_proxy": {
            "state": "AVAILABLE" if rhythm_rows else "NOT_EVALUATED",
            "rows": rhythm_rows,
            "unit": "nominal_trackable_trace_candidates_per_5min_window",
            "football_meaning": "visible recorded-action activity rhythm proxy",
            "forbidden_inference": ["true_match_tempo", "physical_intensity", "possession_speed", "dominance"],
        },
        "loss_recovery_visible_consequences": {
            "state": "AVAILABLE" if loss_recovery_rows else "NOT_EVALUATED",
            "rows": loss_recovery_rows,
            "football_meaning": "visible consequence candidates after recorded TURNOVER/RECOVERY anchors",
            "forbidden_inference": ["causal_effect", "press_success", "transition_quality_fact", "tactical_intention"],
        },
        "turning_point_candidates": {
            "state": "AVAILABLE" if turning_point_rows else "NOT_EVALUATED",
            "rows": turning_point_rows,
            "football_meaning": "multi-signal candidate windows where visible action-rhythm state changes coincide with loss/recovery consequence activity",
            "forbidden_inference": ["true_match_turning_point", "causal_break", "momentum_truth", "psychological_shift"],
        },
        "mechanism_reading_variants": {
            "state": "AVAILABLE" if mechanism_variant_rows else "NOT_EVALUATED",
            "rows": mechanism_variant_rows,
            "football_meaning": "SUPPORTED/WEAKENED reading variants inside the same mechanism family",
            "forbidden_inference": ["distinct_football_mechanism_variant", "success_failure_variant_truth", "independent_recurrence"],
        },
        "player_action_location_candidates": {
            "state": "AVAILABLE" if player_location_rows else "NOT_EVALUATED",
            "rows": player_location_rows,
            "football_meaning": "median recorded action location, not player position",
            "forbidden_inference": ["player_position", "team_shape", "off_ball_role", "compactness"],
        },
        "claim_ceiling": "EVENT_DERIVED_PRESENTATION_INTELLIGENCE_ONLY",
    }

def _comparison_cards(comparative: dict[str, Any]) -> dict[str, Any]:
    cards: list[dict[str, Any]] = []

    period_rows = (comparative.get("period_mechanism_comparison") or {}).get("rows") or []
    if period_rows:
        cards.append({
            "card_id": "comparison:period_mechanism",
            "card_type": "PERIOD_MECHANISM_ANCHOR_COMPARISON",
            "title_tr": "Periyot bazlı mekanizma anchor karşılaştırması",
            "graph": "GROUPED_BAR_WITH_ELIGIBLE_DENOMINATORS",
            "rows": period_rows,
            "broadcast_copy_candidate_tr": "Periyot bazlı time/spatial anchor sayıları eligible denominator ile birlikte gösterilir; fark mekanizma gücü değildir.",
            "broadcast_copy_is_final": False,
            "claim_ceiling": "NOMINAL_REFERENCE_LINKED_COMPARISON_ONLY",
        })

    team_rows = (comparative.get("team_coordinate_comparison") or {}).get("rows") or []
    if team_rows:
        cards.append({
            "card_id": "comparison:team_coordinate",
            "card_type": "TEAM_CANDIDATE_COORDINATE_COMPARISON",
            "title_tr": "Takım-candidate coordinate anchor karşılaştırması",
            "graph": "GROUPED_BAR_OR_SMALL_MULTIPLE_SCATTER_WITH_ELIGIBLE_DENOMINATOR",
            "rows": team_rows,
            "broadcast_copy_candidate_tr": "Takım-candidate coordinate anchor sayıları aynı eligible spatial denominator içinde karşılaştırılır; kimlikler match-local candidate düzeyindedir.",
            "broadcast_copy_is_final": False,
            "claim_ceiling": "TEAM_CANDIDATE_NOMINAL_ANCHOR_COMPARISON_ONLY",
        })

    state_rows = (comparative.get("defeasible_state_comparison") or {}).get("rows") or []
    if state_rows:
        cards.append({
            "card_id": "comparison:defeasible_state",
            "card_type": "DEFEASIBLE_STATE_COMPARISON",
            "title_tr": "SUPPORTED / WEAKENED dağılımı",
            "graph": "STACKED_BAR_WITH_EXPLICIT_DENOMINATOR",
            "rows": state_rows,
            "broadcast_copy_candidate_tr": "SUPPORTED ve WEAKENED nominal chain sayıları aynı eligible chain denominator içinde gösterilir; independence admitted değildir.",
            "broadcast_copy_is_final": False,
            "claim_ceiling": "DEFEASIBLE_STATE_DISTRIBUTION_ONLY",
        })

    for key, card_id, title, graph in [
        ("zone_mentions_by_period", "comparison:zone_period", "Zone mention × periyot", "GROUPED_BAR_COUNTS_ONLY"),
        ("channel_mentions_by_period", "comparison:channel_period", "Channel mention × periyot", "GROUPED_BAR_COUNTS_ONLY"),
    ]:
        rows = (comparative.get(key) or {}).get("rows") or []
        if rows:
            cards.append({
                "card_id": card_id,
                "card_type": "MENTION_COUNT_BY_PERIOD",
                "title_tr": title,
                "graph": graph,
                "rows": rows,
                "broadcast_copy_candidate_tr": "Mention sayıları yalnız kendi eligible mention denominator'ları içinde okunur; time share veya possession share değildir.",
                "broadcast_copy_is_final": False,
                "claim_ceiling": "MENTION_COUNT_COMPARISON_ONLY",
            })

    return {
        "mobile_cards": cards,
        "broadcast_graph_cards": [
            {
                "card_id": card["card_id"],
                "title_tr": card["title_tr"],
                "graph": card["graph"],
                "rows": card["rows"],
                "broadcast_copy_candidate_tr": card["broadcast_copy_candidate_tr"],
                "broadcast_copy_is_final": False,
                "claim_ceiling": card["claim_ceiling"],
            }
            for card in cards
        ],
        "card_count": len(cards),
        "policy": "COMPACT_COMPARISON_WITH_VISIBLE_DENOMINATOR_AND_NO_EVALUATIVE_VERDICT",
        "forbidden_inference": comparative.get("forbidden_inference") or [],
    }

def _chart_render_pack(
    comparison_cards: dict[str, Any],
    football_dynamics: dict[str, Any],
) -> dict[str, Any]:
    specs: list[dict[str, Any]] = []
    for card in comparison_cards.get("mobile_cards") or []:
        card_id = str(card.get("card_id"))
        rows = card.get("rows") or []
        if card_id == "comparison:period_mechanism":
            categories = [str(row.get("period_candidate")) for row in rows]
            specs.append({
                "chart_id": "chart:period_mechanism",
                "source_card_id": card_id,
                "chart_type": "GROUPED_BAR",
                "categories": categories,
                "series": [
                    {"name": "time_anchor_count", "values": [int(row.get("time_anchor_count") or 0) for row in rows]},
                    {"name": "spatial_anchor_count", "values": [int(row.get("spatial_anchor_count") or 0) for row in rows]},
                ],
                "denominators": [
                    {
                        "period_candidate": row.get("period_candidate"),
                        "eligible_time_anchor_denominator": row.get("eligible_time_anchor_denominator"),
                        "eligible_spatial_anchor_denominator": row.get("eligible_spatial_anchor_denominator"),
                    }
                    for row in rows
                ],
                "claim_ceiling": card.get("claim_ceiling"),
            })
        elif card_id == "comparison:team_coordinate":
            specs.append({
                "chart_id": "chart:team_coordinate",
                "source_card_id": card_id,
                "chart_type": "BAR",
                "categories": [str(row.get("team_display_candidate")) for row in rows],
                "series": [
                    {"name": "spatial_anchor_count", "values": [int(row.get("spatial_anchor_count") or 0) for row in rows]},
                ],
                "denominators": [
                    {
                        "team_identity_candidate_id": row.get("team_identity_candidate_id"),
                        "eligible_spatial_anchor_denominator": row.get("eligible_spatial_anchor_denominator"),
                        "team_identity_is_candidate_only": row.get("team_identity_is_candidate_only"),
                    }
                    for row in rows
                ],
                "claim_ceiling": card.get("claim_ceiling"),
            })
        elif card_id == "comparison:defeasible_state":
            specs.append({
                "chart_id": "chart:defeasible_state",
                "source_card_id": card_id,
                "chart_type": "STACKED_BAR",
                "categories": [str(row.get("defeasible_state")) for row in rows],
                "series": [
                    {"name": "nominal_chain_count", "values": [int(row.get("nominal_chain_count") or 0) for row in rows]},
                ],
                "denominators": [
                    {
                        "defeasible_state": row.get("defeasible_state"),
                        "eligible_denominator_nominal_chain_count": row.get("eligible_denominator_nominal_chain_count"),
                        "independence_admitted": row.get("independence_admitted"),
                    }
                    for row in rows
                ],
                "claim_ceiling": card.get("claim_ceiling"),
            })
        elif card_id in {"comparison:zone_period", "comparison:channel_period"}:
            is_zone = card_id.endswith("zone_period")
            label_key = "zone_candidate" if is_zone else "channel_candidate"
            value_key = "eligible_action_zone_mention_count" if is_zone else "eligible_action_channel_mention_count"
            denom_key = "eligible_denominator_zone_mentions" if is_zone else "eligible_denominator_channel_mentions"
            periods = sorted({str(row.get("period_candidate")) for row in rows})
            labels = sorted({str(row.get(label_key)) for row in rows})
            lookup = {(str(row.get("period_candidate")), str(row.get(label_key))): int(row.get(value_key) or 0) for row in rows}
            specs.append({
                "chart_id": "chart:zone_period" if is_zone else "chart:channel_period",
                "source_card_id": card_id,
                "chart_type": "GROUPED_BAR",
                "categories": periods,
                "series": [
                    {"name": label, "values": [lookup.get((period, label), 0) for period in periods]}
                    for label in labels
                ],
                "denominators": [
                    {
                        "period_candidate": period,
                        denom_key: next((row.get(denom_key) for row in rows if str(row.get("period_candidate")) == period), None),
                    }
                    for period in periods
                ],
                "claim_ceiling": card.get("claim_ceiling"),
            })

    rhythm_rows = (football_dynamics.get("activity_rhythm_proxy") or {}).get("rows") or []
    if rhythm_rows:
        periods = sorted({str(row.get("period_candidate")) for row in rhythm_rows})
        for period in periods:
            rows = [row for row in rhythm_rows if str(row.get("period_candidate")) == period]
            rows.sort(key=lambda row: int(row.get("window_start_minute_candidate") or 0))
            specs.append({
                "chart_id": f"chart:activity_rhythm:{period}",
                "source_card_id": "football_dynamics:activity_rhythm_proxy",
                "chart_type": "LINE_OR_STEP_BAR",
                "categories": [f"{row.get('window_start_minute_candidate')}-{row.get('window_end_minute_candidate')}" for row in rows],
                "series": [
                    {
                        "name": "nominal_trace_candidate_count",
                        "values": [int(row.get("nominal_trace_candidate_count") or 0) for row in rows],
                    },
                    {
                        "name": "period_median_nominal_trace_candidate_count",
                        "values": [row.get("period_median_nominal_trace_candidate_count") for row in rows],
                    },
                ],
                "denominators": [],
                "claim_ceiling": "VISIBLE_RECORDED_ACTION_ACTIVITY_RHYTHM_PROXY_ONLY",
                "football_label_tr": "Görünür aksiyon ritmi",
            })

    consequence_rows = (football_dynamics.get("loss_recovery_visible_consequences") or {}).get("rows") or []
    if consequence_rows:
        teams = sorted({str(row.get("team_display_candidate")) for row in consequence_rows})
        outcomes = sorted({str(row.get("primary_consequence_candidate")) for row in consequence_rows})
        for anchor_kind in ["TURNOVER", "RECOVERY"]:
            subset = [row for row in consequence_rows if row.get("anchor_action_family") == anchor_kind]
            if not subset:
                continue
            lookup = {
                (str(row.get("team_display_candidate")), str(row.get("primary_consequence_candidate"))):
                    int(row.get("nominal_consequence_candidate_count") or 0)
                for row in subset
            }
            specs.append({
                "chart_id": f"chart:{anchor_kind.lower()}_visible_consequences",
                "source_card_id": "football_dynamics:loss_recovery_visible_consequences",
                "chart_type": "GROUPED_BAR",
                "categories": teams,
                "series": [
                    {"name": outcome, "values": [lookup.get((team, outcome), 0) for team in teams]}
                    for outcome in outcomes
                    if any(lookup.get((team, outcome), 0) for team in teams)
                ],
                "denominators": [],
                "claim_ceiling": "VISIBLE_CONSEQUENCE_CANDIDATE_COUNTS_ONLY",
                "football_label_tr": "Top kaybı sonrası görünen sonuçlar" if anchor_kind == "TURNOVER" else "Geri kazanım sonrası görünen sonuçlar",
            })

    turning_rows = (football_dynamics.get("turning_point_candidates") or {}).get("rows") or []
    if turning_rows:
        specs.append({
            "chart_id": "chart:turning_point_candidates",
            "source_card_id": "football_dynamics:turning_point_candidates",
            "chart_type": "TIMELINE_MARKERS",
            "markers": [
                {
                    "period_candidate": row.get("period_candidate"),
                    "window_start_minute_candidate": row.get("window_start_minute_candidate"),
                    "window_end_minute_candidate": row.get("window_end_minute_candidate"),
                    "previous_activity_state": row.get("previous_activity_state"),
                    "current_activity_state": row.get("current_activity_state"),
                    "turnover_anchor_consequence_count": row.get("turnover_anchor_consequence_count"),
                    "recovery_anchor_consequence_count": row.get("recovery_anchor_consequence_count"),
                    "change_signal_count": row.get("change_signal_count"),
                }
                for row in turning_rows
            ],
            "denominators": [],
            "claim_ceiling": "TURNING_POINT_CANDIDATE_ONLY",
            "football_label_tr": "Kırılma anı adayları",
        })

    mechanism_variant_rows = (football_dynamics.get("mechanism_reading_variants") or {}).get("rows") or []
    if mechanism_variant_rows:
        specs.append({
            "chart_id": "chart:mechanism_reading_variants",
            "source_card_id": "football_dynamics:mechanism_reading_variants",
            "chart_type": "STACKED_BAR",
            "categories": [str(row.get("reading_variant_state")) for row in mechanism_variant_rows],
            "series": [
                {
                    "name": "nominal_chain_count",
                    "values": [int(row.get("nominal_chain_count") or 0) for row in mechanism_variant_rows],
                }
            ],
            "denominators": [
                {
                    "reading_variant_state": row.get("reading_variant_state"),
                    "eligible_nominal_chain_denominator": row.get("eligible_nominal_chain_denominator"),
                    "independence_admitted": row.get("independence_admitted"),
                }
                for row in mechanism_variant_rows
            ],
            "claim_ceiling": "MECHANISM_READING_VARIANT_ONLY",
            "football_label_tr": "Mekanizma okuma varyantları",
        })

    location_rows = (football_dynamics.get("player_action_location_candidates") or {}).get("rows") or []
    if location_rows:
        specs.append({
            "chart_id": "chart:player_action_locations",
            "source_card_id": "football_dynamics:player_action_location_candidates",
            "chart_type": "PITCH_SCATTER",
            "points": [
                {
                    "actor_identity_candidate_id": row.get("actor_identity_candidate_id"),
                    "label": row.get("actor_display_candidate"),
                    "x": row.get("median_action_x_candidate"),
                    "y": row.get("median_action_y_candidate"),
                    "recorded_coordinate_anchor_count": row.get("recorded_coordinate_anchor_count"),
                }
                for row in location_rows
            ],
            "denominators": [],
            "claim_ceiling": "RECORDED_ACTION_LOCATION_CANDIDATE_ONLY",
            "football_label_tr": "Oyuncu aksiyon bölgeleri",
        })

    for spec in specs:
        spec["render_ready"] = True
        spec["visual_strength_must_not_exceed_evidence_strength"] = True
        spec["percentages_emitted"] = False
        spec["frontend_may_invent_missing_values"] = False
        spec["frontend_may_infer_causality"] = False
        spec["frontend_may_connect_spatial_points_as_trajectory"] = False
        spec["chart_audit"] = {
            "what_it_measures": "declared candidate-unit counts from the source comparison card",
            "what_it_does_not_measure": [
                "football_quality",
                "causal_effect",
                "tactical_intention",
                "independent_recurrence_unless_explicitly_admitted",
            ],
            "denominator_rule": "use only explicit eligible denominators carried by the source rows",
            "observation_window": "match-local current invocation; finer window is encoded only when source rows declare it",
            "source_surface": "analyst_presentation_view_model comparative_views/comparison_cards derived from current invocation",
            "claim_ceiling": spec.get("claim_ceiling"),
            "uncertainty_note": "candidate/proxy/identity limitations remain binding after rendering",
        }

    return {
        "schema_version": "1.0",
        "state": "RENDER_READY",
        "chart_count": len(specs),
        "charts": specs,
        "render_contract": {
            "missing_value_policy": "DO_NOT_INTERPOLATE",
            "percentage_policy": "NO_PERCENTAGE_UNLESS_NUMERATOR_AND_ELIGIBLE_DENOMINATOR_ARE_EXPLICITLY_DEFINED",
            "label_policy": "PRESERVE_CANDIDATE_AND_PROXY_LANGUAGE",
            "color_semantics": "CLIENT_DEFINED_NON_EPISTEMIC_UNLESS_EXPLICITLY_CONTRACTED",
        },
    }

def _dashboard_manifest(
    match_story: dict[str, Any],
    six_phase_lens: dict[str, Any],
    comparison_cards: dict[str, Any],
    chart_render_pack: dict[str, Any],
    mechanism_cards: list[dict[str, Any]],
    player_cards: list[dict[str, Any]],
    traceback_index: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dashboard_id": "hpfa_match_analysis_dashboard_v1",
        "layout_mode": "ANALYST_FIRST_RESPONSIVE",
        "primary_question": "What happened, where/when is it visible, what can we safely say, and what remains unknown?",
        "regions": [
            {
                "region_id": "match_story_header",
                "priority": 1,
                "desktop": "TOP_FULL_WIDTH",
                "mobile": "TOP_STACK",
                "content_ref": "surface_data.match_story",
                "purpose": "3-5 mechanism target only when distinct admitted families exist",
            },
            {
                "region_id": "field_replay",
                "priority": 2,
                "desktop": "CENTER_LEFT_LARGE",
                "mobile": "SECOND_STACK",
                "content_ref": "surface_data.mechanism_cards[*].where_when + surface_data.observed_replay_cards",
                "visual_mode": "SCHEMATIC_PITCH_WITH_RECORDED_ANCHORS",
                "allowed_overlays": [
                    "recorded_coordinate_anchor_dot",
                    "episode_time_label",
                    "action_family_label",
                    "team_candidate_marker",
                    "reference_link_highlight",
                ],
                "blocked_overlays": [
                    "invented_ball_trajectory",
                    "invented_player_run",
                    "team_shape_polygon",
                    "pressure_geometry",
                    "pitch_control_surface",
                    "off_ball_role_path",
                ],
            },
            {
                "region_id": "six_phase_matrix",
                "priority": 3,
                "desktop": "RIGHT_RAIL_TOP",
                "mobile": "THIRD_STACK",
                "content_ref": "surface_data.six_phase_lens",
                "phase_slots": [item.get("phase") for item in six_phase_lens.get("phases") or []],
                "display_rule": "SHOW_PROXY_LENS_ONLY_AND_NOT_EVALUATED_EXPLICITLY",
            },
            {
                "region_id": "football_dynamics_panel",
                "priority": 4,
                "desktop": "CENTER_RIGHT_MIDDLE",
                "mobile": "FOURTH_STACK",
                "content_ref": "surface_data.football_dynamics + surface_data.chart_render_pack",
                "visual_mode": "RHYTHM_CONSEQUENCE_AND_ACTION_LOCATION_VIEWS",
                "football_questions": [
                    "Where did visible recorded-action activity rise or fall?",
                    "What visible consequence candidates followed recorded losses/recoveries?",
                    "Where were players' recorded actions concentrated?",
                ],
                "claim_ceiling": "EVENT_DERIVED_PRESENTATION_INTELLIGENCE_ONLY",
            },
            {
                "region_id": "match_timeline",
                "priority": 4,
                "desktop": "CENTER_LEFT_BELOW_FIELD",
                "mobile": "FOURTH_STACK",
                "content_ref": "surface_data.observed_replay_cards",
                "visual_mode": "PARTIAL_ORDER_SAFE_INTERVAL_STRIP",
                "same_timestamp_total_order_allowed": False,
            },
            {
                "region_id": "process_chain",
                "priority": 5,
                "desktop": "BOTTOM_LEFT",
                "mobile": "FIFTH_STACK",
                "content_ref": "surface_data.comparison_cards",
                "visual_mode": "COUNT_AND_CONSEQUENCE_CARDS_ONLY",
                "note": "No rate/share without explicit eligible denominator.",
            },
            {
                "region_id": "comparison_panel",
                "priority": 6,
                "desktop": "BOTTOM_CENTER",
                "mobile": "SIXTH_STACK",
                "content_ref": "surface_data.chart_render_pack",
                "chart_count": chart_render_pack.get("chart_count"),
                "render_state": chart_render_pack.get("state"),
            },
            {
                "region_id": "truth_limits_panel",
                "priority": 7,
                "desktop": "BOTTOM_RIGHT",
                "mobile": "SEVENTH_STACK",
                "content_ref": "closed_claims + unavailable_surfaces + graphability",
                "purpose": "Show what data supports and what current package cannot prove.",
            },
            {
                "region_id": "player_process_drawer",
                "priority": 8,
                "desktop": "RIGHT_DRAWER",
                "mobile": "DRILLDOWN_ROUTE",
                "content_ref": "surface_data.player_process_cards",
                "card_count": len(player_cards),
            },
            {
                "region_id": "evidence_drawer",
                "priority": 9,
                "desktop": "RIGHT_DRAWER_SECONDARY",
                "mobile": "DRILLDOWN_ROUTE",
                "content_ref": "surface_data.traceback_index",
                "traceback_scope": traceback_index.get("scope"),
            },
        ],
        "depth_model": {
            "principle": "SIMPLE_FIRST_VIEW_DEEPER_ON_DEMAND_TRACEABLE_TO_EVIDENCE",
            "layers": [
                {
                    "layer_id": "L1_MATCH_READ",
                    "analyst_time_horizon": "5_TO_10_SECONDS",
                    "question": "What are the few visible match stories worth attention?",
                    "surfaces": ["match_story_header", "six_phase_matrix", "comparison_panel"],
                    "content_rule": "compress_to_distinct_mechanism_families_and_visible_state_changes",
                    "must_show": ["safe_meaning", "uncertainty_marker"],
                    "must_not_show": ["raw_reference_ids", "full_counterevidence_graph", "dense_metric_tables"],
                },
                {
                    "layer_id": "L2_MECHANISM_READ",
                    "analyst_time_horizon": "30_TO_120_SECONDS",
                    "question": "How did the visible mechanism unfold, where/when, through which players and variants?",
                    "surfaces": ["field_replay", "football_dynamics_panel", "match_timeline", "process_chain", "player_process_drawer"],
                    "content_rule": "episode_process_variant_consequence_and_player_participation",
                    "must_show": ["where_when", "successful_failed_deviant_variant", "visible_consequence", "player_participation"],
                    "must_not_show": ["invented_trajectory", "off_ball_role_truth", "coach_intention"],
                },
                {
                    "layer_id": "L3_EVIDENCE_AUDIT",
                    "analyst_time_horizon": "ON_DEMAND",
                    "question": "Why is this claim allowed, what weakens it, and when should it be withdrawn?",
                    "surfaces": ["truth_limits_panel", "evidence_drawer", "counterevidence"],
                    "content_rule": "support_counterevidence_dependency_uncertainty_withdrawal_traceback",
                    "must_show": ["support", "counterevidence", "dependency_state", "uncertainty", "withdrawal_condition", "traceback"],
                    "must_not_show": ["confidence_inflation_from_volume", "absence_as_counterevidence", "model_output_as_fact"],
                },
            ],
            "drilldown_path": [
                "MATCH_STORY",
                "MECHANISM",
                "WHERE_WHEN",
                "VARIANT",
                "PLAYER_PARTICIPATION",
                "CONSEQUENCE",
                "COUNTEREVIDENCE",
                "EVIDENCE_TRACEBACK",
            ],
            "collapse_rule": "DETAIL_MAY_HIDE_UNTIL_REQUESTED_BUT_UNCERTAINTY_MAY_NOT_BE_HIDDEN",
            "empty_state_rule": "UNKNOWN_NOT_EVALUATED_AND_UNOBSERVABLE_MUST_REMAIN_VISIBLE",
        },
        "mobile_navigation": [
            "MATCH_STORY",
            "FIELD_REPLAY",
            "DYNAMICS",
            "SIX_PHASE",
            "COMPARISONS",
            "PLAYERS",
            "COUNTEREVIDENCE",
            "EVIDENCE",
        ],
        "desktop_navigation": {
            "left": ["MATCH_STORY", "FIELD_REPLAY", "TIMELINE"],
            "right": ["SIX_PHASE", "MECHANISM", "COUNTEREVIDENCE"],
            "bottom": ["COMPARISONS", "TRUTH_LIMITS"],
        },
        "visual_language": {
            "tone": "PROFESSIONAL_TECHNICAL_STAFF_BROADCAST",
            "information_density": "HIGH_BUT_PROGRESSIVELY_DISCLOSED",
            "pitch_is_primary_canvas": True,
            "decorative_match_photo_required": False,
            "color_may_encode_epistemic_strength": False,
            "candidate_proxy_language_must_remain_visible": True,
            "design_doctrine": {
                "CARAVAGGIO": "high_contrast_attention_hierarchy_without_decorative_darkness",
                "LEONARDO_DA_VINCI": "geometry_proportion_mathematical_structure_and_legible_system_drawing",
                "TESLA": "electric_energy_accents_and_dynamic_flow_without_visual_noise",
                "GIORDANO_BRUNO": "conceptual_sharpness_and_intellectual_courage",
                "EDUARDO_GALEANO": "human_scale_football_storytelling_without_sentimentality",
                "RAFFAELLO_SANZIO": "clear_compositional_focus_balance_and_positive_visual_order",
                "HIERONYMUS_BOSCH": "controlled_system_complexity_with_local_detail_and_global_order",
                "UMBERTO_ECO": "layered_meaning_progressive_disclosure_and_traceable_depth",
                "SAMUEL_BECKETT": "whitespace_restraint_silence_and_tension_where_information_is_absent",
            },
            "palette_principles": {
                "base": "dark_navy_black",
                "primary_accent": "electric_blue",
                "support_accent": "restrained_green",
                "warning_accent": "restrained_amber_or_red",
                "rule": "color_is_navigation_or_status_not_evidence_strength_unless_explicitly_contracted",
            },
            "composition_principles": [
                "strong_focus_before_detail",
                "geometry_before_decoration",
                "progressive_disclosure_before_screen_clutter",
                "empty_space_may_signal_unknown_or_unobserved",
                "visual_complexity_must_have_analyst_value",
                "literal_historical_iconography_is_not_required",
            ],
            "epistemic_visual_tokens": {
                "OBSERVED": {
                    "geometry": "sharp_edge_or_point",
                    "opacity": "high",
                    "meaning": "directly observed/admitted surface",
                },
                "CANDIDATE": {
                    "geometry": "soft_edge_or_faint_glow",
                    "opacity": "medium",
                    "meaning": "candidate/proxy signal only",
                },
                "UNCERTAIN": {
                    "geometry": "soft_boundary_or_halo",
                    "opacity": "medium_low",
                    "meaning": "uncertainty or unresolved boundary",
                },
                "COUNTEREVIDENCE": {
                    "geometry": "dashed_branch_or_fracture_marker",
                    "opacity": "high",
                    "meaning": "alternative explanation or weakening evidence",
                },
                "WITHDRAWN": {
                    "geometry": "dimmed_crack",
                    "opacity": "low",
                    "meaning": "withdrawn claim, not whole-model failure",
                },
                "MISSING_UNKNOWN": {
                    "geometry": "intentional_void_or_gap",
                    "opacity": "none",
                    "meaning": "missing/unknown, never evidence by absence",
                },
            },
            "epistemic_token_rule": "VISUAL_DRAMA_CANNOT_INCREASE_CLAIM_CAPACITY",
        },
        "operator_cognitive_doctrine": {
            "core": [
                "mechanism_over_scoreline",
                "evidence_over_rhetoric",
                "context_over_raw_count",
                "counterevidence_before_confidence",
                "uncertainty_must_be_visible",
                "deep_reasoning_simple_expression",
                "complex_systems_without_false_certainty",
            ],
            "preferred_experience": [
                "dense_but_ordered",
                "direct_and_non_theatrical",
                "analyst_action_before_decoration",
                "traceable_claims",
                "clear_unknowns",
            ],
            "avoid": [
                "surface_level_commentary",
                "fan_style_judgment",
                "empty_enthusiasm",
                "ornamental_complexity",
                "unverified_claims",
                "blind_composite_scores",
                "aesthetic_inflation_of_evidence",
            ],
        },
        "interaction_rules": {
            "tap_or_click_may_filter_view": True,
            "interaction_may_strengthen_evidence": False,
            "client_may_create_new_football_semantics": False,
            "every_claim_card_must_offer_traceback": True,
        },
        "claim_ceiling": "PRESENTATION_LAYOUT_ONLY_NO_NEW_EVIDENCE",
        "mechanism_count": len(mechanism_cards),
        "match_story_state": match_story.get("state"),
    }

def _graphability_manifest(
    surfaces: dict[str, Any],
    episode_cards: list[dict[str, Any]],
    phase_cards: list[dict[str, Any]],
    six_phase_lens: dict[str, Any],
    mechanism_cards: list[dict[str, Any]],
    player_cards: list[dict[str, Any]],
    counter_cards: list[dict[str, Any]],
    traceback_index: dict[str, Any],
    broadcast_candidates: list[str],
    broadcast_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    specs: dict[str, Any] = {}

    specs["match_story"] = {
        "state": "GRAPHABLE" if mechanism_cards else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "HORIZONTAL_BAR",
        "data_semantics": "nominal_chain_count_by_distinct_mechanism_family",
        "data": [
            {
                "mechanism_candidate_id": card.get("mechanism_candidate_id"),
                "label": card.get("display_tr"),
                "nominal_chain_count": card.get("nominal_chain_count"),
            }
            for card in mechanism_cards
        ],
        "forbidden_visual_inference": [
            "bar_length_is_evidence_strength",
            "bar_length_is_independent_recurrence",
            "bar_length_is_probability",
        ],
    }

    specs["mechanism_cards"] = {
        "state": "GRAPHABLE" if mechanism_cards else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "STACKED_BAR",
        "data_semantics": "defeasible_state_distribution_within_nominal_chains",
        "data": [
            {
                "mechanism_candidate_id": card.get("mechanism_candidate_id"),
                "display_tr": card.get("display_tr"),
                **{str(k): v for k, v in (card.get("defeasible_state_counts") or {}).items()},
            }
            for card in mechanism_cards
        ],
        "where_when_graphs": {
            "when": {
                "preferred_representation": "TIME_ANCHOR_STRIP",
                "data_semantics": "context_window_start_anchors_by_period",
                "delivery_mode": "LAZY_REFERENCE_JOIN",
                "sample_data_ref": "surface_data.mechanism_cards[*].where_when.time_anchor_sample",
                "lazy_source_ref": "surface_data.mechanism_cards[*].where_when.lazy_graph_sources.when",
                "anchor_counts": [
                    {
                        "mechanism_candidate_id": card.get("mechanism_candidate_id"),
                        "time_anchor_count": (card.get("where_when") or {}).get("time_anchor_count", 0),
                    }
                    for card in mechanism_cards
                ],
                "forbidden_visual_inference": [
                    "time_anchor_is_episode_duration",
                    "time_anchor_order_is_total_order_when_same_timestamp",
                    "time_density_is_mechanism_strength",
                ],
            },
            "where": {
                "preferred_representation": "COORDINATE_ANCHOR_SCATTER",
                "data_semantics": "recorded_trace_coordinate_anchors_reached_through_visible_sequence_candidate_membership_refs_not_sequence_truth",
                "delivery_mode": "LAZY_REFERENCE_JOIN",
                "sample_data_ref": "surface_data.mechanism_cards[*].where_when.spatial_anchor_sample",
                "lazy_source_ref": "surface_data.mechanism_cards[*].where_when.lazy_graph_sources.where",
                "anchor_counts": [
                    {
                        "mechanism_candidate_id": card.get("mechanism_candidate_id"),
                        "spatial_anchor_count": (card.get("where_when") or {}).get("spatial_anchor_count", 0),
                    }
                    for card in mechanism_cards
                ],
                "forbidden_visual_inference": [
                    "anchor_connection_is_ball_trajectory",
                    "anchor_distribution_is_team_shape",
                    "anchor_density_is_pitch_control",
                    "anchor_position_is_off_ball_positioning_truth",
                ],
            },
        },
        "forbidden_visual_inference": [
            "stack_share_is_probability",
            "supported_count_is_independent_support_count",
            "mechanism_is_causal_truth",
        ],
    }

    specs["player_process_cards"] = {
        "state": "GRAPHABLE" if player_cards else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "GROUPED_OR_SMALL_MULTIPLE_BAR",
        "data_semantics": "recorded_action_family_candidate_counts_by_match_local_actor_candidate",
        "data": [
            {
                "actor_identity_candidate_id": card.get("actor_identity_candidate_id"),
                "actor_display_candidate": card.get("actor_display_candidate"),
                "team_normalized_key": card.get("team_normalized_key"),
                "trace_candidate_count": card.get("trace_candidate_count"),
                "action_family_candidate_counts": card.get("action_family_candidate_counts") or {},
            }
            for card in player_cards
        ],
        "forbidden_visual_inference": [
            "trace_volume_is_player_quality",
            "trace_volume_is_physical_action_count",
            "action_family_distribution_is_off_ball_role",
        ],
    }

    specs["observed_replay"] = {
        "state": "GRAPHABLE" if episode_cards else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "INTERVAL_STRIP_WITH_UNORDERED_SAME_TIME_BUNDLES",
        "data_semantics": "episode_candidate_time_intervals_and_visible_action_family_distribution",
        "data": [
            {
                "episode_candidate_id": card.get("id"),
                "period_candidate": card.get("period_candidate"),
                "start_second_candidate": card.get("start_second_candidate"),
                "end_second_candidate": card.get("end_second_candidate"),
                "action_family_distribution": card.get("action_family_distribution") or {},
                "status": card.get("status"),
            }
            for card in episode_cards
        ],
        "forbidden_visual_inference": [
            "interval_is_possession_truth",
            "interval_is_tactical_episode_truth",
            "same_timestamp_creates_total_order",
            "connection_line_is_ball_trajectory",
        ],
    }

    phase_rows = six_phase_lens.get("phases") or []
    specs["six_phase_match_view"] = {
        "state": "GRAPHABLE" if phase_rows else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "SIX_SLOT_STATUS_BAR_OR_MATRIX",
        "data_semantics": "canonical_six_phase_slots_with_proxy_lens_or_not_evaluated_status",
        "data": phase_rows,
        "forbidden_visual_inference": [
            "candidate_label_is_canonical_six_phase_truth",
            "frequency_is_time_share_without_duration_denominator",
            "frequency_is_tactical_dominance",
        ],
    }

    counter_counts: dict[str, int] = {}
    withdrawal_counts: dict[str, int] = {}
    for card in counter_cards:
        for value in card.get("counter_scenarios") or []:
            key = str(value)
            counter_counts[key] = counter_counts.get(key, 0) + 1
        for value in card.get("withdrawal_conditions") or []:
            key = str(value)
            withdrawal_counts[key] = withdrawal_counts.get(key, 0) + 1
    specs["counterevidence_cards"] = {
        "state": "GRAPHABLE" if counter_counts or withdrawal_counts else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "HORIZONTAL_BAR",
        "data_semantics": "nominal_counter_scenario_and_withdrawal_condition_mentions",
        "data": {
            "counter_scenarios": [{"id": k, "nominal_mentions": v} for k, v in sorted(counter_counts.items())],
            "withdrawal_conditions": [{"id": k, "nominal_mentions": v} for k, v in sorted(withdrawal_counts.items())],
        },
        "forbidden_visual_inference": [
            "nominal_mentions_are_independent_counterevidence",
            "absence_of_counterevidence_is_support",
        ],
    }

    episode_nodes = len(traceback_index.get("episodes") or {})
    mechanism_nodes = len(traceback_index.get("mechanisms") or {})
    player_nodes = len(traceback_index.get("players") or {})
    specs["traceback_evidence_drawer"] = {
        "state": "GRAPHABLE" if episode_nodes or mechanism_nodes or player_nodes else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "NODE_LINK_OR_HIERARCHICAL_DRILLDOWN",
        "data_semantics": "reference_graph_navigation_counts",
        "data": [
            {"node_family": "episode", "node_count": episode_nodes},
            {"node_family": "mechanism", "node_count": mechanism_nodes},
            {"node_family": "player", "node_count": player_nodes},
        ],
        "forbidden_visual_inference": [
            "graph_degree_is_evidence_strength",
            "reference_density_is_truth_strength",
            "edge_is_causal_relation",
        ],
    }

    specs["broadcast_summary"] = {
        "state": "GRAPHABLE" if broadcast_groups else "UNGRAPHABLE_WITH_CURRENT_DATA",
        "preferred_representation": "STACKED_OR_GROUPED_BAR_BY_FAMILY_AND_DEFEASIBLE_STATE",
        "data_semantics": "broadcast_candidate_groups_after_deterministic_family_state_compression",
        "data": broadcast_groups,
        "forbidden_visual_inference": [
            "nominal_candidate_count_is_match_importance",
            "nominal_candidate_count_is_evidence_strength",
            "supported_group_is_publication_permission",
            "representative_sentence_is_final_broadcast_copy",
        ],
    }

    state_counts: dict[str, int] = {}
    for value in surfaces.values():
        state = str(value.get("state") or "UNKNOWN")
        state_counts[state] = state_counts.get(state, 0) + 1
    specs["unknown_unobservable_register"] = {
        "state": "GRAPHABLE",
        "preferred_representation": "BAR",
        "data_semantics": "analyst_surface_epistemic_state_counts",
        "data": [{"state": k, "surface_count": v} for k, v in sorted(state_counts.items())],
        "forbidden_visual_inference": [
            "available_surface_count_is_product_quality_score",
            "degraded_surface_count_is football weakness",
        ],
    }

    specs["comparative_views"] = {
        "state": "GRAPHABLE",
        "preferred_representations": {
            "defeasible_state_comparison": "STACKED_BAR_WITH_EXPLICIT_DENOMINATOR",
            "zone_mentions_by_period": "GROUPED_BAR_COUNTS_ONLY",
            "channel_mentions_by_period": "GROUPED_BAR_COUNTS_ONLY",
            "period_mechanism_comparison": "GROUPED_BAR_WITH_ELIGIBLE_DENOMINATORS",
            "team_coordinate_comparison": "GROUPED_BAR_OR_SMALL_MULTIPLE_SCATTER_WITH_ELIGIBLE_DENOMINATOR",
        },
        "data_semantics": "candidate_unit_comparisons_with_explicit_denominator_or_preview_only_state",
        "data_ref": "surface_data.comparative_views",
        "forbidden_visual_inference": [
            "nominal_anchor_count_as_independent_recurrence",
            "count_difference_as_rate_without_denominator",
            "zone_or_channel_mentions_as_time_share",
            "team_candidate_as_validated_identity",
            "nominal_chain_count_as_independent_recurrence",
            "count_difference_as_causal_effect",
        ],
    }

    specs["analyst_report"] = {
        "state": "GRAPHABLE_AS_COMPANION_ONLY",
        "preferred_representation": "NO_DIRECT_REPORT_PROSE_CHART",
        "data_semantics": "report prose itself is not chart data; use linked mechanism/player/phase/evidence specs",
        "data": [],
        "forbidden_visual_inference": [
            "natural_language_frequency_is_evidence_strength",
        ],
    }

    return {
        "policy": "EVERY_ANALYST_CONSTRUCT_MUST_DECLARE_GRAPHABILITY",
        "fallback_state": "UNGRAPHABLE_WITH_CURRENT_DATA",
        "visual_strength_must_not_exceed_evidence_strength": True,
        "specs": specs,
    }

def _closed_claims(full_spine: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "tracking_truth": False,
        "video_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "causal_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "source_status": full_spine.get("status", "UNKNOWN"),
    }

def build_view_model(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root)
    full = _load(root / "active_match_full_spine_v1.json")
    episode = _load(root / "analyst_episode_locator_lite_v1.json")
    declared_raw = full.get("current_invocation_artifacts") if isinstance(full, dict) else []
    declared = {
        Path(str(item)).name
        for item in (declared_raw if isinstance(declared_raw, list) else [])
    }

    artifacts = [
        _artifact(root, "active_match_full_spine_v1.json"),
        _artifact(root, "HPFA_ANALYST_REPORT.txt"),
        _artifact(root, "analyst_episode_locator_lite_v1.json", current="analyst_episode_locator_lite_v1.json" in declared),
        _artifact(root, "match_local_identity_candidates_lite_v1.json", current="match_local_identity_candidates_lite_v1.json" in declared),
        _artifact(root, "trackable_action_trace_candidates_lite_v1.json", current="trackable_action_trace_candidates_lite_v1.json" in declared),
        _artifact(root, "trackable_action_consequence_candidates_lite_v1.json", current="trackable_action_consequence_candidates_lite_v1.json" in declared),
        _artifact(root, "visible_action_sequence_candidates_lite_v1.json", current="visible_action_sequence_candidates_lite_v1.json" in declared),
    ]
    available = {item["name"] for item in artifacts if item["state"] == "AVAILABLE"}
    episode_available = "analyst_episode_locator_lite_v1.json" in available
    report_available = "HPFA_ANALYST_REPORT.txt" in available
    episode_cards = _episode_cards(episode) if episode_available else []
    phase_cards = _phase_cards(full)
    counter_cards = _counterevidence_cards(full)
    mechanism_where_when = _mechanism_where_when(root, full, declared)
    mechanism_cards = _mechanism_cards(full)
    for card in mechanism_cards:
        card["where_when"] = mechanism_where_when.get(card["mechanism_candidate_id"], {
            "time_anchors": [],
            "spatial_anchors": [],
            "claim_ceiling": "MECHANISM_WHERE_WHEN_REFERENCE_BINDING_ONLY",
        })
    match_story = _match_story(mechanism_cards)
    player_process_cards = _player_process_cards(root, declared)
    traceback_index = _traceback_index(root, full, episode, declared)
    broadcast_candidates = _broadcast_candidates(full)
    broadcast_groups = _broadcast_groups(full)
    six_phase_lens = _six_phase_lens(phase_cards)
    comparative_views = _comparative_views(
        mechanism_cards=mechanism_cards,
        episode_cards=episode_cards,
        player_cards=player_process_cards,
    )
    comparison_cards = _comparison_cards(comparative_views)
    football_dynamics = _football_dynamics_surface(
        root=root,
        declared=declared,
        player_cards=player_process_cards,
        mechanism_cards=mechanism_cards,
    )
    chart_render_pack = _chart_render_pack(
        comparison_cards,
        football_dynamics,
    )
    dashboard_manifest = _dashboard_manifest(
        match_story=match_story,
        six_phase_lens=six_phase_lens,
        comparison_cards=comparison_cards,
        chart_render_pack=chart_render_pack,
        mechanism_cards=mechanism_cards,
        player_cards=player_process_cards,
        traceback_index=traceback_index,
    )
    report_text = ""
    report_path = root / "HPFA_ANALYST_REPORT.txt"
    if report_available:
        report_text = report_path.read_text(encoding="utf-8")

    surfaces: dict[str, Any] = {}
    surfaces["analyst_report"] = _surface(
        "AVAILABLE" if report_available else "MISSING",
        ["HPFA_ANALYST_REPORT.txt"],
        "Current-invocation analyst report artifact only.",
        "analyst_report_candidate_only",
    )
    surfaces["match_story"] = _surface(
        "DEGRADED" if mechanism_cards else "NOT_EVALUATED",
        ["active_match_full_spine_v1.json"] if mechanism_cards else [],
        "Distinct admitted mechanism families are compressed without forcing 3-5 output when fewer families exist.",
        "match_story_presentation_candidate_only",
    )
    surfaces["six_phase_match_view"] = _surface(
        "DEGRADED" if phase_cards else "NOT_EVALUATED",
        ["active_match_full_spine_v1.json"] if phase_cards else [],
        "Canonical six-phase slots are shown only as PROXY_LENS_ONLY or NOT_EVALUATED; no slot is promoted to phase truth.",
        "six_phase_presentation_proxy_lens_only",
    )

    surfaces["mechanism_cards"] = _surface(
        "AVAILABLE" if mechanism_cards else "NOT_EVALUATED",
        ["active_match_full_spine_v1.json"] if mechanism_cards else [],
        "Cards group existing argument/mechanism families; nominal counts never become independent support.",
        "mechanism_family_presentation_candidate_only",
    )
    surfaces["player_process_cards"] = _surface(
        "DEGRADED" if player_process_cards else "NOT_EVALUATED",
        [
            "match_local_identity_candidates_lite_v1.json",
            "trackable_action_trace_candidates_lite_v1.json",
            "trackable_action_consequence_candidates_lite_v1.json",
        ] if player_process_cards else [],
        "Recorded-action participation only; trace volume is not physical action count or off-ball tactical role.",
        "recorded_action_participation_candidate_only",
    )
    surfaces["counterevidence_cards"] = _surface(
        "AVAILABLE" if counter_cards else "NOT_EVALUATED",
        ["active_match_full_spine_v1.json"] if counter_cards else [],
        "Explicit counter-scenarios, withdrawal conditions and contradiction refs only; absence is never counterevidence.",
        "argument_counterevidence_candidate_only",
    )
    surfaces["observed_replay"] = _surface(
        "DEGRADED" if episode_available else "MISSING",
        ["analyst_episode_locator_lite_v1.json"] if episode_available else [],
        "Episode locator can support navigation only; no trajectory, off-ball movement or total-order interpolation.",
        "recorded_actions_only_candidate_navigation",
    )
    traceback_available = bool(
        traceback_index.get("episodes")
        or traceback_index.get("mechanisms")
        or traceback_index.get("players")
    )
    surfaces["traceback_evidence_drawer"] = _surface(
        "AVAILABLE" if traceback_available else "MISSING",
        [
            "active_match_full_spine_v1.json",
            "analyst_episode_locator_lite_v1.json",
            "trackable_action_trace_candidates_lite_v1.json",
            "trackable_action_consequence_candidates_lite_v1.json",
        ] if traceback_available else [],
        "Reference-ID deep links connect analyst cards back to episode/context/row-nucleus, argument/packet, trace and consequence candidates.",
        "traceback_reference_index_only",
    )
    surfaces["broadcast_summary"] = _surface(
        "DEGRADED" if broadcast_candidates else "NOT_EVALUATED",
        ["active_match_full_spine_v1.json"] if broadcast_candidates else [],
        "Safe-sentence candidates are compressed deterministically by argument family and defeasible state; representative copy is not final broadcast publication.",
        "broadcast_compression_candidate_only",
    )
    surfaces["unknown_unobservable_register"] = _surface(
        "AVAILABLE",
        ["active_match_full_spine_v1.json"] if full else [],
        "Closed claims and missing/degraded surfaces are explicit product data.",
        "epistemic_status_only",
    )

    if not full:
        overall = "FAIL_CLOSED"
    elif any(item["state"] == "MISSING" for item in surfaces.values() if item is not surfaces["match_story"]):
        overall = "DEGRADED"
    else:
        overall = "REVIEW_REQUIRED"

    graphability = _graphability_manifest(
        surfaces=surfaces,
        episode_cards=episode_cards,
        phase_cards=phase_cards,
        six_phase_lens=six_phase_lens,
        mechanism_cards=mechanism_cards,
        player_cards=player_process_cards,
        counter_cards=counter_cards,
        traceback_index=traceback_index,
        broadcast_candidates=broadcast_candidates,
        broadcast_groups=broadcast_groups,
    )

    unavailable = {
        key: value["state"]
        for key, value in surfaces.items()
        if value["state"] in {"MISSING", "NOT_EVALUATED", "DEGRADED"}
    }
    surface_data = {
        "analyst_report_text": report_text,
        "observed_replay_cards": episode_cards,
        "phase_activity_candidates": phase_cards,
        "six_phase_lens": six_phase_lens,
        "mechanism_cards": mechanism_cards,
        "mechanism_where_when": mechanism_where_when,
        "match_story": match_story,
        "player_process_cards": player_process_cards,
        "traceback_index": traceback_index,
        "graphability": graphability,
        "counterevidence_cards": counter_cards,
        "broadcast_sentence_candidates": broadcast_candidates,
        "broadcast_groups": broadcast_groups,
        "comparative_views": comparative_views,
        "comparison_cards": comparison_cards,
        "football_dynamics": football_dynamics,
        "chart_render_pack": chart_render_pack,
        "dashboard_manifest": dashboard_manifest,
        "unknown_unobservable_register": {
            "surface_gaps": unavailable,
            "review_hits": list(full.get("review_hits") or []),
            "hard_block_hits": list(full.get("hard_block_hits") or []),
            "closed_claims": _closed_claims(full),
        },
    }

    return {
        "module_id": MODULE_ID,
        "schema_version": SCHEMA_VERSION,
        "status": overall,
        "decision": "PRESENTATION_VIEW_MODEL_BUILT" if full else "UPSTREAM_FULL_SPINE_MISSING",
        "presentation_role": "THIN_CLIENT_INPUT_ONLY",
        "recorded_actions_only": True,
        "visual_strength_must_not_exceed_evidence_strength": True,
        "surfaces": surfaces,
        "surface_data": surface_data,
        "artifact_provenance": artifacts,
        "closed_claims": _closed_claims(full),
        "interaction_provenance_may_affect_evidence": False,
        "client_may_create_new_football_semantics": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

def write_view_model(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    payload = build_view_model(root)
    (root / OUTPUT_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return payload
