from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def build_occurrence_aware_trace_payload(
    action_payload: dict[str, Any],
    taxonomy_payload: dict[str, Any],
    relation_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    occurrence_payload: dict[str, Any],
    trace_builder,
) -> dict[str, Any]:
    """Rebind only occurrence-admitted review bundles into the existing trace producer.

    This is a local-copy migration adapter. It never mutates upstream taxonomy truth and never
    promotes an occurrence candidate to canonical/physical event truth.
    """
    action_copy = copy.deepcopy(action_payload)
    taxonomy_copy = copy.deepcopy(taxonomy_payload)
    relation_copy = copy.deepcopy(relation_payload)
    evidence_copy = copy.deepcopy(evidence_payload)

    occurrence_candidates = [
        row for row in (occurrence_payload.get("action_occurrence_candidates") or []) if isinstance(row, dict)
    ]
    admitted_record_ids: set[str] = set()
    occurrence_by_bundle: dict[str, set[str]] = defaultdict(set)
    occurrence_meta: dict[str, dict[str, Any]] = {}

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
            record_id = _clean(provenance.get("multi_family_review_record_id"))
            if record_id:
                admitted_record_ids.add(record_id)

    locally_rebound_record_ids: list[str] = []
    for record in taxonomy_copy.get("multi_family_review_records") or []:
        if not isinstance(record, dict):
            continue
        record_id = _clean(record.get("multi_family_review_record_id"))
        if record_id not in admitted_record_ids:
            continue
        if _clean(record.get("record_status")) != "REVIEW_REQUIRED":
            continue
        record["record_status"] = "PASS_CANDIDATE_CLASSIFICATION"
        locally_rebound_record_ids.append(record_id)

    payload = trace_builder(action_copy, taxonomy_copy, relation_copy, evidence_copy)

    occurrence_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_actor_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_opponent_trace_counts: dict[str, int] = defaultdict(int)
    occurrence_bound_trace_count = 0

    for trace in payload.get("trackable_action_trace_candidates") or []:
        if not isinstance(trace, dict):
            continue
        supporting_occurrence_ids: set[str] = set()
        for raw_bundle_id in trace.get("selected_action_bundle_candidate_ids") or []:
            supporting_occurrence_ids.update(occurrence_by_bundle.get(_clean(raw_bundle_id), set()))
        ids = sorted(supporting_occurrence_ids)
        trace["supporting_action_occurrence_candidate_ids"] = ids
        trace["occurrence_backed_trace_candidate"] = bool(ids)
        trace["occurrence_binding_is_event_truth"] = False
        trace["occurrence_binding_changes_upstream_taxonomy_truth"] = False
        trace["occurrence_binding_scope"] = (
            "TRACE_SELECTION_LOCAL_COPY_ONLY" if ids else "NO_OCCURRENCE_BINDING"
        )
        if ids:
            occurrence_bound_trace_count += 1
        team = _clean(trace.get("team_identity_candidate_id"))
        actor = _clean(trace.get("actor_identity_candidate_id"))
        for occurrence_id in ids:
            occurrence_trace_counts[occurrence_id] += 1
            candidate = occurrence_meta.get(occurrence_id) or {}
            if (
                team == _clean(candidate.get("team_identity_candidate_id"))
                and actor == _clean(candidate.get("actor_identity_candidate_id"))
            ):
                occurrence_actor_trace_counts[occurrence_id] += 1
            if (
                team == _clean(candidate.get("opponent_team_identity_candidate_id"))
                and actor == _clean(candidate.get("opponent_identity_candidate_id"))
            ):
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
        binding_records.append({
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
    payload["occurrence_bound_trace_candidate_count"] = occurrence_bound_trace_count
    payload["occurrence_both_participants_trace_visible_count"] = complete
    payload["occurrence_partial_participant_trace_visible_count"] = partial
    payload["occurrence_no_participant_trace_visible_count"] = missing
    payload["occurrence_local_taxonomy_rebind_record_ids"] = sorted(locally_rebound_record_ids)
    payload["occurrence_local_taxonomy_rebind_record_count"] = len(locally_rebound_record_ids)
    payload["occurrence_binding_changes_upstream_taxonomy_truth"] = False
    payload["occurrence_binding_is_event_truth"] = False

    reviews = list(payload.get("review_hits") or [])
    if partial:
        reviews.append("occurrence_partial_participant_trace_binding_present")
    if missing:
        reviews.append("occurrence_without_trace_binding_present")
    if locally_rebound_record_ids:
        reviews.append("occurrence_local_trace_taxonomy_rebind_used")
    payload["review_hits"] = sorted(set(reviews))
    if payload.get("status") != "FAIL_CLOSED" and payload["review_hits"]:
        payload["status"] = "REVIEW_REQUIRED"
        payload["module_status"] = "REVIEW_REQUIRED"
    return payload
