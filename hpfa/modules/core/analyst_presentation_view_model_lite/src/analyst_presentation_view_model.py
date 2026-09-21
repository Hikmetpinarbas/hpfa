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
    ]
    available = {item["name"] for item in artifacts if item["state"] == "AVAILABLE"}
    episode_available = "analyst_episode_locator_lite_v1.json" in available
    report_available = "HPFA_ANALYST_REPORT.txt" in available
    episode_cards = _episode_cards(episode) if episode_available else []
    phase_cards = _phase_cards(full)
    counter_cards = _counterevidence_cards(full)
    mechanism_cards = _mechanism_cards(full)
    match_story = _match_story(mechanism_cards)
    player_process_cards = _player_process_cards(root, declared)
    traceback_index = _traceback_index(root, full, episode, declared)
    broadcast_candidates = _broadcast_candidates(full)
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
        "Phase-activity candidates are exposed without promotion to canonical six-phase truth.",
        "phase_candidate_only",
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
        "Safe-sentence candidate pool is exposed; editorial selection/compression is not production broadcast truth.",
        "safe_sentence_candidate_pool_only",
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

    unavailable = {
        key: value["state"]
        for key, value in surfaces.items()
        if value["state"] in {"MISSING", "NOT_EVALUATED", "DEGRADED"}
    }
    surface_data = {
        "analyst_report_text": report_text,
        "observed_replay_cards": episode_cards,
        "phase_activity_candidates": phase_cards,
        "mechanism_cards": mechanism_cards,
        "match_story": match_story,
        "player_process_cards": player_process_cards,
        "traceback_index": traceback_index,
        "counterevidence_cards": counter_cards,
        "broadcast_sentence_candidates": broadcast_candidates,
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
