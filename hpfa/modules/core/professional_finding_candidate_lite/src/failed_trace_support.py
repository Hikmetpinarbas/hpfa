from __future__ import annotations

from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _validate(label: str, payload: dict[str, Any], module_id: str) -> list[str]:
    blocks: list[str] = []
    if payload.get("module_id") != module_id:
        blocks.append(f"{label}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{label}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{label}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{label}_production_release_claimed")
    if _status(payload.get("status") or payload.get("module_status")) == "FAIL_CLOSED":
        blocks.append(f"{label}_input_fail_closed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{label}_hard_blocks_present")
    return blocks


def attach_failed_trace_support(
    finding_payload: dict[str, Any],
    reciprocal_payload: dict[str, Any],
    trace_payload: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate trace-evidence coverage behind existing professional finding candidates.

    The family name is retained for governance continuity. A missing or partial trace is
    evidence-coverage debt only. It is never interpreted as a failed football action,
    negative outcome, counterevidence, physical-action absence, or canonical event truth.
    """
    blocks: list[str] = []
    for label, payload, module_id in (
        ("finding", finding_payload, FINDING_MODULE_ID),
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
        ("trace", trace_payload, TRACE_MODULE_ID),
    ):
        blocks.extend(_validate(label, payload, module_id))

    result = dict(finding_payload)
    result["professional_finding_candidates"] = [
        dict(row) for row in (finding_payload.get("professional_finding_candidates") or []) if isinstance(row, dict)
    ]
    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["failed_trace_support_status"] = "FAIL_CLOSED"
        result["hard_block_hits"] = sorted(set((finding_payload.get("hard_block_hits") or []) + blocks))
        result["claim_output_allowed_count"] = 0
        result["professional_finding_emitted_count"] = 0
        result["canonical_event_count"] = CANONICAL_EVENT_COUNT
        result["true_action_count"] = TRUE_ACTION_COUNT
        result["production_release"] = False
        return result

    chain_by_id = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): row
        for row in (reciprocal_payload.get("reciprocal_process_chain_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }
    trace_by_id = {
        _clean(row.get("trackable_action_trace_candidate_id")): row
        for row in (trace_payload.get("trackable_action_trace_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
    }
    binding_by_occurrence = {
        _clean(row.get("action_occurrence_candidate_id")): row
        for row in (trace_payload.get("occurrence_trace_binding_records") or [])
        if isinstance(row, dict) and _clean(row.get("action_occurrence_candidate_id"))
    }

    evaluated = 0
    incomplete = 0
    complete = 0
    no_linkage = 0

    for finding in result["professional_finding_candidates"]:
        support = finding.get("support") if isinstance(finding.get("support"), dict) else {}
        chain_ids = {
            _clean(value)
            for value in (support.get("supporting_reciprocal_process_chain_candidate_ids") or [])
            if _clean(value)
        }
        trace_ids: set[str] = set()
        for chain_id in chain_ids:
            chain = chain_by_id.get(chain_id) or {}
            trace_ids.update(
                _clean(value)
                for value in (chain.get("supporting_trackable_action_trace_candidate_ids") or [])
                if _clean(value)
            )

        occurrence_ids: set[str] = set()
        missing_trace_ids: list[str] = []
        unbound_trace_ids: list[str] = []
        for trace_id in sorted(trace_ids):
            trace = trace_by_id.get(trace_id)
            if not isinstance(trace, dict):
                missing_trace_ids.append(trace_id)
                continue
            linked = {
                _clean(value)
                for value in (trace.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(value)
            }
            if not linked:
                unbound_trace_ids.append(trace_id)
            occurrence_ids.update(linked)

        binding_counts = {
            "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE": 0,
            "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED": 0,
            "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED": 0,
            "UNKNOWN_BINDING_STATE": 0,
        }
        missing_binding_occurrence_ids: list[str] = []
        for occurrence_id in sorted(occurrence_ids):
            binding = binding_by_occurrence.get(occurrence_id)
            if not isinstance(binding, dict):
                missing_binding_occurrence_ids.append(occurrence_id)
                binding_counts["UNKNOWN_BINDING_STATE"] += 1
                continue
            state = _clean(binding.get("binding_state")) or "UNKNOWN_BINDING_STATE"
            if state not in binding_counts:
                state = "UNKNOWN_BINDING_STATE"
            binding_counts[state] += 1

        if not trace_ids:
            state = "NO_SUPPORTING_TRACE_LINKAGE_REVIEW_REQUIRED"
            no_linkage += 1
        elif (
            missing_trace_ids
            or unbound_trace_ids
            or missing_binding_occurrence_ids
            or binding_counts["PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"]
            or binding_counts["NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"]
            or binding_counts["UNKNOWN_BINDING_STATE"]
        ):
            state = "INCOMPLETE_TRACE_EVIDENCE_SUPPORT_REVIEW_REQUIRED"
            incomplete += 1
        else:
            state = "COMPLETE_VISIBLE_PARTICIPANT_TRACE_SUPPORT_CURRENT_SCOPE"
            complete += 1
        evaluated += 1

        trace_support = {
            "state_candidate": state,
            "supporting_trace_candidate_ids": sorted(trace_ids),
            "supporting_trace_candidate_count": len(trace_ids),
            "supporting_occurrence_candidate_ids": sorted(occurrence_ids),
            "supporting_occurrence_candidate_count": len(occurrence_ids),
            "occurrence_binding_state_counts": binding_counts,
            "missing_trace_candidate_ids": missing_trace_ids,
            "trace_candidates_without_occurrence_binding_ids": unbound_trace_ids,
            "occurrence_ids_without_binding_record": missing_binding_occurrence_ids,
            "scope": "CURRENT_OCCURRENCE_BOUND_TRACKABLE_TRACE_EVIDENCE_ONLY",
            "missing_trace_is_failed_football_action": False,
            "missing_trace_is_negative_outcome": False,
            "missing_trace_is_counterevidence": False,
            "missing_trace_proves_action_absence": False,
            "trace_count_is_physical_action_count": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }

        challenge = dict(finding.get("finding_challenge_packet") or {})
        evaluated_families = list(challenge.get("evaluated_falsifier_families") or [])
        if "FAILED_TRACE_SUPPORT" not in evaluated_families:
            evaluated_families.append("FAILED_TRACE_SUPPORT")
        pending = [
            value for value in (challenge.get("pending_falsifier_families") or [])
            if value != "FAILED_TRACE_SUPPORT"
        ]
        challenge["evaluated_falsifier_families"] = evaluated_families
        challenge["pending_falsifier_families"] = pending
        challenge["failed_trace_support"] = trace_support
        challenge["failed_trace_support_evaluated_for_current_scope"] = True
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["challenge_packet_is_final_finding"] = False
        finding["finding_challenge_packet"] = challenge

        uncertainty = dict(finding.get("uncertainty") or {})
        uncertainty["trace_evidence_support_state_candidate"] = state
        uncertainty["failed_trace_support_evaluated_for_current_scope"] = True
        uncertainty["missing_trace_is_action_failure_truth"] = False
        finding["uncertainty"] = uncertainty
        finding["claim_output_allowed"] = False
        finding["professional_finding_emitted"] = False

    result["failed_trace_support_status"] = "REVIEW_REQUIRED"
    result["failed_trace_support_evaluated_candidate_count"] = evaluated
    result["failed_trace_support_complete_candidate_count"] = complete
    result["failed_trace_support_incomplete_candidate_count"] = incomplete
    result["failed_trace_support_no_linkage_candidate_count"] = no_linkage
    result["failed_trace_support_evaluated_for_current_scope"] = True
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
