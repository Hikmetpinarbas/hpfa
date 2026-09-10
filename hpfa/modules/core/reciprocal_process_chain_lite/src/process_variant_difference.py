from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any

CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_PROCESS_VARIANT_DIFFERENCE_CANDIDATE_ONLY"
NON_COMPARABLE = {
    "RIGHT_CENSORED_OBSERVATION_VARIANT",
    "UNRESOLVED_VISIBLE_PROCESS_VARIANT",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value and value not in {float("inf"), float("-inf")} else None


def _resolution_class(row: dict[str, Any]) -> str:
    labels = {
        _clean(key).upper()
        for field in ("response_consequence_candidate_counts", "counter_response_consequence_candidate_counts")
        for key in (row.get(field) or {})
        if _clean(key)
    }
    if any("RIGHT_CENSORED" in value for value in labels):
        return "RIGHT_CENSORED_OBSERVATION_VARIANT"
    if any(marker in value for value in labels for marker in ("UNCERTAIN", "NO_VISIBLE_FOLLOW_UP", "MIXED_TEAM_SAME_TIME")):
        return "UNRESOLVED_VISIBLE_PROCESS_VARIANT"
    if any("RECOVERY_RESPONSE_AFTER_BREAKDOWN" in value for value in labels):
        return "RECOVERY_AFTER_BREAKDOWN_VISIBLE_VARIANT"
    if any("RESTART" in value or "RESET" in value for value in labels):
        return "RESET_OR_RESTART_VISIBLE_VARIANT"
    if any("OPPONENT_HANDOVER" in value or "OPPONENT_TAKEOVER" in value or "LOSS" in value for value in labels):
        return "ADVERSE_HANDOVER_VISIBLE_VARIANT"
    if any(marker in value for value in labels for marker in ("SHOT_FOLLOW_UP", "SAME_TEAM_CONTINUATION", "RECOVERY_TO_SAME_TEAM_CONTINUATION", "CONTINUATION_VISIBLE")):
        return "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT"
    if any("TERMINAL_OUTCOME_SUPPORT" in value for value in labels):
        return "TERMINAL_VISIBLE_VARIANT"
    return "OTHER_VISIBLE_CONSEQUENCE_VARIANT"


def _family(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(sorted(_clean(k) for k in (row.get("anchor_action_family_counts") or {}) if _clean(k))),
        tuple(sorted(_clean(k) for k in (row.get("response_action_family_counts") or {}) if _clean(k))),
    )


def _cohort_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [_number(row.get("response_latency_candidate_seconds")) for row in rows]
    latencies = [value for value in latencies if value is not None]
    counter_families: Counter[str] = Counter()
    response_consequences: Counter[str] = Counter()
    counter_consequences: Counter[str] = Counter()
    episode_scopes: set[tuple[str, str, str]] = set()
    chain_ids: list[str] = []
    for row in rows:
        chain_id = _clean(row.get("reciprocal_process_chain_candidate_id"))
        if chain_id:
            chain_ids.append(chain_id)
        for key, value in (row.get("counter_response_action_family_counts") or {}).items():
            if _clean(key) and int(value or 0) > 0:
                counter_families[_clean(key)] += 1
        for field, target in (("response_consequence_candidate_counts", response_consequences), ("counter_response_consequence_candidate_counts", counter_consequences)):
            for key, value in (row.get(field) or {}).items():
                if _clean(key) and int(value or 0) > 0:
                    target[_clean(key)] += 1
        scope = (
            _clean(row.get("anchor_episode_candidate_id")),
            _clean(row.get("response_episode_candidate_id")),
            _clean(row.get("counter_response_episode_candidate_id")) if row.get("counter_response_visible") else "NO_VISIBLE_COUNTER_RESPONSE",
        )
        if scope[0] and scope[1] and scope[2]:
            episode_scopes.add(scope)
    return {
        "chain_candidate_ids": sorted(set(chain_ids)),
        "chain_count_candidate": len(rows),
        "response_latency_median_candidate_seconds": round(median(latencies), 6) if latencies else None,
        "response_latency_observed_count": len(latencies),
        "counter_response_visible_count": sum(bool(row.get("counter_response_visible")) for row in rows),
        "counter_response_action_family_presence_counts": dict(sorted(counter_families.items())),
        "response_consequence_family_presence_counts": dict(sorted(response_consequences.items())),
        "counter_response_consequence_family_presence_counts": dict(sorted(counter_consequences.items())),
        "episode_scope_count_candidate": len(episode_scopes),
    }


def build_process_variant_difference_explanations(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    records = [row for row in (reciprocal_payload.get("reciprocal_process_chain_candidates") or []) if isinstance(row, dict)]
    if _clean(reciprocal_payload.get("status")).upper() == "FAIL_CLOSED" or not records:
        return {
            "process_variant_difference_explanations": [],
            "process_variant_difference_explanation_count": 0,
            "status": "FAIL_CLOSED" if _clean(reciprocal_payload.get("status")).upper() == "FAIL_CLOSED" else "NO_ELIGIBLE_COMPARISON",
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    families: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict[str, Any]]] = {}
    for row in records:
        families.setdefault(_family(row), []).append(row)

    out: list[dict[str, Any]] = []
    for family, rows in sorted(families.items(), key=lambda item: repr(item[0])):
        by_resolution: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            state = _resolution_class(row)
            if state in NON_COMPARABLE:
                continue
            by_resolution.setdefault(state, []).append(row)
        if len(by_resolution) < 2:
            continue
        counts = {state: len(group) for state, group in by_resolution.items()}
        maximum = max(counts.values())
        leaders = sorted(state for state, count in counts.items() if count == maximum)
        if len(leaders) != 1:
            continue
        modal = leaders[0]
        modal_summary = _cohort_summary(by_resolution[modal])
        for deviant in sorted(state for state in by_resolution if state != modal):
            deviant_summary = _cohort_summary(by_resolution[deviant])
            visible_differences: list[dict[str, Any]] = []
            for field in (
                "response_latency_median_candidate_seconds",
                "counter_response_visible_count",
                "counter_response_action_family_presence_counts",
                "response_consequence_family_presence_counts",
                "counter_response_consequence_family_presence_counts",
                "episode_scope_count_candidate",
            ):
                if modal_summary.get(field) != deviant_summary.get(field):
                    visible_differences.append({
                        "observation_dimension": field,
                        "modal_candidate": modal_summary.get(field),
                        "deviant_candidate": deviant_summary.get(field),
                    })
            out.append({
                "process_family_signature_candidate": {
                    "anchor_action_families": list(family[0]),
                    "response_action_families": list(family[1]),
                },
                "modal_resolution_class_candidate": modal,
                "deviant_resolution_class_candidate": deviant,
                "modal_cohort": modal_summary,
                "deviant_cohort": deviant_summary,
                "visible_difference_candidates": visible_differences,
                "visible_difference_candidate_count": len(visible_differences),
                "analyst_question_candidate": "Which admitted match-local visible differences distinguish the modal process resolution from this deviant resolution?",
                "safe_meaning": "These are observed match-local differences between comparable resolution cohorts of the same process-family signature.",
                "alternative_explanations": ["SMALL_COHORT", "DEPENDENT_OBSERVATIONS", "UNOBSERVED_VIDEO_TRACKING_CONTEXT", "EPISODE_CONTEXT_DIFFERENCE"],
                "difference_is_causal_explanation": False,
                "difference_is_tactical_adaptation_truth": False,
                "difference_is_coach_intention_truth": False,
                "deviant_is_failure_truth": False,
                "right_censoring_used_as_counterevidence": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    return {
        "process_variant_difference_explanations": out,
        "process_variant_difference_explanation_count": len(out),
        "status": "PASS" if out else "NO_ELIGIBLE_COMPARISON",
        "right_censoring_used_as_counterevidence": False,
        "difference_is_causal_explanation": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
