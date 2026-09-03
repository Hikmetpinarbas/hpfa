from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

CLAIM_CEILING = "RECIPROCAL_OUTCOME_CONTRAST_CANDIDATE_ONLY"
FINDING_INPUT_CLAIM_CEILING = "DEFEASIBLE_PROCESS_FINDING_INPUT_CANDIDATE_ONLY"
C4_PACKET_CLAIM_CEILING = "composite_candidate_only"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
COUNTER_SEARCH_SCOPE = "SAME_ADMITTED_PROCESS_FAMILY_SIGNATURE_ONLY"
COUNTER_SEARCH_EVALUATED_FAMILIES = ["DIRECT_VISIBLE_OUTCOME_CONTRAST"]
COUNTER_SEARCH_PENDING_FAMILIES = [
    "CONTEXT_DEPENDENCE",
    "SEGMENT_ONLY",
    "PLAYER_OUTLIER",
    "THRESHOLD_SENSITIVITY",
    "OPPONENT_SYMMETRY",
    "FAILED_TRACE_SUPPORT",
    "DUPLICATE_REFLECTION_RISK",
    "ALTERNATIVE_EXPLANATION",
]
SEGMENT_FALSIFIER_FAMILY = "SEGMENT_ONLY"
SEGMENT_FALSIFIER_METHOD = "EPISODE_SCOPE_SPREAD_CANDIDATE"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _family_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    anchor = tuple(sorted(_clean(key) for key in (row.get("anchor_action_family_counts") or {}) if _clean(key)))
    response = tuple(sorted(_clean(key) for key in (row.get("response_action_family_counts") or {}) if _clean(key)))
    return anchor, response


def _outcome_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    response = tuple(sorted(_clean(key) for key in (row.get("response_consequence_candidate_counts") or {}) if _clean(key)))
    counter = tuple(sorted(_clean(key) for key in (row.get("counter_response_consequence_candidate_counts") or {}) if _clean(key)))
    return response, counter, bool(row.get("counter_response_visible"))


def _episode_scope_signature(row: dict[str, Any]) -> tuple[str, str] | None:
    anchor_episode = _clean(row.get("anchor_episode_candidate_id"))
    response_episode = _clean(row.get("response_episode_candidate_id"))
    if not anchor_episode or not response_episode:
        return None
    return anchor_episode, response_episode


def _contrast_episode_scope(row: dict[str, Any]) -> tuple[str, str] | None:
    scope = row.get("process_episode_scope_signature_candidate")
    if not isinstance(scope, dict):
        return None
    anchor_episode = _clean(scope.get("anchor_episode_candidate_id"))
    response_episode = _clean(scope.get("response_episode_candidate_id"))
    if not anchor_episode or not response_episode:
        return None
    return anchor_episode, response_episode


def _segment_scope_metadata(
    chain_id: str,
    analogue_ids: list[str],
    scope_by_chain_id: dict[str, tuple[str, str] | None],
) -> dict[str, Any]:
    anchor_scope = scope_by_chain_id.get(chain_id)
    peer_scopes = {peer_id: scope_by_chain_id.get(peer_id) for peer_id in analogue_ids}
    missing_scope_ids = sorted(
        [ref_id for ref_id, scope in [(chain_id, anchor_scope), *peer_scopes.items()] if scope is None]
    )

    if not analogue_ids:
        state = "SEGMENT_SCOPE_NOT_EVALUATED_NO_ANALOGUE"
        falsifier_state = "NOT_EVALUATED"
        evaluated = False
        unique_scopes: set[tuple[str, str]] = set()
    elif missing_scope_ids:
        state = "SEGMENT_SCOPE_NOT_EVALUATED_INCOMPLETE_EPISODE_BINDING"
        falsifier_state = "NOT_EVALUATED"
        evaluated = False
        unique_scopes = set()
    else:
        unique_scopes = {anchor_scope} if anchor_scope is not None else set()
        unique_scopes.update(scope for scope in peer_scopes.values() if scope is not None)
        evaluated = True
        if len(unique_scopes) > 1:
            state = "MULTI_EPISODE_SCOPE_VISIBLE_CANDIDATE"
            falsifier_state = "SEGMENT_ONLY_FALSIFIER_NOT_OBSERVED_IN_CURRENT_EPISODE_SCOPE_COMPARISON"
        else:
            state = "SINGLE_EPISODE_SCOPE_ONLY_CANDIDATE"
            falsifier_state = "SEGMENT_ONLY_RISK_CANDIDATE"

    return {
        "segment_falsifier_method": SEGMENT_FALSIFIER_METHOD,
        "segment_scope_state": state,
        "segment_falsifier_state": falsifier_state,
        "segment_scope_evaluated": evaluated,
        "segment_scope_observed_episode_scope_count": len(unique_scopes),
        "segment_scope_episode_pair_labels": sorted(f"{left} -> {right}" for left, right in unique_scopes),
        "segment_scope_missing_binding_chain_ids": missing_scope_ids,
        "segment_scope_is_recurrence_truth": False,
        "segment_scope_is_pattern_robustness_truth": False,
        "multi_episode_scope_is_stable_tendency_truth": False,
    }


def _counter_search_metadata(
    support_ids: list[str],
    counter_ids: list[str],
    *,
    segment_scope_evaluated: bool,
) -> dict[str, Any]:
    peer_count = len(set(support_ids) | set(counter_ids))
    evaluated_families = list(COUNTER_SEARCH_EVALUATED_FAMILIES)
    pending_families = list(COUNTER_SEARCH_PENDING_FAMILIES)
    if segment_scope_evaluated:
        evaluated_families.append(SEGMENT_FALSIFIER_FAMILY)
        pending_families = [family for family in pending_families if family != SEGMENT_FALSIFIER_FAMILY]
    return {
        "counter_search_scope": COUNTER_SEARCH_SCOPE,
        "counter_search_scope_state": (
            "PARTIAL_SCOPE_EVALUATED" if peer_count else "PARTIAL_SCOPE_EVALUATED_NO_ANALOGUE"
        ),
        "counter_search_peer_count": peer_count,
        "counter_search_evaluated_families": evaluated_families,
        "counter_search_pending_families": pending_families,
        "counter_search_complete_for_final_finding": False,
        "alternative_explanation_search_state": "NOT_EVALUATED",
        "alternative_explanation_required": True,
        "falsifier_coverage_state": "PARTIAL",
        "falsifier_families_evaluated": list(evaluated_families),
        "falsifier_families_pending": list(pending_families),
    }


def _claim_safety_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "counter_search_scope": row.get("counter_search_scope"),
        "counter_search_scope_state": row.get("counter_search_scope_state"),
        "counter_search_peer_count": row.get("counter_search_peer_count"),
        "counter_search_evaluated_families": list(row.get("counter_search_evaluated_families") or []),
        "counter_search_pending_families": list(row.get("counter_search_pending_families") or []),
        "counter_search_complete_for_final_finding": False,
        "alternative_explanation_search_state": row.get("alternative_explanation_search_state"),
        "alternative_explanation_required": row.get("alternative_explanation_required") is True,
        "falsifier_coverage_state": row.get("falsifier_coverage_state"),
        "falsifier_families_evaluated": list(row.get("falsifier_families_evaluated") or []),
        "falsifier_families_pending": list(row.get("falsifier_families_pending") or []),
        "segment_falsifier_method": row.get("segment_falsifier_method"),
        "segment_scope_state": row.get("segment_scope_state"),
        "segment_falsifier_state": row.get("segment_falsifier_state"),
        "segment_scope_evaluated": row.get("segment_scope_evaluated") is True,
        "segment_scope_observed_episode_scope_count": row.get("segment_scope_observed_episode_scope_count"),
        "segment_scope_episode_pair_labels": list(row.get("segment_scope_episode_pair_labels") or []),
        "segment_scope_missing_binding_chain_ids": list(row.get("segment_scope_missing_binding_chain_ids") or []),
        "segment_scope_is_recurrence_truth": False,
        "segment_scope_is_pattern_robustness_truth": False,
        "multi_episode_scope_is_stable_tendency_truth": False,
        "no_visible_counterexample_is_confirmation": False,
        "support_links_are_independent_votes": False,
        "counterevidence_links_are_independent_votes": False,
        "withdrawal_condition": row.get("withdrawal_condition"),
        "finding_emitted": False,
        "claim_safety_metadata_is_truth_claim": False,
    }


def build_outcome_contrast_candidates(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    """Build same-process/different-visible-outcome contrast candidates.

    This function does not infer causal efficacy, tactical success, expected value,
    or canonical outcomes. It only compares already-built reciprocal process
    candidates that share the same visible anchor/response action-family signature.
    """
    records = reciprocal_payload.get("reciprocal_process_chain_candidates") or []
    if reciprocal_payload.get("status") == "FAIL_CLOSED" or not isinstance(records, list):
        return {
            "outcome_contrast_candidates": [],
            "outcome_contrast_candidate_count": 0,
            "different_outcome_analogue_link_count": 0,
            "same_outcome_support_link_count": 0,
            "outcome_contrast_status": "FAIL_CLOSED",
            "outcome_contrast_claim_ceiling": CLAIM_CEILING,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if not isinstance(row, dict):
            continue
        chain_id = _clean(row.get("reciprocal_process_chain_candidate_id"))
        if not chain_id:
            continue
        groups[_family_signature(row)].append(row)

    contrasts: list[dict[str, Any]] = []
    different_links = 0
    same_links = 0
    for family_signature, group in sorted(groups.items(), key=lambda item: repr(item[0])):
        for anchor in group:
            anchor_id = _clean(anchor.get("reciprocal_process_chain_candidate_id"))
            anchor_outcome = _outcome_signature(anchor)
            anchor_episode_scope = _episode_scope_signature(anchor)
            different: list[str] = []
            same: list[str] = []
            for peer in group:
                peer_id = _clean(peer.get("reciprocal_process_chain_candidate_id"))
                if not peer_id or peer_id == anchor_id:
                    continue
                if _outcome_signature(peer) == anchor_outcome:
                    same.append(peer_id)
                else:
                    different.append(peer_id)

            different = sorted(set(different))
            same = sorted(set(same))
            different_links += len(different)
            same_links += len(same)
            contrasts.append({
                "outcome_contrast_candidate_id": "oc_" + _digest(anchor_id, family_signature, anchor_outcome)[:24],
                "reciprocal_process_chain_candidate_id": anchor_id,
                "process_family_signature_candidate": {
                    "anchor_action_families": list(family_signature[0]),
                    "response_action_families": list(family_signature[1]),
                },
                "process_episode_scope_signature_candidate": (
                    {
                        "anchor_episode_candidate_id": anchor_episode_scope[0],
                        "response_episode_candidate_id": anchor_episode_scope[1],
                    }
                    if anchor_episode_scope is not None
                    else None
                ),
                "episode_scope_binding_complete": anchor_episode_scope is not None,
                "visible_outcome_signature_candidate": {
                    "response_consequence_families": list(anchor_outcome[0]),
                    "counter_response_consequence_families": list(anchor_outcome[1]),
                    "counter_response_visible": anchor_outcome[2],
                },
                "different_visible_outcome_analogue_chain_ids": different,
                "same_visible_outcome_support_chain_ids": same,
                "counterevidence_candidate_present": bool(different),
                "contrast_interpretation": (
                    "A visible reciprocal process candidate with the same anchor/response action-family signature ended with a different visible consequence/counter-response signature."
                    if different
                    else "No same-signature different-outcome analogue is visible in the admitted reciprocal candidate set."
                ),
                "allowed_claim": "Visible process candidates with the same admitted action-family signature may be contrasted by their observed consequence/counter-response signatures.",
                "forbidden_inference": [
                    "causal efficacy",
                    "tactical success truth",
                    "expected outcome probability",
                    "coach intention",
                    "adaptation truth",
                    "possession truth",
                    "dominance",
                ],
                "withdrawal_condition": "Withdraw or downgrade if the underlying reciprocal chain, family signature, consequence signature, temporal relation, or episode binding is invalidated.",
                "outcome_contrast_is_causal_truth": False,
                "outcome_contrast_is_tactical_success_truth": False,
                "same_signature_implies_same_process_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "true_action_count": TRUE_ACTION_COUNT,
                "claim_ceiling": CLAIM_CEILING,
            })

    return {
        "outcome_contrast_candidates": contrasts,
        "outcome_contrast_candidate_count": len(contrasts),
        "different_outcome_analogue_link_count": different_links,
        "same_outcome_support_link_count": same_links,
        "outcome_contrast_status": "PASS" if contrasts else "NO_ELIGIBLE_CONTRAST_CANDIDATES",
        "outcome_contrast_claim_ceiling": CLAIM_CEILING,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def build_defeasible_process_finding_inputs(contrast_payload: dict[str, Any]) -> dict[str, Any]:
    """Package contrasts as downstream finding inputs without emitting findings."""
    contrasts = contrast_payload.get("outcome_contrast_candidates") or []
    if contrast_payload.get("outcome_contrast_status") == "FAIL_CLOSED" or not isinstance(contrasts, list):
        return {
            "defeasible_process_finding_inputs": [],
            "defeasible_process_finding_input_count": 0,
            "finding_input_status": "FAIL_CLOSED",
            "finding_input_claim_ceiling": FINDING_INPUT_CLAIM_CEILING,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    scope_by_chain_id = {
        _clean(row.get("reciprocal_process_chain_candidate_id")): _contrast_episode_scope(row)
        for row in contrasts
        if isinstance(row, dict) and _clean(row.get("reciprocal_process_chain_candidate_id"))
    }

    inputs: list[dict[str, Any]] = []
    for contrast in contrasts:
        if not isinstance(contrast, dict):
            continue
        chain_id = _clean(contrast.get("reciprocal_process_chain_candidate_id"))
        contrast_id = _clean(contrast.get("outcome_contrast_candidate_id"))
        if not chain_id or not contrast_id:
            continue
        support_ids = sorted(set(_clean(item) for item in (contrast.get("same_visible_outcome_support_chain_ids") or []) if _clean(item)))
        counter_ids = sorted(set(_clean(item) for item in (contrast.get("different_visible_outcome_analogue_chain_ids") or []) if _clean(item)))
        if support_ids and counter_ids:
            evidence_state = "SUPPORT_AND_COUNTEREVIDENCE_VISIBLE_CANDIDATE"
        elif counter_ids:
            evidence_state = "COUNTEREVIDENCE_VISIBLE_CANDIDATE"
        elif support_ids:
            evidence_state = "DEPENDENT_SUPPORT_VISIBLE_NO_COUNTEREXAMPLE_CANDIDATE"
        else:
            evidence_state = "ISOLATED_VISIBLE_PROCESS_NO_ANALOGUE_CANDIDATE"

        analogue_ids = sorted(set(support_ids) | set(counter_ids))
        segment_metadata = _segment_scope_metadata(chain_id, analogue_ids, scope_by_chain_id)
        counter_metadata = _counter_search_metadata(
            support_ids,
            counter_ids,
            segment_scope_evaluated=segment_metadata["segment_scope_evaluated"] is True,
        )

        inputs.append({
            "defeasible_process_finding_input_id": "dfi_" + _digest(contrast_id, chain_id, support_ids, counter_ids)[:24],
            "outcome_contrast_candidate_id": contrast_id,
            "reciprocal_process_chain_candidate_id": chain_id,
            "process_family_signature_candidate": contrast.get("process_family_signature_candidate") or {},
            "process_episode_scope_signature_candidate": contrast.get("process_episode_scope_signature_candidate"),
            "visible_outcome_signature_candidate": contrast.get("visible_outcome_signature_candidate") or {},
            "dependent_support_chain_ids": support_ids,
            "counterevidence_chain_ids": counter_ids,
            "evidence_balance_state_candidate": evidence_state,
            **segment_metadata,
            **counter_metadata,
            "no_visible_counterexample_is_confirmation": False,
            "support_links_are_independent_votes": False,
            "counterevidence_links_are_independent_votes": False,
            "finding_emitted": False,
            "allowed_claim": "This object packages one visible reciprocal process candidate with same-signature dependent support and different-outcome counterevidence for downstream defeasible finding composition.",
            "forbidden_inference": [
                "causality",
                "tactical truth",
                "expected outcome probability",
                "effect size",
                "stable team tendency",
                "coach intention",
                "adaptation truth",
                "dominance",
                "recurrence truth",
                "pattern robustness truth",
            ],
            "withdrawal_condition": "Withdraw or downgrade if the source reciprocal chain, contrast grouping, support/counterevidence linkage, temporal relation, or episode binding is invalidated.",
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "claim_ceiling": FINDING_INPUT_CLAIM_CEILING,
        })

    return {
        "defeasible_process_finding_inputs": inputs,
        "defeasible_process_finding_input_count": len(inputs),
        "finding_input_status": "PASS" if inputs else "NO_ELIGIBLE_FINDING_INPUTS",
        "finding_input_claim_ceiling": FINDING_INPUT_CLAIM_CEILING,
        "finding_input_is_final_finding": False,
        "finding_input_is_independent_evidence": False,
        "counter_search_complete_for_final_finding": False,
        "alternative_explanation_search_required": True,
        "segment_falsifier_method": SEGMENT_FALSIFIER_METHOD,
        "segment_scope_is_recurrence_truth": False,
        "segment_scope_is_pattern_robustness_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def _dependent_sequence_ref(ref_id: str, role: str) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "source_surface": "RECIPROCAL_PROCESS_CHAIN_CANDIDATE",
        "evidence_role": role,
        "dependency_group": "same_upstream_reciprocal_process_population",
        "independent_support_vote": False,
    }


def _counter_signal_ref(ref_id: str) -> dict[str, Any]:
    return {
        "signal_ref": ref_id,
        "source_surface": "RECIPROCAL_OUTCOME_CONTRAST_CANDIDATE",
        "relation_type": "CONTRADICTS",
        "explicit_contradiction": True,
        "contradiction_basis": "same admitted process-family signature with different visible outcome signature candidate",
        "dependency_group": "same_upstream_reciprocal_process_population",
        "independent_support_vote": False,
    }


def build_c4_packet_candidates(finding_payload: dict[str, Any]) -> dict[str, Any]:
    """Adapt reciprocal finding inputs to the existing C4 composite packet contract.

    This is an adapter, not a new reasoning engine. Only finding inputs with at
    least one admitted analogue are emitted because the existing composite packet
    contract requires at least two distinct evidence refs. All refs remain
    dependent projections of the same upstream reciprocal process population.
    """
    inputs = finding_payload.get("defeasible_process_finding_inputs") or []
    if finding_payload.get("finding_input_status") == "FAIL_CLOSED" or not isinstance(inputs, list):
        return {
            "reciprocal_c4_packet_candidates": [],
            "reciprocal_c4_packet_candidate_count": 0,
            "reciprocal_c4_adapter_status": "FAIL_CLOSED",
            "reciprocal_c4_adapter_claim_ceiling": C4_PACKET_CLAIM_CEILING,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    candidates: list[dict[str, Any]] = []
    for row in inputs:
        if not isinstance(row, dict):
            continue
        finding_id = _clean(row.get("defeasible_process_finding_input_id"))
        chain_id = _clean(row.get("reciprocal_process_chain_candidate_id"))
        support_ids = sorted(set(_clean(item) for item in (row.get("dependent_support_chain_ids") or []) if _clean(item)))
        counter_ids = sorted(set(_clean(item) for item in (row.get("counterevidence_chain_ids") or []) if _clean(item)))
        if not finding_id or not chain_id or not (support_ids or counter_ids):
            continue

        safety_metadata = _claim_safety_metadata(row)
        candidates.append({
            "packet_id": "cep_reciprocal_" + _digest(finding_id, chain_id, support_ids, counter_ids)[:20],
            "packet_family": "sequence",
            "input_features": [],
            "input_windows": [],
            "input_sequences": [
                _dependent_sequence_ref(chain_id, "anchor_reciprocal_process_candidate"),
                *[_dependent_sequence_ref(ref_id, "same_outcome_dependent_support_candidate") for ref_id in support_ids],
            ],
            "input_metrics": [],
            "supporting_signals": [],
            "contradicting_signals": [_counter_signal_ref(ref_id) for ref_id in counter_ids],
            "claim_ceiling": C4_PACKET_CLAIM_CEILING,
            "report_consumers": [
                "multi_signal_evidence_fusion_lite",
                "composite_argument_builder_lite",
                "defeasible_argument_router_lite",
                "evidence_graph_engine_lite",
                "active_match_analyst_report_lite",
            ],
            "blocked_language_families": [
                "tactical_truth",
                "dominance_truth",
                "control_truth",
                "coach_intention",
                "off_ball_truth",
                "pitch_control_truth",
                "causal_truth",
                "quality_truth",
                "sequence_truth",
            ],
            "source_finding_input_id": finding_id,
            "source_outcome_contrast_candidate_id": row.get("outcome_contrast_candidate_id"),
            "process_family_signature_candidate": row.get("process_family_signature_candidate") or {},
            "process_episode_scope_signature_candidate": row.get("process_episode_scope_signature_candidate"),
            "visible_outcome_signature_candidate": row.get("visible_outcome_signature_candidate") or {},
            "counter_search_scope_state": row.get("counter_search_scope_state"),
            "counter_search_complete_for_final_finding": False,
            "alternative_explanation_search_state": row.get("alternative_explanation_search_state"),
            "falsifier_coverage_state": row.get("falsifier_coverage_state"),
            "segment_scope_state": row.get("segment_scope_state"),
            "segment_falsifier_state": row.get("segment_falsifier_state"),
            "claim_safety_metadata": safety_metadata,
            "dependent_support_only": True,
            "counterevidence_is_dependent_projection": True,
            "finding_emitted": False,
            "claim_output_allowed": False,
            "report_language_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        })

    return {
        "reciprocal_c4_packet_candidates": candidates,
        "reciprocal_c4_packet_candidate_count": len(candidates),
        "reciprocal_c4_adapter_status": "PASS" if candidates else "NO_ELIGIBLE_ANALOGUE_PACKET_CANDIDATES",
        "reciprocal_c4_adapter_claim_ceiling": C4_PACKET_CLAIM_CEILING,
        "reciprocal_c4_adapter_creates_new_engine": False,
        "reciprocal_c4_adapter_creates_independent_evidence": False,
        "reciprocal_c4_adapter_emits_final_finding": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def attach_outcome_contrast(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    output = dict(reciprocal_payload)
    contrast_payload = build_outcome_contrast_candidates(reciprocal_payload)
    output.update(contrast_payload)
    finding_payload = build_defeasible_process_finding_inputs(contrast_payload)
    output.update(finding_payload)
    output.update(build_c4_packet_candidates(finding_payload))
    output["outcome_contrast_is_independent_evidence"] = False
    output["production_release"] = False
    output["canonical_event_count"] = CANONICAL_EVENT_COUNT
    output["true_action_count"] = TRUE_ACTION_COUNT
    return output
