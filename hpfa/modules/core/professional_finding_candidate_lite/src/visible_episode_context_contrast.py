from __future__ import annotations

import json
from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
RECIPROCAL_MODULE_ID = "reciprocal_process_chain_lite_v1"
ACTIVITY_MODULE_ID = "team_episode_activity_lens_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _positive_keys(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    out: list[str] = []
    for key, raw in value.items():
        try:
            count = int(raw)
        except (TypeError, ValueError):
            continue
        text = _clean(key)
        if text and count > 0:
            out.append(text)
    return tuple(sorted(set(out)))


def _outcome_signature(chain: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    return (
        _positive_keys(chain.get("response_consequence_candidate_counts")),
        _positive_keys(chain.get("counter_response_consequence_candidate_counts")),
        bool(chain.get("counter_response_visible")),
    )


def _outcome_object(signature: tuple[tuple[str, ...], tuple[str, ...], bool]) -> dict[str, Any]:
    return {
        "response_consequence_families": list(signature[0]),
        "counter_response_consequence_families": list(signature[1]),
        "counter_response_visible": signature[2],
    }


def _activity_signature(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    return {
        "period_candidate": row.get("period_candidate"),
        "visible_activity_signals_present": sorted(
            {_clean(value) for value in (row.get("visible_activity_signals_present") or []) if _clean(value)}
        ),
        "action_families_present": list(_positive_keys(row.get("action_family_candidate_counts"))),
        "zones_present": list(_positive_keys(row.get("zone_candidate_counts"))),
        "channels_present": list(_positive_keys(row.get("channel_candidate_counts"))),
    }


def _fingerprint(value: dict[str, Any] | None) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _find_context_alt(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict) and row.get("type") == "CONTEXT_DEPENDENCE":
            return row
    return None


def attach_visible_episode_context_contrast(
    finding_payload: dict[str, Any],
    reciprocal_payload: dict[str, Any],
    activity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Attach current visible episode-activity context to existing finding candidates.

    This is a dependent projection over already-admitted episode/team activity and
    reciprocal process candidates. It compares co-occurring visible context across
    different visible outcome variants. It does not classify success/failure, infer
    causality, create a tactical phase, or open final finding output.
    """
    blocks: list[str] = []
    reviews: list[str] = []
    for label, payload, module_id in (
        ("finding", finding_payload, FINDING_MODULE_ID),
        ("reciprocal", reciprocal_payload, RECIPROCAL_MODULE_ID),
        ("activity", activity_payload, ACTIVITY_MODULE_ID),
    ):
        if payload.get("module_id") != module_id:
            blocks.append(f"{label}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")
        if _status(payload.get("status")) == "FAIL_CLOSED" or payload.get("hard_block_hits"):
            blocks.append(f"{label}_input_fail_closed")
        elif _status(payload.get("status")) == "REVIEW_REQUIRED":
            reviews.append(f"{label}_upstream_review_required")

    result = dict(finding_payload)
    result["professional_finding_candidates"] = [
        dict(row) for row in (finding_payload.get("professional_finding_candidates") or []) if isinstance(row, dict)
    ]

    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["context_contrast_status"] = "FAIL_CLOSED"
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
    activity_by_episode_team = {
        (_clean(row.get("episode_candidate_id")), _clean(row.get("team_identity_candidate_id"))): row
        for row in (activity_payload.get("team_episode_activity_rows") or [])
        if isinstance(row, dict)
        and _clean(row.get("episode_candidate_id"))
        and _clean(row.get("team_identity_candidate_id"))
    }

    fully_covered = 0
    variation_visible = 0
    partial_coverage = 0

    for row in result["professional_finding_candidates"]:
        support = row.get("support") if isinstance(row.get("support"), dict) else {}
        chain_ids = [
            _clean(value)
            for value in (support.get("supporting_reciprocal_process_chain_candidate_ids") or [])
            if _clean(value)
        ]
        grouped: dict[str, dict[str, Any]] = {}
        covered_chain_count = 0

        for chain_id in chain_ids:
            chain = chain_by_id.get(chain_id)
            if not isinstance(chain, dict):
                continue
            anchor = activity_by_episode_team.get((
                _clean(chain.get("anchor_episode_candidate_id")),
                _clean(chain.get("anchor_team_identity_candidate_id")),
            ))
            response = activity_by_episode_team.get((
                _clean(chain.get("response_episode_candidate_id")),
                _clean(chain.get("response_team_identity_candidate_id")),
            ))
            counter = None
            if chain.get("counter_response_visible") is True:
                counter = activity_by_episode_team.get((
                    _clean(chain.get("counter_response_episode_candidate_id")),
                    _clean(chain.get("counter_response_team_identity_candidate_id")),
                ))

            anchor_sig = _activity_signature(anchor)
            response_sig = _activity_signature(response)
            counter_sig = _activity_signature(counter) if chain.get("counter_response_visible") is True else {
                "state": "NO_VISIBLE_COUNTER_RESPONSE"
            }
            complete = anchor_sig is not None and response_sig is not None and (
                chain.get("counter_response_visible") is not True or counter_sig is not None
            )
            if complete:
                covered_chain_count += 1

            context = {
                "anchor_episode_activity": anchor_sig,
                "response_episode_activity": response_sig,
                "counter_response_episode_activity": counter_sig,
            }
            outcome = _outcome_signature(chain)
            outcome_key = json.dumps(_outcome_object(outcome), sort_keys=True, separators=(",", ":"))
            bucket = grouped.setdefault(outcome_key, {
                "visible_outcome_signature_candidate": _outcome_object(outcome),
                "chain_ids": [],
                "context_fingerprints": set(),
                "context_examples": [],
            })
            bucket["chain_ids"].append(chain_id)
            if complete:
                fp = _fingerprint(context)
                bucket["context_fingerprints"].add(fp)
                if len(bucket["context_examples"]) < 3:
                    bucket["context_examples"].append(context)

        outcome_groups = list(grouped.values())
        if len(outcome_groups) <= 1:
            context_state = "NOT_APPLICABLE_SINGLE_VISIBLE_OUTCOME"
        elif covered_chain_count < len(chain_ids):
            context_state = "PARTIAL_CONTEXT_COVERAGE_REVIEW_REQUIRED"
            partial_coverage += 1
        else:
            signature_sets = [frozenset(group["context_fingerprints"]) for group in outcome_groups]
            if len(set(signature_sets)) <= 1:
                context_state = "NO_VISIBLE_EPISODE_CONTEXT_DIFFERENCE_AT_CURRENT_RESOLUTION"
            else:
                context_state = "VISIBLE_EPISODE_CONTEXT_VARIATION_ACROSS_OUTCOMES_CANDIDATE"
                variation_visible += 1
            fully_covered += 1

        serializable_groups = []
        for group in outcome_groups:
            serializable_groups.append({
                "visible_outcome_signature_candidate": group["visible_outcome_signature_candidate"],
                "chain_ids": sorted(group["chain_ids"]),
                "distinct_visible_episode_context_count_candidate": len(group["context_fingerprints"]),
                "visible_episode_context_examples": group["context_examples"],
            })

        contrast = {
            "state_candidate": context_state,
            "supported_chain_count": len(chain_ids),
            "context_covered_chain_count": covered_chain_count,
            "visible_outcome_group_count": len(outcome_groups),
            "outcome_context_groups": serializable_groups,
            "scope": "ADMITTED_TEAM_EPISODE_VISIBLE_ACTIVITY_ONLY",
            "uses_presence_not_uncalibrated_threshold": True,
            "context_difference_is_causal_explanation": False,
            "context_difference_is_tactical_truth": False,
            "absence_of_visible_context_difference_disproves_context_dependence": False,
            "off_ball_context_requires_video_or_tracking": True,
        }

        challenge = dict(row.get("finding_challenge_packet") or {})
        evaluated = list(challenge.get("evaluated_falsifier_families") or [])
        if "VISIBLE_EPISODE_CONTEXT_CONTRAST" not in evaluated:
            evaluated.append("VISIBLE_EPISODE_CONTEXT_CONTRAST")
        challenge["evaluated_falsifier_families"] = evaluated
        challenge["visible_episode_context_contrast"] = contrast
        challenge["context_dependence_search_complete_for_final_finding"] = False
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["alternative_explanation_search_complete"] = False
        challenge["challenge_packet_is_final_finding"] = False
        row["finding_challenge_packet"] = challenge

        alternatives = [dict(item) for item in (row.get("alternative_explanations") or []) if isinstance(item, dict)]
        context_alt = _find_context_alt(alternatives)
        if context_alt is None:
            context_alt = {"type": "CONTEXT_DEPENDENCE"}
            alternatives.append(context_alt)
        context_alt["state"] = "PARTIALLY_EVALUATED_VISIBLE_EPISODE_ACTIVITY_SCOPE"
        context_alt["visible_episode_context_contrast_state_candidate"] = context_state
        context_alt["broader_context_search_complete"] = False
        row["alternative_explanations"] = alternatives

        uncertainty = dict(row.get("uncertainty") or {})
        uncertainty["visible_episode_context_coverage_complete_for_current_scope"] = (
            covered_chain_count == len(chain_ids) and bool(chain_ids)
        )
        uncertainty["context_dependence_search_complete_for_final_finding"] = False
        row["uncertainty"] = uncertainty
        row["claim_output_allowed"] = False
        row["professional_finding_emitted"] = False

    result["context_contrast_status"] = "REVIEW_REQUIRED"
    result["context_contrast_evaluated_candidate_count"] = len(result["professional_finding_candidates"])
    result["context_contrast_full_coverage_candidate_count"] = fully_covered
    result["context_contrast_partial_coverage_candidate_count"] = partial_coverage
    result["findings_with_visible_context_variation_candidate_count"] = variation_visible
    result["context_dependence_search_complete_for_final_finding"] = False
    result["review_hits"] = sorted(set((finding_payload.get("review_hits") or []) + reviews))
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
