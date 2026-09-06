from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from typing import Any


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number_key(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except (TypeError, ValueError):
        return text


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _core_key(bundle: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(bundle.get("match_surface_binding_id")),
        _clean(bundle.get("source_role")),
        _clean(bundle.get("team_identity_candidate_id")),
        _clean(bundle.get("actor_identity_candidate_id")),
        _clean(bundle.get("period_candidate")),
        _clean(bundle.get("start_candidate")),
        _clean(bundle.get("end_candidate")),
        _clean(bundle.get("pos_x_candidate")),
        _clean(bundle.get("pos_y_candidate")),
    )


def _interaction_core(bundle: dict[str, Any]) -> tuple[str, ...]:
    """Provider-annotation core only; never physical-position or event-identity truth."""
    return (
        _clean(bundle.get("match_surface_binding_id")),
        _clean(bundle.get("period_candidate")),
        _number_key(bundle.get("start_candidate")),
        _number_key(bundle.get("end_candidate")),
        _number_key(bundle.get("pos_x_candidate")),
        _number_key(bundle.get("pos_y_candidate")),
    )


def _goalkeeper_context_bundle_eligible(bundle: dict[str, Any]) -> bool:
    """Admit only an already-PASS goalkeeper surface as contextual object view.

    This never makes the goalkeeper a participant in occurrence admission and never
    creates an independent support vote or event instance.
    """
    if _clean(bundle.get("source_role")) != "GOALKEEPER_SURFACE_CANDIDATE":
        return False
    if _clean(bundle.get("bundle_status")) != "PASS":
        return False
    if not _clean(bundle.get("team_identity_candidate_id")) or not _clean(bundle.get("actor_identity_candidate_id")):
        return False
    if not _clean(bundle.get("period_candidate")):
        return False
    if any(_number_key(bundle.get(field)) == "" for field in ("start_candidate", "end_candidate", "pos_x_candidate", "pos_y_candidate")):
        return False
    if _clean(bundle.get("coordinate_evidence_status")) != "COORDINATE_PRESENT":
        return False
    if bundle.get("cross_role_fusion_allowed") is True:
        return False
    if bundle.get("validated_event_identity") is True or bundle.get("event_instance_allowed") is True:
        return False
    if bundle.get("canonical_event_count") not in {None, "UNKNOWN"}:
        return False
    return True


def _explicit_occurrence_trace(
    rows: list[dict[str, Any]],
    occurrence_by_bundle: dict[str, set[str]],
) -> dict[str, Any]:
    rows = sorted(rows, key=lambda row: _clean(row.get("action_bundle_candidate_id")))
    first = rows[0]
    bundle_ids = sorted(_clean(row.get("action_bundle_candidate_id")) for row in rows)
    occurrence_ids = sorted(
        {
            occurrence_id
            for bundle_id in bundle_ids
            for occurrence_id in occurrence_by_bundle.get(bundle_id, set())
        }
    )
    families = sorted(
        {
            _clean(row.get("action_family_candidate"))
            for row in rows
            if _clean(row.get("action_family_candidate"))
        }
    )
    evidence_ids = sorted(
        {
            _clean(value)
            for row in rows
            for value in row.get("supporting_evidence_atom_ids") or []
            if _clean(value)
        }
    )
    provider_row_ids = sorted(
        {
            _clean(value)
            for row in rows
            for value in row.get("provider_row_id_candidates") or []
            if _clean(value)
        }
    )
    raw_labels = sorted(
        {
            _clean(value)
            for row in rows
            for value in row.get("raw_labels") or []
            if _clean(value)
        }
    )
    normalized_labels = sorted(
        {
            _clean(value)
            for row in rows
            for value in row.get("normalized_labels") or []
            if _clean(value)
        }
    )
    return {
        "trackable_action_trace_candidate_id": "tat_occ_" + _digest(_core_key(first), bundle_ids, occurrence_ids)[:24],
        "match_surface_binding_id": first.get("match_surface_binding_id"),
        "source_role": first.get("source_role"),
        "team_identity_candidate_id": first.get("team_identity_candidate_id"),
        "actor_identity_candidate_id": first.get("actor_identity_candidate_id"),
        "period_candidate": first.get("period_candidate"),
        "start_candidate": first.get("start_candidate"),
        "end_candidate": first.get("end_candidate"),
        "pos_x_candidate": first.get("pos_x_candidate"),
        "pos_y_candidate": first.get("pos_y_candidate"),
        "coordinate_evidence_status": first.get("coordinate_evidence_status"),
        "action_family_candidates": families,
        "selected_action_bundle_candidate_ids": bundle_ids,
        "supporting_relation_candidate_ids": [],
        "reflection_context_action_bundle_candidate_ids": [],
        "supporting_taxonomy_record_ids": [],
        "supporting_evidence_atom_ids": evidence_ids,
        "reflection_evidence_atom_ids": [],
        "provider_row_id_candidates": provider_row_ids,
        "raw_labels": raw_labels,
        "normalized_labels": normalized_labels,
        "primary_source_lineage_records": [],
        "reflection_source_lineage_records": [],
        "selection_bases": ["EXPLICIT_ADMITTED_OCCURRENCE_REVIEW_BUNDLE_BINDING"],
        "same_surface_multi_family_grouping_candidate": len(families) > 1,
        "relation_support_visible": False,
        "team_reflection_context_visible": False,
        "supporting_action_occurrence_candidate_ids": occurrence_ids,
        "occurrence_backed_trace_candidate": True,
        "occurrence_binding_scope": "EXPLICIT_ADMITTED_BUNDLE_ONLY",
        "occurrence_binding_preserves_taxonomy_review_state": True,
        "occurrence_binding_is_event_truth": False,
        "occurrence_binding_changes_upstream_taxonomy_truth": False,
        "trace_count_is_physical_action_count": False,
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "reflection_context_is_event_equivalence_truth": False,
        "final_double_count_suppression_admitted": False,
        "count_value_output_allowed": False,
        "consequence_classification_allowed": False,
        "sequence_link_allowed": False,
        "same_time_order_truth_admitted": False,
        "source_row_order_is_temporal_truth": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "TRACKABLE_ACTION_TRACE_CANDIDATE_ONLY",
    }


def build_occurrence_aware_trace_payload(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    occurrence_payload: dict[str, Any],
    trace_builder,
) -> dict[str, Any]:
    """Bind existing traces to admitted occurrences without creating event truth.

    Participant identity remains owned by occurrence admission. A PASS goalkeeper
    surface may be attached only as an exact-core, same-side contextual object view;
    it cannot create or complete an occurrence and cannot add independent support.
    """
    action_copy = copy.deepcopy(action_payload)
    taxonomy_copy = copy.deepcopy(taxonomy_payload)
    relation_copy = copy.deepcopy(relation_payload)
    evidence_copy = copy.deepcopy(evidence_payload)

    occurrence_candidates = [
        row for row in (occurrence_payload.get("action_occurrence_candidates") or []) if isinstance(row, dict)
    ]
    occurrence_by_bundle: dict[str, set[str]] = defaultdict(set)
    occurrence_meta: dict[str, dict[str, Any]] = {}
    explicitly_admitted_review_bundle_ids: set[str] = set()

    for candidate in occurrence_candidates:
        occurrence_id = _clean(candidate.get("action_occurrence_candidate_id"))
        if not occurrence_id:
            continue
        occurrence_meta[occurrence_id] = candidate
        for raw_bundle_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = _clean(raw_bundle_id)
            if bundle_id:
                occurrence_by_bundle[bundle_id].add(occurrence_id)
        for provenance in candidate.get("conditional_review_passthrough_provenance") or []:
            if not isinstance(provenance, dict):
                continue
            for raw_bundle_id in provenance.get("supporting_action_bundle_candidate_ids") or []:
                bundle_id = _clean(raw_bundle_id)
                if bundle_id:
                    explicitly_admitted_review_bundle_ids.add(bundle_id)

    payload = trace_builder(action_copy, taxonomy_copy, relation_copy, evidence_copy)
    traces = payload.get("trackable_action_trace_candidates") or []
    if not isinstance(traces, list):
        traces = []
        payload["trackable_action_trace_candidates"] = traces

    existing_bundle_ids = {
        _clean(bundle_id)
        for trace in traces
        if isinstance(trace, dict)
        for bundle_id in trace.get("selected_action_bundle_candidate_ids") or []
        if _clean(bundle_id)
    }
    action_by_id = {
        _clean(bundle.get("action_bundle_candidate_id")): bundle
        for bundle in action_copy.get("action_bundle_candidates") or []
        if isinstance(bundle, dict) and _clean(bundle.get("action_bundle_candidate_id"))
    }

    occurrence_goalkeeper_context_bundle_refs: dict[str, set[str]] = defaultdict(set)
    for occurrence_id, candidate in occurrence_meta.items():
        participant_bundles = [
            action_by_id[bundle_id]
            for bundle_id in (_clean(value) for value in (candidate.get("supporting_action_bundle_candidate_ids") or []))
            if bundle_id in action_by_id
        ]
        participant_cores = {_interaction_core(bundle) for bundle in participant_bundles}
        if len(participant_cores) != 1:
            continue
        interaction_core = next(iter(participant_cores))
        admitted_teams = {
            value
            for value in (
                _clean(candidate.get("team_identity_candidate_id")),
                _clean(candidate.get("opponent_team_identity_candidate_id")),
            )
            if value
        }
        for bundle_id, bundle in action_by_id.items():
            if not _goalkeeper_context_bundle_eligible(bundle):
                continue
            if _clean(bundle.get("team_identity_candidate_id")) not in admitted_teams:
                continue
            if _interaction_core(bundle) != interaction_core:
                continue
            occurrence_by_bundle[bundle_id].add(occurrence_id)
            occurrence_goalkeeper_context_bundle_refs[occurrence_id].add(bundle_id)

    missing_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for bundle_id in sorted(explicitly_admitted_review_bundle_ids):
        if bundle_id in existing_bundle_ids:
            continue
        bundle = action_by_id.get(bundle_id)
        if not bundle:
            continue
        if _clean(bundle.get("bundle_status")) != "REVIEW_REQUIRED":
            continue
        if bundle_id not in occurrence_by_bundle:
            continue
        if not _clean(bundle.get("actor_identity_candidate_id")):
            continue
        missing_groups[_core_key(bundle)].append(bundle)

    appended_trace_count = 0
    for rows in missing_groups.values():
        trace = _explicit_occurrence_trace(rows, occurrence_by_bundle)
        traces.append(trace)
        appended_trace_count += 1

    for trace in traces:
        if not isinstance(trace, dict):
            continue
        if "supporting_action_occurrence_candidate_ids" not in trace:
            supporting_occurrence_ids: set[str] = set()
            selected_bundle_ids = {
                _clean(raw_bundle_id)
                for raw_bundle_id in trace.get("selected_action_bundle_candidate_ids") or []
                if _clean(raw_bundle_id)
            }
            for bundle_id in selected_bundle_ids:
                supporting_occurrence_ids.update(occurrence_by_bundle.get(bundle_id, set()))
            trace["supporting_action_occurrence_candidate_ids"] = sorted(supporting_occurrence_ids)
            trace["occurrence_backed_trace_candidate"] = bool(supporting_occurrence_ids)
            goalkeeper_context = any(
                bundle_id in occurrence_goalkeeper_context_bundle_refs.get(occurrence_id, set())
                for bundle_id in selected_bundle_ids
                for occurrence_id in supporting_occurrence_ids
            )
            trace["occurrence_binding_scope"] = (
                "EXACT_CORE_TEAM_GOALKEEPER_CONTEXT_ONLY"
                if goalkeeper_context
                else ("EXISTING_TRACE_OCCURRENCE_ANNOTATION" if supporting_occurrence_ids else "NO_OCCURRENCE_BINDING")
            )
            trace["occurrence_binding_preserves_taxonomy_review_state"] = True
            trace["occurrence_binding_is_event_truth"] = False
            trace["occurrence_binding_changes_upstream_taxonomy_truth"] = False
            trace["goalkeeper_context_binding_is_occurrence_participant_truth"] = False

    payload["trackable_action_trace_candidate_count"] = len(traces)

    occurrence_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_actor_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_opponent_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_trace_refs: dict[str, set[str]] = defaultdict(set)
    occurrence_player_refs: dict[str, set[str]] = defaultdict(set)
    occurrence_goalkeeper_refs: dict[str, set[str]] = defaultdict(set)
    occurrence_team_refs: dict[str, set[str]] = defaultdict(set)
    occurrence_relation_types: dict[str, set[str]] = defaultdict(set)
    occurrence_reflection_bundle_refs: dict[str, set[str]] = defaultdict(set)
    occurrence_bound_trace_count = 0
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        ids = [
            _clean(value)
            for value in trace.get("supporting_action_occurrence_candidate_ids") or []
            if _clean(value)
        ]
        if ids:
            occurrence_bound_trace_count += 1
        trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
        team = _clean(trace.get("team_identity_candidate_id"))
        actor = _clean(trace.get("actor_identity_candidate_id"))
        source_role = _clean(trace.get("source_role"))
        reflections = {
            _clean(value)
            for value in (trace.get("reflection_context_action_bundle_candidate_ids") or [])
            if _clean(value)
        }
        for occurrence_id in ids:
            occurrence_trace_counts[occurrence_id] += 1
            if trace_id:
                occurrence_trace_refs[occurrence_id].add(trace_id)
            if team:
                occurrence_team_refs[occurrence_id].add(team)
                occurrence_relation_types[occurrence_id].update({"OCCURRENCE_HAS_TEAM", "TEAM_PARTICIPATES_IN_TRACE"})
            if actor:
                if source_role == "GOALKEEPER_SURFACE_CANDIDATE":
                    occurrence_goalkeeper_refs[occurrence_id].add(actor)
                    occurrence_relation_types[occurrence_id].update({"OCCURRENCE_HAS_GOALKEEPER", "GOALKEEPER_PARTICIPATES_IN_TRACE"})
                else:
                    occurrence_player_refs[occurrence_id].add(actor)
                    occurrence_relation_types[occurrence_id].update({"OCCURRENCE_HAS_PLAYER", "PLAYER_PARTICIPATES_IN_TRACE"})
            if reflections:
                occurrence_reflection_bundle_refs[occurrence_id].update(reflections)
                occurrence_relation_types[occurrence_id].add("SAME_UNDERLYING_OCCURRENCE_REFLECTION")
            candidate = occurrence_meta.get(occurrence_id) or {}
            if source_role != "GOALKEEPER_SURFACE_CANDIDATE":
                if team == _clean(candidate.get("team_identity_candidate_id")) and actor == _clean(candidate.get("actor_identity_candidate_id")):
                    occurrence_actor_trace_counts[occurrence_id] += 1
                if team == _clean(candidate.get("opponent_team_identity_candidate_id")) and actor == _clean(candidate.get("opponent_identity_candidate_id")):
                    occurrence_opponent_trace_counts[occurrence_id] += 1

    complete = 0
    partial = 0
    missing = 0
    binding_records: list[dict[str, Any]] = []
    for candidate in occurrence_candidates:
        occurrence_id = _clean(candidate.get("action_occurrence_candidate_id"))
        actor_count = occurrence_actor_trace_counts.get(occurrence_id, 0)
        opponent_count = occurrence_opponent_trace_counts.get(occurrence_id, 0)
        total = occurrence_trace_counts.get(occurrence_id, 0)
        if actor_count >= 1 and opponent_count >= 1:
            state = "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE"
            complete += 1
        elif total:
            state = "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
            partial += 1
        else:
            state = "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
            missing += 1

        opponent_refs = sorted({
            value
            for value in (
                _clean(candidate.get("opponent_identity_candidate_id")),
                _clean(candidate.get("opponent_team_identity_candidate_id")),
            )
            if value
        })
        team_refs = set(occurrence_team_refs.get(occurrence_id, set()))
        for value in (
            _clean(candidate.get("team_identity_candidate_id")),
            _clean(candidate.get("opponent_team_identity_candidate_id")),
        ):
            if value:
                team_refs.add(value)
        relation_types = set(occurrence_relation_types.get(occurrence_id, set()))
        if opponent_refs:
            relation_types.add("OCCURRENCE_HAS_OPPONENT_CONTEXT")
        trace_refs = sorted(occurrence_trace_refs.get(occurrence_id, set()))
        if len(trace_refs) > 1:
            relation_types.add("DERIVED_FROM_SAME_OCCURRENCE")
        derivation_parents = {
            _clean(value)
            for value in (candidate.get("supporting_action_bundle_candidate_ids") or [])
            if _clean(value)
        }
        derivation_parents.update(occurrence_goalkeeper_context_bundle_refs.get(occurrence_id, set()))
        reflection_refs = sorted(occurrence_reflection_bundle_refs.get(occurrence_id, set()))

        binding_records.append({
            "object_binding_id": "ocb_" + _digest(occurrence_id, trace_refs)[:24],
            "occurrence_ref": occurrence_id,
            "trace_refs": trace_refs,
            "player_refs": sorted(occurrence_player_refs.get(occurrence_id, set())),
            "team_refs": sorted(team_refs),
            "goalkeeper_refs": sorted(occurrence_goalkeeper_refs.get(occurrence_id, set())),
            "goalkeeper_context_bundle_refs": sorted(occurrence_goalkeeper_context_bundle_refs.get(occurrence_id, set())),
            "goalkeeper_context_is_occurrence_participant_truth": False,
            "opponent_refs": opponent_refs,
            "relation_types": sorted(relation_types),
            "dependency_group": f"occurrence:{occurrence_id}" if occurrence_id else None,
            "independence_group": None,
            "independence_proven": False,
            "provenance_root": occurrence_id,
            "derivation_parents": sorted(derivation_parents),
            "reflection_context_refs": reflection_refs,
            "underlying_occurrence_root_count_contribution": 1 if occurrence_id else 0,
            "object_view_count_is_independent_support_count": False,
            "object_view_creates_event": False,
            "action_occurrence_candidate_id": occurrence_id,
            "binding_state": state,
            "actor_trace_candidate_count": actor_count,
            "opponent_trace_candidate_count": opponent_count,
            "total_occurrence_bound_trace_candidate_count": total,
            "binding_is_event_truth": False,
            "canonical_event_count": "UNKNOWN",
        })

    payload["occurrence_trace_binding_records"] = binding_records
    payload["occurrence_trace_binding_record_count"] = len(binding_records)
    payload["object_centric_trace_binding_record_count"] = len(binding_records)
    payload["object_views_create_independent_support"] = False
    payload["occurrence_bound_trace_candidate_count"] = occurrence_bound_trace_count
    payload["occurrence_both_participants_trace_visible_count"] = complete
    payload["occurrence_partial_participant_trace_visible_count"] = partial
    payload["occurrence_no_participant_trace_visible_count"] = missing
    payload["occurrence_explicit_review_bundle_trace_candidate_count"] = appended_trace_count
    payload["occurrence_goalkeeper_context_bundle_binding_count"] = sum(len(values) for values in occurrence_goalkeeper_context_bundle_refs.values())
    payload["goalkeeper_context_binding_creates_occurrence"] = False
    payload["goalkeeper_context_binding_creates_independent_support"] = False
    payload["occurrence_local_taxonomy_rebind_record_ids"] = []
    payload["occurrence_local_taxonomy_rebind_record_count"] = 0
    payload["occurrence_binding_preserves_taxonomy_review_state"] = True
    payload["occurrence_binding_changes_upstream_taxonomy_truth"] = False
    payload["occurrence_binding_is_event_truth"] = False

    reviews = list(payload.get("review_hits") or [])
    if partial:
        reviews.append("occurrence_partial_participant_trace_binding_present")
    if missing:
        reviews.append("occurrence_without_trace_binding_present")
    if appended_trace_count:
        reviews.append("occurrence_explicit_review_bundle_trace_binding_used")
    if payload["occurrence_goalkeeper_context_bundle_binding_count"]:
        reviews.append("occurrence_goalkeeper_context_binding_used")
    payload["review_hits"] = sorted(set(reviews))
    if payload.get("status") != "FAIL_CLOSED" and payload["review_hits"]:
        payload["status"] = "REVIEW_REQUIRED"
        payload["module_status"] = "REVIEW_REQUIRED"
    return payload
