from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "reciprocal_process_variant_profile_lite_v1"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_PROCESS_VARIANT_PROFILE_CANDIDATE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"

RIGHT_CENSORED_MARKERS = {"RIGHT_CENSORED_NO_VISIBLE_FOLLOW_UP_CANDIDATE"}
UNRESOLVED_MARKERS = {
    "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _family_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    anchor = tuple(
        sorted(_clean(key) for key in (row.get("anchor_action_family_counts") or {}) if _clean(key))
    )
    response = tuple(
        sorted(_clean(key) for key in (row.get("response_action_family_counts") or {}) if _clean(key))
    )
    return anchor, response


def _outcome_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    response = tuple(
        sorted(
            _clean(key)
            for key in (row.get("response_consequence_candidate_counts") or {})
            if _clean(key)
        )
    )
    counter = tuple(
        sorted(
            _clean(key)
            for key in (row.get("counter_response_consequence_candidate_counts") or {})
            if _clean(key)
        )
    )
    return response, counter, bool(row.get("counter_response_visible"))


def _outcome_object(signature: tuple[tuple[str, ...], tuple[str, ...], bool]) -> dict[str, Any]:
    return {
        "response_consequence_families": list(signature[0]),
        "counter_response_consequence_families": list(signature[1]),
        "counter_response_visible": signature[2],
    }


def _episode_scope(row: dict[str, Any]) -> tuple[str, str, str] | None:
    anchor = _clean(row.get("anchor_episode_candidate_id"))
    response = _clean(row.get("response_episode_candidate_id"))
    counter_visible = bool(row.get("counter_response_visible"))
    counter = _clean(row.get("counter_response_episode_candidate_id"))
    if not anchor or not response:
        return None
    if counter_visible and not counter:
        return None
    return anchor, response, counter if counter_visible else "NO_VISIBLE_COUNTER_RESPONSE"


def _scope_object(scope: tuple[str, str, str]) -> dict[str, str]:
    return {
        "anchor_episode_candidate_id": scope[0],
        "response_episode_candidate_id": scope[1],
        "counter_response_episode_candidate_id": scope[2],
    }


def _resolution_class(signature: tuple[tuple[str, ...], tuple[str, ...], bool]) -> str:
    """Map already-visible consequence labels to football-functional resolution roles.

    This is descriptive process resolution, not tactical success/failure truth. It is
    deliberately outcome-family based so downstream analysts can see how otherwise
    similar match-local processes resolve without inventing intent or causality.
    """
    labels = {value.upper() for value in (*signature[0], *signature[1]) if value}
    if labels & RIGHT_CENSORED_MARKERS or any("RIGHT_CENSORED" in value for value in labels):
        return "RIGHT_CENSORED_OBSERVATION_VARIANT"
    if labels & UNRESOLVED_MARKERS or any(
        marker in value
        for value in labels
        for marker in ("UNCERTAIN", "NO_VISIBLE_FOLLOW_UP", "MIXED_TEAM_SAME_TIME")
    ):
        return "UNRESOLVED_VISIBLE_PROCESS_VARIANT"
    if any("RECOVERY_RESPONSE_AFTER_BREAKDOWN" in value for value in labels):
        return "RECOVERY_AFTER_BREAKDOWN_VISIBLE_VARIANT"
    if any("RESTART_OR_RESET" in value or "RESTART" in value or "RESET" in value for value in labels):
        return "RESET_OR_RESTART_VISIBLE_VARIANT"
    if any("OPPONENT_HANDOVER" in value or "OPPONENT_TAKEOVER" in value or "LOSS" in value for value in labels):
        return "ADVERSE_HANDOVER_VISIBLE_VARIANT"
    if any(
        marker in value
        for value in labels
        for marker in (
            "SHOT_FOLLOW_UP",
            "SAME_TEAM_CONTINUATION",
            "RECOVERY_TO_SAME_TEAM_CONTINUATION",
            "CONTINUATION_VISIBLE",
        )
    ):
        return "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT"
    if any("TERMINAL_OUTCOME_SUPPORT" in value for value in labels):
        return "TERMINAL_VISIBLE_VARIANT"
    return "OTHER_VISIBLE_CONSEQUENCE_VARIANT"


def _resolution_profile(
    outcome_counts: Counter[tuple[tuple[str, ...], tuple[str, ...], bool]],
) -> tuple[list[dict[str, Any]], int, str | None, list[str]]:
    class_counts: Counter[str] = Counter()
    for signature, count in outcome_counts.items():
        class_counts[_resolution_class(signature)] += count

    non_comparable = {
        "RIGHT_CENSORED_OBSERVATION_VARIANT",
        "UNRESOLVED_VISIBLE_PROCESS_VARIANT",
    }
    comparable_denominator = sum(
        count for state, count in class_counts.items() if state not in non_comparable
    )
    total = sum(class_counts.values())
    rows: list[dict[str, Any]] = []
    for state, count in sorted(class_counts.items()):
        comparable = state not in non_comparable
        rows.append({
            "process_resolution_class_candidate": state,
            "chain_count_candidate": count,
            "within_profile_share_candidate": round(count / total, 6) if total else None,
            "within_comparable_resolution_share_candidate": (
                round(count / comparable_denominator, 6)
                if comparable and comparable_denominator
                else None
            ),
            "comparable_for_modal_deviation_candidate": comparable,
        })

    comparable_counts = {
        state: count for state, count in class_counts.items() if state not in non_comparable
    }
    dominant: str | None = None
    deviants: list[str] = []
    if comparable_counts:
        max_count = max(comparable_counts.values())
        leaders = sorted(state for state, count in comparable_counts.items() if count == max_count)
        if len(leaders) == 1:
            dominant = leaders[0]
            deviants = sorted(state for state in comparable_counts if state != dominant)
    return rows, comparable_denominator, dominant, deviants


def build_process_variant_profiles(reciprocal_payload: dict[str, Any]) -> dict[str, Any]:
    """Profile match-local repeated reciprocal process signatures and visible outcomes.

    This is a dependent descriptive projection over already-admitted reciprocal
    process candidates. It does not create actions, episodes, sequence truth,
    recurrence truth, tactical patterns, probabilities, or independent evidence.
    """
    upstream_status = _status(reciprocal_payload.get("status"))
    records = reciprocal_payload.get("reciprocal_process_chain_candidates") or []
    if upstream_status == "FAIL_CLOSED" or not isinstance(records, list):
        return {
            "module_id": MODULE_ID,
            "process_variant_profiles": [],
            "process_variant_profile_count": 0,
            "process_variant_profile_status": "FAIL_CLOSED",
            "upstream_reciprocal_status": upstream_status,
            "process_variant_profile_claim_ceiling": CLAIM_CEILING,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }

    groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    eligible_records: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        chain_id = _clean(row.get("reciprocal_process_chain_candidate_id"))
        signature = _family_signature(row)
        if not chain_id or not any(signature):
            continue
        groups[signature].append(row)
        eligible_records.append(row)

    eligible_population = len(eligible_records)
    profiles: list[dict[str, Any]] = []

    for family_signature, group in sorted(groups.items(), key=lambda item: repr(item[0])):
        chain_ids = sorted(
            {
                _clean(row.get("reciprocal_process_chain_candidate_id"))
                for row in group
                if _clean(row.get("reciprocal_process_chain_candidate_id"))
            }
        )
        episode_scopes = sorted(
            {scope for row in group if (scope := _episode_scope(row)) is not None}
        )
        incomplete_episode_binding_count = sum(_episode_scope(row) is None for row in group)
        outcome_counts: Counter[tuple[tuple[str, ...], tuple[str, ...], bool]] = Counter(
            _outcome_signature(row) for row in group
        )

        occurrence_count = len(group)
        unique_episode_scope_count = len(episode_scopes)
        distinct_outcome_count = len(outcome_counts)

        if occurrence_count <= 1:
            repeat_state = "SINGLE_INSTANCE_NOT_RECURRENCE"
        elif incomplete_episode_binding_count:
            repeat_state = "REPEATED_VISIBLE_PROCESS_INCOMPLETE_EPISODE_BINDING_REVIEW_REQUIRED"
        elif unique_episode_scope_count <= 1:
            repeat_state = "SINGLE_EPISODE_SCOPE_REPEAT_CANDIDATE"
        else:
            repeat_state = "MULTI_EPISODE_SCOPE_REPEAT_CANDIDATE"

        if distinct_outcome_count <= 1:
            variation_state = "SAME_VISIBLE_OUTCOME_SIGNATURE_ONLY_CANDIDATE"
        else:
            variation_state = "MULTIPLE_VISIBLE_OUTCOME_SIGNATURES_CANDIDATE"

        outcome_profile = []
        for signature, count in sorted(outcome_counts.items(), key=lambda item: repr(item[0])):
            outcome_profile.append({
                "visible_outcome_signature_candidate": _outcome_object(signature),
                "chain_count_candidate": count,
                "within_variant_share_candidate": round(count / occurrence_count, 6) if occurrence_count else None,
                "process_resolution_class_candidate": _resolution_class(signature),
            })

        resolution_profile, comparable_resolution_count, dominant_resolution, deviant_resolutions = _resolution_profile(
            outcome_counts
        )
        censored_count = sum(
            row["chain_count_candidate"]
            for row in resolution_profile
            if row["process_resolution_class_candidate"] == "RIGHT_CENSORED_OBSERVATION_VARIANT"
        )
        unresolved_count = sum(
            row["chain_count_candidate"]
            for row in resolution_profile
            if row["process_resolution_class_candidate"] == "UNRESOLVED_VISIBLE_PROCESS_VARIANT"
        )

        segment_only_risk = (
            occurrence_count > 1
            and incomplete_episode_binding_count == 0
            and unique_episode_scope_count <= 1
        )
        multi_episode_spread = (
            occurrence_count > 1
            and incomplete_episode_binding_count == 0
            and unique_episode_scope_count > 1
        )

        profiles.append({
            "process_variant_profile_candidate_id": "pvp_" + _digest(family_signature)[:24],
            "process_family_signature_candidate": {
                "anchor_action_families": list(family_signature[0]),
                "response_action_families": list(family_signature[1]),
            },
            "reciprocal_process_chain_candidate_ids": chain_ids,
            "visible_repeat_count_candidate": occurrence_count,
            "eligible_reciprocal_population_count": eligible_population,
            "trace_variant_frequency_candidate": (
                round(occurrence_count / eligible_population, 6) if eligible_population else None
            ),
            "unique_episode_scope_count_candidate": unique_episode_scope_count,
            "episode_scope_candidates": [_scope_object(scope) for scope in episode_scopes],
            "incomplete_episode_binding_count": incomplete_episode_binding_count,
            "repeat_scope_state_candidate": repeat_state,
            "distinct_visible_outcome_signature_count_candidate": distinct_outcome_count,
            "visible_outcome_profile_candidate": outcome_profile,
            "visible_outcome_variation_state_candidate": variation_state,
            "process_resolution_variant_profile_candidate": resolution_profile,
            "comparable_visible_resolution_count_candidate": comparable_resolution_count,
            "right_censored_resolution_count_candidate": censored_count,
            "unresolved_resolution_count_candidate": unresolved_count,
            "dominant_process_resolution_class_candidate": dominant_resolution,
            "deviant_process_resolution_classes_candidate": deviant_resolutions,
            "dominant_resolution_state_candidate": (
                "UNIQUE_MATCH_LOCAL_MODAL_RESOLUTION_CANDIDATE"
                if dominant_resolution
                else "NO_UNIQUE_MATCH_LOCAL_MODAL_RESOLUTION"
            ),
            "success_failure_classification_state_candidate": "REQUIRES_FAMILY_SPECIFIC_TARGET_CONSEQUENCE_DEFINITION",
            "segment_only_risk_candidate": segment_only_risk,
            "multi_episode_spread_visible_candidate": multi_episode_spread,
            "dependent_projection_only": True,
            "independent_evidence_vote": False,
            "repeat_candidate_is_recurrence_truth": False,
            "multi_episode_spread_is_stable_tendency_truth": False,
            "outcome_variation_is_tactical_flexibility_truth": False,
            "dominant_resolution_is_tactical_preference_truth": False,
            "deviant_resolution_is_failure_truth": False,
            "trace_variant_frequency_is_probability_truth": False,
            "allowed_claim": "The same admitted match-local anchor/response action-family signature was visible this many times, across these admitted episode scopes, with these visible process-resolution variants and match-local modal/deviant resolution candidates.",
            "forbidden_inference": [
                "recurrence truth",
                "stable team tendency",
                "coach intention",
                "rehearsed mechanism",
                "tactical flexibility truth",
                "causal efficacy",
                "expected outcome probability",
                "possession truth",
                "sequence truth",
                "dominance",
            ],
            "withdrawal_condition": "Withdraw or downgrade if family-signature admission, reciprocal-chain eligibility, episode binding, consequence signature, reflection control, or temporal ordering is invalidated.",
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "claim_ceiling": CLAIM_CEILING,
        })

    repeated = sum(profile["visible_repeat_count_candidate"] > 1 for profile in profiles)
    multi_episode = sum(profile["multi_episode_spread_visible_candidate"] for profile in profiles)
    segment_only = sum(profile["segment_only_risk_candidate"] for profile in profiles)
    outcome_variation = sum(
        profile["distinct_visible_outcome_signature_count_candidate"] > 1 for profile in profiles
    )
    incomplete = sum(profile["incomplete_episode_binding_count"] > 0 for profile in profiles)
    resolution_variation = sum(
        len(profile["process_resolution_variant_profile_candidate"]) > 1 for profile in profiles
    )
    modal_resolution = sum(
        profile["dominant_process_resolution_class_candidate"] is not None for profile in profiles
    )

    if upstream_status not in {"PASS", "OK", "SUCCESS"}:
        profile_status = "REVIEW_REQUIRED"
    elif incomplete:
        profile_status = "REVIEW_REQUIRED"
    elif profiles:
        profile_status = "PASS"
    else:
        profile_status = "NO_ELIGIBLE_PROCESS_VARIANT_PROFILES"

    return {
        "module_id": MODULE_ID,
        "process_variant_profiles": profiles,
        "process_variant_profile_count": len(profiles),
        "repeated_process_variant_profile_count": repeated,
        "multi_episode_process_variant_profile_count": multi_episode,
        "single_episode_repeat_risk_profile_count": segment_only,
        "outcome_variation_profile_count": outcome_variation,
        "process_resolution_variation_profile_count": resolution_variation,
        "unique_modal_resolution_profile_count": modal_resolution,
        "incomplete_episode_binding_profile_count": incomplete,
        "eligible_reciprocal_population_count": eligible_population,
        "process_variant_profile_status": profile_status,
        "upstream_reciprocal_status": upstream_status,
        "process_variant_profile_claim_ceiling": CLAIM_CEILING,
        "process_variant_profile_is_recurrence_truth": False,
        "process_variant_profile_is_tactical_truth": False,
        "process_variant_profile_creates_independent_evidence": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }