from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

CLAIM_CEILING = "RECIPROCAL_OUTCOME_CONTRAST_CANDIDATE_ONLY"
FINDING_INPUT_CLAIM_CEILING = "DEFEASIBLE_PROCESS_FINDING_INPUT_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


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

        inputs.append({
            "defeasible_process_finding_input_id": "dfi_" + _digest(contrast_id, chain_id, support_ids, counter_ids)[:24],
            "outcome_contrast_candidate_id": contrast_id,
            "reciprocal_process_chain_candidate_id": chain_id,
            "process_family_signature_candidate": contrast.get("process_family_signature_candidate") or {},
            "visible_outcome_signature_candidate": contrast.get("visible_outcome_signature_candidate") or {},
            "dependent_support_chain_ids": support_ids,
            "counterevidence_chain_ids": counter_ids,
            "evidence_balance_state_candidate": evidence_state,
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
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def attach_outcome_contrast(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    output = dict(reciprocal_payload)
    contrast_payload = build_outcome_contrast_candidates(reciprocal_payload)
    output.update(contrast_payload)
    output.update(build_defeasible_process_finding_inputs(contrast_payload))
    output["outcome_contrast_is_independent_evidence"] = False
    output["production_release"] = False
    output["canonical_event_count"] = CANONICAL_EVENT_COUNT
    output["true_action_count"] = TRUE_ACTION_COUNT
    return output
