from __future__ import annotations

from typing import Any

FINDING_MODULE_ID = "professional_finding_candidate_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
DEFAULT_REPEAT_THRESHOLDS = (2, 3, 4)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _find_threshold_alt(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict) and row.get("type") == "THRESHOLD_SENSITIVITY":
            return row
    return None


def attach_threshold_sensitivity(
    finding_payload: dict[str, Any],
    thresholds: tuple[int, ...] = DEFAULT_REPEAT_THRESHOLDS,
) -> dict[str, Any]:
    """Attach descriptive repeat-threshold perturbation to finding candidates.

    This does not calibrate a football threshold and does not convert recurrence into
    tactical truth. It only asks whether an already-eligible match-local repeat would
    remain eligible under stricter minimum-repeat gates.
    """
    result = dict(finding_payload)
    rows = [
        dict(row)
        for row in (finding_payload.get("professional_finding_candidates") or [])
        if isinstance(row, dict)
    ]
    result["professional_finding_candidates"] = rows

    blocks: list[str] = []
    if finding_payload.get("module_id") != FINDING_MODULE_ID:
        blocks.append("finding_module_id_mismatch")
    if finding_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("finding_canonical_event_count_claimed")
    if finding_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("finding_true_action_count_claimed")
    if finding_payload.get("production_release") is True:
        blocks.append("finding_production_release_claimed")
    if _status(finding_payload.get("status")) == "FAIL_CLOSED" or finding_payload.get("hard_block_hits"):
        blocks.append("finding_input_fail_closed")

    clean_thresholds = tuple(sorted({int(value) for value in thresholds if int(value) >= 2}))
    if not clean_thresholds:
        blocks.append("threshold_grid_empty")

    if blocks:
        result["status"] = "FAIL_CLOSED"
        result["threshold_sensitivity_status"] = "FAIL_CLOSED"
        result["hard_block_hits"] = sorted(set((finding_payload.get("hard_block_hits") or []) + blocks))
        result["claim_output_allowed_count"] = 0
        result["professional_finding_emitted_count"] = 0
        result["canonical_event_count"] = CANONICAL_EVENT_COUNT
        result["true_action_count"] = TRUE_ACTION_COUNT
        result["production_release"] = False
        return result

    stable_all = 0
    loses_under_stricter = 0
    not_evaluable = 0

    for row in rows:
        support = row.get("support") if isinstance(row.get("support"), dict) else {}
        try:
            repeat_count = int(support.get("visible_repeat_count_candidate"))
        except (TypeError, ValueError):
            repeat_count = 0

        evaluations = [
            {
                "minimum_repeat_threshold_candidate": threshold,
                "candidate_remains_repeat_eligible": repeat_count >= threshold,
            }
            for threshold in clean_thresholds
        ]

        if repeat_count < 2:
            state = "NOT_EVALUABLE_REPEAT_COUNT_BELOW_EXISTING_GATE"
            not_evaluable += 1
        elif all(item["candidate_remains_repeat_eligible"] for item in evaluations):
            state = "SURVIVES_ALL_TESTED_REPEAT_THRESHOLDS"
            stable_all += 1
        elif any(item["candidate_remains_repeat_eligible"] for item in evaluations):
            state = "SENSITIVE_TO_STRICTER_REPEAT_THRESHOLD"
            loses_under_stricter += 1
        else:
            state = "FAILS_TESTED_REPEAT_THRESHOLDS"
            loses_under_stricter += 1

        challenge = dict(row.get("finding_challenge_packet") or {})
        evaluated = list(challenge.get("evaluated_falsifier_families") or [])
        if "THRESHOLD_SENSITIVITY_REPEAT_GATE" not in evaluated:
            evaluated.append("THRESHOLD_SENSITIVITY_REPEAT_GATE")
        challenge["evaluated_falsifier_families"] = evaluated
        pending = [
            value for value in (challenge.get("pending_falsifier_families") or [])
            if value != "THRESHOLD_SENSITIVITY"
        ]
        challenge["pending_falsifier_families"] = pending
        challenge["threshold_sensitivity"] = {
            "state_candidate": state,
            "visible_repeat_count_candidate": repeat_count,
            "tested_minimum_repeat_thresholds": list(clean_thresholds),
            "threshold_evaluations": evaluations,
            "scope": "DESCRIPTIVE_MATCH_LOCAL_REPEAT_GATE_PERTURBATION_ONLY",
            "thresholds_are_calibrated": False,
            "thresholds_are_football_truth": False,
            "survival_proves_stable_pattern": False,
        }
        challenge["threshold_sensitivity_search_complete_for_current_repeat_gate_scope"] = True
        challenge["counter_search_complete_for_final_finding"] = False
        challenge["challenge_packet_is_final_finding"] = False
        row["finding_challenge_packet"] = challenge

        alternatives = [
            dict(item)
            for item in (row.get("alternative_explanations") or [])
            if isinstance(item, dict)
        ]
        threshold_alt = _find_threshold_alt(alternatives)
        if threshold_alt is None:
            threshold_alt = {"type": "THRESHOLD_SENSITIVITY"}
            alternatives.append(threshold_alt)
        threshold_alt["state"] = "EVALUATED_DESCRIPTIVE_REPEAT_GATE_PERTURBATION"
        threshold_alt["repeat_gate_sensitivity_state_candidate"] = state
        threshold_alt["calibrated_threshold_available"] = False
        row["alternative_explanations"] = alternatives

        uncertainty = dict(row.get("uncertainty") or {})
        uncertainty["repeat_gate_threshold_sensitivity_evaluated"] = True
        uncertainty["repeat_gate_thresholds_calibrated"] = False
        row["uncertainty"] = uncertainty
        row["claim_output_allowed"] = False
        row["professional_finding_emitted"] = False

    result["threshold_sensitivity_status"] = "REVIEW_REQUIRED"
    result["threshold_sensitivity_evaluated_candidate_count"] = len(rows)
    result["threshold_sensitivity_survives_all_tested_thresholds_count"] = stable_all
    result["threshold_sensitivity_stricter_gate_sensitive_count"] = loses_under_stricter
    result["threshold_sensitivity_not_evaluable_count"] = not_evaluable
    result["threshold_sensitivity_scope_complete"] = True
    result["threshold_sensitivity_calibrated"] = False
    result["status"] = "REVIEW_REQUIRED"
    result["claim_output_allowed_count"] = 0
    result["professional_finding_emitted_count"] = 0
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["true_action_count"] = TRUE_ACTION_COUNT
    result["production_release"] = False
    return result
