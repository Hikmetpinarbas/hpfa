from __future__ import annotations

from typing import Any

from hpfa.modules.core.professional_finding_candidate_lite.src.alternative_explanation import (
    attach_alternative_explanation_evaluation,
)

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
    trace_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit whether finding support is trace-visible without converting missing trace into football failure.

    With a trace payload, the evaluator inspects occurrence-binding coverage. Without it,
    it performs the weaker but still useful current reciprocal-chain trace-linkage audit.
    The resulting challenge packet is then passed to the alternative-explanation evaluator.
    """
    blocks = _validate("finding", finding_payload, FINDING_MODULE_ID)
    blocks += _validate("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID)
    full_trace_scope = isinstance(trace_payload, dict) and bool(trace_payload)
    if full_trace_scope:
        blocks += _validate("trace", trace_payload or {}, TRACE_MODULE_ID)

    result = dict(finding_payload)
    rows = [dict(row) for row in (finding_payload.get("professional_finding_candidates") or []) if isinstance(row, dict)]
    result["professional_finding_candidates"] = rows
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
    trace_by_id: dict[str, dict[str, Any]] = {}
    binding_by_occurrence: dict[str, dict[str, Any]] = {}
    if full_trace_scope:
        trace_by_id = {
            _clean(row.get("trackable_action_trace_candidate_id")): row
            for row in ((trace_payload or {}).get("trackable_action_trace_candidates") or [])
            if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
        }
        binding_by_occurrence = {
            _clean(row.get("action_occurrence_candidate_id")): row
            for row in ((trace_payload or {}).get("occurrence_trace_binding_records") or [])
            if isinstance(row, dict) and _clean(row.get("action_occurrence_candidate_id"))
        }

    complete = incomplete = no_linkage = 0
    for finding in rows:
        support = finding.get("support") if isinstance(finding.get("support"), dict) else {}
        chain_ids = {_clean(v) for v in (support.get("supporting_reciprocal_process_chain_candidate_ids") or []) if _clean(v)}
        missing_chain_ids = sorted(chain_id for chain_id in chain_ids if chain_id not in chain_by_id)
        trace_ids: set[str] = set()
        chains_without_trace: list[str] = []
        for chain_id in sorted(chain_ids):
            chain = chain_by_id.get(chain_id)
            if not isinstance(chain, dict):
                continue
            linked = {_clean(v) for v in (chain.get("supporting_trackable_action_trace_candidate_ids") or []) if _clean(v)}
            if not linked:
                chains_without_trace.append(chain_id)
            trace_ids.update(linked)

        occurrence_ids: set[str] = set()
        missing_trace_ids: list[str] = []
        unbound_trace_ids: list[str] = []
        binding_counts = {
            "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE": 0,
            "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED": 0,
            "NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED": 0,
            "UNKNOWN_BINDING_STATE": 0,
        }
        if full_trace_scope:
            for trace_id in sorted(trace_ids):
                trace = trace_by_id.get(trace_id)
                if not isinstance(trace, dict):
                    missing_trace_ids.append(trace_id)
                    continue
                linked = {_clean(v) for v in (trace.get("supporting_action_occurrence_candidate_ids") or []) if _clean(v)}
                if not linked:
                    unbound_trace_ids.append(trace_id)
                occurrence_ids.update(linked)
            for occurrence_id in sorted(occurrence_ids):
                binding = binding_by_occurrence.get(occurrence_id)
                state = _clean((binding or {}).get("binding_state")) or "UNKNOWN_BINDING_STATE"
                if state not in binding_counts:
                    state = "UNKNOWN_BINDING_STATE"
                binding_counts[state] += 1

        if not trace_ids:
            state = "NO_SUPPORTING_TRACE_LINKAGE_REVIEW_REQUIRED"
            no_linkage += 1
        elif missing_chain_ids or chains_without_trace:
            state = "INCOMPLETE_CHAIN_TRACE_LINKAGE_REVIEW_REQUIRED"
            incomplete += 1
        elif full_trace_scope and (
            missing_trace_ids
            or unbound_trace_ids
            or binding_counts["PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"]
            or binding_counts["NO_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"]
            or binding_counts["UNKNOWN_BINDING_STATE"]
        ):
            state = "INCOMPLETE_OCCURRENCE_TRACE_EVIDENCE_REVIEW_REQUIRED"
            incomplete += 1
        else:
            state = (
                "COMPLETE_VISIBLE_PARTICIPANT_TRACE_SUPPORT_CURRENT_SCOPE"
                if full_trace_scope
                else "CHAIN_TRACE_LINKAGE_VISIBLE_CURRENT_SCOPE"
            )
            complete += 1

        trace_support = {
            "state_candidate": state,
            "supporting_chain_candidate_count": len(chain_ids),
            "supporting_trace_candidate_count": len(trace_ids),
            "supporting_trace_candidate_ids": sorted(trace_ids),
            "missing_supporting_chain_candidate_ids": missing_chain_ids,
            "chains_without_visible_trace_support": chains_without_trace,
            "full_occurrence_binding_scope_evaluated": full_trace_scope,
            "supporting_occurrence_candidate_count": len(occurrence_ids),
            "occurrence_binding_state_counts": binding_counts,
            "missing_trace_candidate_ids": missing_trace_ids,
            "trace_candidates_without_occurrence_binding_ids": unbound_trace_ids,
            "scope": (
                "CURRENT_OCCURRENCE_BOUND_TRACKABLE_TRACE_EVIDENCE"
                if full_trace_scope
                else "CURRENT_RECIPROCAL_CHAIN_TRACE_LINKAGE_ONLY"
            ),
            "missing_trace_is_failed_football_action": False,
            "missing_trace_is_negative_outcome": False,
            "missing_trace_is_counterevidence": False,
            "missing_trace_proves_action_absence": False,
            "trace_count_is_physical_action_count": False,
        }

        challenge = dict(finding.get("finding_challenge_packet") or {})
        evaluated = list(challenge.get("evaluated_falsifier_families") or [])
        marker = "FAILED_TRACE_SUPPORT" if full_trace_scope else "FAILED_TRACE_SUPPORT_CHAIN_LINKAGE_SCOPE"
        if marker not in evaluated:
            evaluated.append(marker)
        challenge["evaluated_falsifier_families"] = evaluated
        if full_trace_scope:
            challenge["pending_falsifier_families"] = [
                value for value in (challenge.get("pending_falsifier_families") or [])
                if value != "FAILED_TRACE_SUPPORT"
            ]
        challenge["failed_trace_support"] = trace_support
        challenge["failed_trace_support_evaluated_for_current_scope"] = True
        challenge["failed_trace_support_complete_for_final_finding"] = full_trace_scope
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["challenge_packet_is_final_finding"] = False
        finding["finding_challenge_packet"] = challenge

        uncertainty = dict(finding.get("uncertainty") or {})
        uncertainty["trace_evidence_support_state_candidate"] = state
        uncertainty["failed_trace_support_full_occurrence_scope_evaluated"] = full_trace_scope
        uncertainty["missing_trace_is_action_failure_truth"] = False
        finding["uncertainty"] = uncertainty
        finding["claim_output_allowed"] = False
        finding["professional_finding_emitted"] = False

    result["failed_trace_support_status"] = "REVIEW_REQUIRED"
    result["failed_trace_support_evaluated_candidate_count"] = len(rows)
    result["failed_trace_support_complete_candidate_count"] = complete
    result["failed_trace_support_incomplete_candidate_count"] = incomplete
    result["failed_trace_support_no_linkage_candidate_count"] = no_linkage
    result["failed_trace_support_full_occurrence_scope_evaluated"] = full_trace_scope
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return attach_alternative_explanation_evaluation(result)
