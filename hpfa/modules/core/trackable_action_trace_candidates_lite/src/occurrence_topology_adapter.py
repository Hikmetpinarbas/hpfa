from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def apply_occurrence_topology_binding(
    trace_payload: dict[str, Any],
    occurrence_payload: dict[str, Any],
) -> dict[str, Any]:
    """Re-evaluate trace sufficiency according to the admitted occurrence topology.

    Legacy interaction occurrences require actor + opponent traces. A canonical action-grammar
    candidate with SINGLE_ACTOR_ACTION topology requires only the actor trace. This prevents a
    correctly admitted pass/dribble occurrence from being downgraded merely because it has no
    opponent participant by definition.

    The legacy trace inventory is preserved for support/provenance, but an explicit occurrence-
    backed primary trace surface is exposed for downstream membership. This does not promote
    occurrence candidates to canonical event truth or physical action truth.
    """
    if trace_payload.get("status") == "FAIL_CLOSED":
        return trace_payload

    occurrence_meta = {
        _clean(row.get("action_occurrence_candidate_id")): row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict) and _clean(row.get("action_occurrence_candidate_id"))
    }

    both_complete = 0
    single_complete = 0
    partial = 0
    missing = 0
    unresolved_topology = 0

    for record in trace_payload.get("occurrence_trace_binding_records") or []:
        if not isinstance(record, dict):
            continue
        occurrence_id = _clean(record.get("action_occurrence_candidate_id"))
        candidate = occurrence_meta.get(occurrence_id) or {}
        topology = _clean(candidate.get("occurrence_topology"))
        if not topology:
            topology = (
                "TWO_PARTICIPANT_INTERACTION"
                if _clean(candidate.get("opponent_identity_candidate_id"))
                else "UNRESOLVED"
            )
        actor_count = int(record.get("actor_trace_candidate_count") or 0)
        opponent_count = int(record.get("opponent_trace_candidate_count") or 0)
        total = int(record.get("total_occurrence_bound_trace_candidate_count") or 0)

        record["occurrence_topology"] = topology
        if topology == "SINGLE_ACTOR_ACTION":
            record["required_participant_scope"] = "ACTOR_ONLY"
            if actor_count >= 1:
                record["binding_state"] = "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE"
                single_complete += 1
            elif total:
                record["binding_state"] = "SINGLE_ACTOR_TRACE_MISMATCH_REVIEW_REQUIRED"
                partial += 1
            else:
                record["binding_state"] = "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
                missing += 1
        elif topology == "TWO_PARTICIPANT_INTERACTION":
            record["required_participant_scope"] = "ACTOR_AND_OPPONENT"
            if actor_count >= 1 and opponent_count >= 1:
                record["binding_state"] = "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE"
                both_complete += 1
            elif total:
                record["binding_state"] = "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
                partial += 1
            else:
                record["binding_state"] = "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
                missing += 1
        else:
            record["required_participant_scope"] = "UNRESOLVED"
            unresolved_topology += 1
            if total:
                record["binding_state"] = "OCCURRENCE_TOPOLOGY_UNRESOLVED_REVIEW_REQUIRED"
                partial += 1
            else:
                record["binding_state"] = "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
                missing += 1

    trace_payload["occurrence_both_participants_trace_visible_count"] = both_complete
    trace_payload["occurrence_single_actor_trace_visible_count"] = single_complete
    trace_payload["occurrence_partial_participant_trace_visible_count"] = partial
    trace_payload["occurrence_no_participant_trace_visible_count"] = missing
    trace_payload["occurrence_unresolved_topology_count"] = unresolved_topology
    trace_payload["occurrence_topology_aware_binding"] = True

    legacy_traces = [
        row
        for row in (trace_payload.get("trackable_action_trace_candidates") or [])
        if isinstance(row, dict)
    ]
    primary_traces: list[dict[str, Any]] = []
    for trace in legacy_traces:
        occurrence_ids = sorted(
            {
                _clean(value)
                for value in trace.get("supporting_action_occurrence_candidate_ids") or []
                if _clean(value)
            }
        )
        is_primary = bool(occurrence_ids)
        trace["primary_occurrence_member_candidate"] = is_primary
        trace["legacy_unbound_support_only"] = not is_primary
        if is_primary:
            primary_traces.append(trace)

    trace_payload["source_legacy_trace_candidate_count"] = len(legacy_traces)
    trace_payload["primary_occurrence_trace_candidates"] = primary_traces
    trace_payload["primary_occurrence_trace_candidate_count"] = len(primary_traces)
    trace_payload["legacy_unbound_trace_candidate_count"] = len(legacy_traces) - len(primary_traces)
    trace_payload["primary_trace_member_surface"] = "OCCURRENCE_BACKED_TRACE_CANDIDATES"
    trace_payload["legacy_trace_records_are_primary_action_member_surface"] = False
    trace_payload["legacy_unbound_trace_records_retained_as_support_only"] = True
    trace_payload["primary_occurrence_trace_surface_is_action_identity_truth"] = False
    trace_payload["primary_occurrence_trace_surface_is_canonical_event_truth"] = False

    reviews = [
        _clean(value)
        for value in trace_payload.get("review_hits") or []
        if _clean(value)
        and _clean(value)
        not in {
            "occurrence_partial_participant_trace_binding_present",
            "occurrence_without_trace_binding_present",
        }
    ]
    if partial:
        reviews.append("occurrence_partial_participant_trace_binding_present")
    if missing:
        reviews.append("occurrence_without_trace_binding_present")
    if unresolved_topology:
        reviews.append("occurrence_topology_unresolved")
    trace_payload["review_hits"] = sorted(set(reviews))
    if trace_payload.get("status") != "FAIL_CLOSED":
        state = "REVIEW_REQUIRED" if trace_payload["review_hits"] else "PASS"
        trace_payload["status"] = state
        trace_payload["module_status"] = state

    trace_payload["canonical_event_count"] = "UNKNOWN"
    trace_payload["true_action_count"] = "UNKNOWN"
    trace_payload["production_release"] = False
    return trace_payload
