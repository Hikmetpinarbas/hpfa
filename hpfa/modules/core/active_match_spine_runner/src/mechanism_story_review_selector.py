from __future__ import annotations

from typing import Any


NUMERIC_BOUND_STATES = {"POINT_IDENTIFIED_OBSERVED_RATE", "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"}


def _has_visible_difference(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    return value is not None


def _has_process_context(record: dict[str, Any]) -> bool:
    return bool(record.get("process_context_feature_difference_candidates"))


def _has_consequence_difference(record: dict[str, Any]) -> bool:
    return bool(record.get("consequence_feature_difference_candidates"))


def _bound_signature(contract: dict[str, Any]) -> tuple[Any, ...]:
    return (
        contract.get("rate_bound_estimand_id"),
        contract.get("rate_bound_denominator_basis"),
        contract.get("rate_bound_state"),
        contract.get("rate_bound_resolved_success_n"),
        contract.get("rate_bound_resolved_failure_n"),
        contract.get("rate_bound_unresolved_eligible_n"),
        contract.get("rate_bound_eligible_total_n"),
        contract.get("rate_bound_lower"),
        contract.get("rate_bound_upper"),
        contract.get("rate_bound_width"),
        contract.get("rate_bound_assumption_set_id"),
    )


def _bound_by_family(analyst_output_claim_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(analyst_output_claim_payload, dict):
        return {}
    if str(analyst_output_claim_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in analyst_output_claim_payload.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            continue
        if row.get("rate_bound_binding_state") != "SOURCE_BOUND_NUMERIC":
            continue
        if str(row.get("rate_bound_state") or "") not in NUMERIC_BOUND_STATES:
            continue
        if row.get("rate_bound_can_authorize_emit") is not False:
            continue
        if row.get("rate_bound_can_strengthen_claim_ceiling") is not False:
            continue
        for family_ref in row.get("rate_bound_matched_process_variant_family_refs") or []:
            ref = str(family_ref or "").strip()
            if ref:
                grouped.setdefault(ref, []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for family_ref, rows in grouped.items():
        signatures = {_bound_signature(row) for row in rows}
        if len(signatures) == 1:
            result[family_ref] = rows[0]
    return result


def _safe_finding_review_by_family(
    analyst_output_claim_payload: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(analyst_output_claim_payload, dict):
        return {}
    if str(analyst_output_claim_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}

    tier_order = {
        "SF_R0_REVIEW_RICH_MATCH_LOCAL_DESCRIPTION": 0,
        "SF_R1_REVIEWABLE_MATCH_LOCAL_DESCRIPTION": 1,
        "SF_R2_SUPPORTING_MATCH_LOCAL_CONTEXT": 2,
        "SF_R3_LOW_CONTEXT_OR_ABSTAIN": 3,
        "SF_UNBOUND": 4,
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in analyst_output_claim_payload.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            continue
        family_refs = {
            str(value or "").strip()
            for value in [
                *(row.get("rate_bound_matched_process_variant_family_refs") or []),
                *(row.get("variant_feature_challenge_family_refs") or []),
                *[
                    profile.get("family_ref")
                    for profile in (row.get("variant_support_spread_profiles") or [])
                    if isinstance(profile, dict)
                ],
            ]
            if str(value or "").strip()
        }
        if not family_refs:
            continue

        decision = str(row.get("safe_finding_admission_decision") or "").upper()
        blocking = {str(value) for value in (row.get("blocking_dimensions") or [])}
        spread = row.get("variant_support_episode_spread_observed") is True
        challenge = (
            str(row.get("variant_feature_challenge_binding_state") or "")
            == "MATCHED_CHALLENGE_VISIBLE"
            or bool(row.get("variant_feature_challenge_refs"))
        )
        source_bound_rate = (
            row.get("rate_bound_binding_state") == "SOURCE_BOUND_NUMERIC"
            and str(row.get("rate_bound_state") or "") in NUMERIC_BOUND_STATES
        )
        outcome_debt = bool(
            blocking
            & {
                "OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN",
                "UNRESOLVED_OUTCOME_BURDEN",
            }
        )
        if decision == "DOWNGRADE" and spread and challenge and source_bound_rate and not outcome_debt:
            tier = "SF_R0_REVIEW_RICH_MATCH_LOCAL_DESCRIPTION"
        elif decision == "DOWNGRADE" and spread and challenge and not outcome_debt:
            tier = "SF_R1_REVIEWABLE_MATCH_LOCAL_DESCRIPTION"
        elif decision == "DOWNGRADE" and (spread or challenge):
            tier = "SF_R2_SUPPORTING_MATCH_LOCAL_CONTEXT"
        else:
            tier = "SF_R3_LOW_CONTEXT_OR_ABSTAIN"

        summary = {
            "tier": tier,
            "tier_order": tier_order[tier],
            "source_contract_ref": row.get("analyst_output_contract_id"),
            "decision": decision or "UNKNOWN",
            "claim_scope": row.get("claim_scope"),
            "blocking_dimensions": sorted(blocking),
            "episode_spread_observed": spread,
            "challenge_visible": challenge,
            "source_bound_rate_visible": source_bound_rate,
            "outcome_debt_visible": outcome_debt,
            "review_readiness_is_truth_ranking": False,
            "review_readiness_is_confidence_score": False,
            "review_readiness_can_authorize_emit": False,
            "review_readiness_can_increase_support": False,
        }
        for family_ref in family_refs:
            grouped.setdefault(family_ref, []).append(summary)

    result: dict[str, dict[str, Any]] = {}
    for family_ref, rows in grouped.items():
        ordered = sorted(
            rows,
            key=lambda row: (
                int(row.get("tier_order") or 99),
                str(row.get("source_contract_ref") or ""),
            ),
        )
        best = ordered[0]
        decision_counts: dict[str, int] = {}
        tier_counts: dict[str, int] = {}
        blocking: set[str] = set()
        for row in rows:
            decision = str(row.get("decision") or "UNKNOWN")
            tier = str(row.get("tier") or "SF_UNBOUND")
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            blocking.update(str(value) for value in (row.get("blocking_dimensions") or []))
        result[family_ref] = {
            "safe_finding_review_readiness_band": best["tier"],
            "safe_finding_review_contract_count": len(rows),
            "safe_finding_review_source_contract_refs": sorted(
                str(row.get("source_contract_ref") or "")
                for row in rows
                if str(row.get("source_contract_ref") or "")
            ),
            "safe_finding_review_decision_counts": dict(sorted(decision_counts.items())),
            "safe_finding_review_tier_counts": dict(sorted(tier_counts.items())),
            "safe_finding_review_blocking_dimensions": sorted(blocking),
            "safe_finding_review_has_observed_episode_spread": any(
                row.get("episode_spread_observed") is True for row in rows
            ),
            "safe_finding_review_has_challenge_surface": any(
                row.get("challenge_visible") is True for row in rows
            ),
            "safe_finding_review_has_source_bound_rate": any(
                row.get("source_bound_rate_visible") is True for row in rows
            ),
            "safe_finding_review_has_outcome_debt": any(
                row.get("outcome_debt_visible") is True for row in rows
            ),
            "safe_finding_review_readiness_is_truth_ranking": False,
            "safe_finding_review_readiness_is_confidence_score": False,
            "safe_finding_review_readiness_can_authorize_emit": False,
            "safe_finding_review_readiness_can_increase_support": False,
        }
    return result


def _eligibility_state(record: dict[str, Any], bound_by_family: dict[str, dict[str, Any]]) -> str:
    if not (
        int(record.get("resolved_variant_count") or 0) > 0
        and int(record.get("success_resolved_variant_count") or 0) > 0
        and int(record.get("failure_resolved_variant_count") or 0) > 0
    ):
        return "BLOCKED_INSUFFICIENT_RESOLVED_OUTCOMES"
    if int(record.get("right_censored_variant_count") or 0) == 0:
        return "ELIGIBLE_RESOLVED"
    family_ref = str(record.get("source_process_variant_family_ref") or "").strip()
    if family_ref and family_ref in bound_by_family:
        return "BOUND_AWARE_REVIEW_ONLY"
    return "BLOCKED_CENSORING_UNBOUNDED"


def _priority_band(record: dict[str, Any], bound_by_family: dict[str, dict[str, Any]]) -> str:
    eligibility = _eligibility_state(record, bound_by_family)
    if eligibility.startswith("BLOCKED_"):
        return eligibility
    if eligibility == "BOUND_AWARE_REVIEW_ONLY":
        return "BOUND_AWARE_REVIEW_ONLY"
    process_context = _has_process_context(record)
    consequence = _has_consequence_difference(record)
    first_context = _has_visible_difference(record, "first_supported_context_difference_layer_candidate")
    first_consequence = _has_visible_difference(record, "first_supported_consequence_difference_layer_candidate")
    if process_context and consequence and first_context and first_consequence:
        return "P0_REVIEW_RICH"
    if consequence and first_consequence:
        return "P1_REVIEWABLE"
    return "P2_SUPPORTING_CONTEXT"


def _review_support_state(record: dict[str, Any]) -> str:
    episode_spread = int(record.get("visible_episode_spread_count") or 0)
    occurrence_clusters = int(record.get("occurrence_disjoint_support_cluster_count") or 0)
    divergence_count = int(record.get("supported_branch_divergence_binding_count") or 0)
    success_failure_divergence_count = int(
        record.get("success_failure_supported_branch_divergence_count") or 0
    )
    if episode_spread >= 2 and occurrence_clusters >= 2 and success_failure_divergence_count > 0:
        return "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if episode_spread >= 2 and success_failure_divergence_count > 0:
        return "MULTI_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if episode_spread >= 2 and divergence_count > 0:
        return "MULTI_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST"
    if success_failure_divergence_count > 0:
        return "SINGLE_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if divergence_count > 0:
        return "SINGLE_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST"
    return "DIVERGENCE_SUPPORT_UNRESOLVED"


def _diversity_key(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(v) for v in (record.get("grammar_signature_tokens") or []))


def _process_context_binding_by_variant_family(
    process_variant_payload: dict[str, Any] | None,
    process_participation_payload: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(process_variant_payload, dict) or not isinstance(process_participation_payload, dict):
        return {}
    if str(process_variant_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}
    if str(process_participation_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}

    context_rows = [
        row
        for row in (process_participation_payload.get("process_participation_candidates") or [])
        if isinstance(row, dict) and row.get("semantic_role") == "CONTEXT_INTERVAL"
    ]
    contexts_by_episode: dict[str, list[dict[str, Any]]] = {}
    for row in context_rows:
        episode_ref = str(row.get("episode_candidate_id") or "").strip()
        if episode_ref:
            contexts_by_episode.setdefault(episode_ref, []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        family_ref = str(family.get("observable_process_variant_family_id") or "").strip()
        if not family_ref:
            continue
        teams = {str(v) for v in (family.get("team_identity_candidate_ids") or []) if str(v)}
        periods = {str(v) for v in (family.get("period_candidates") or []) if str(v)}
        episodes = {str(v) for v in (family.get("visible_episode_candidate_ids") or []) if str(v)}

        family_episode_presence: dict[str, int] = {}
        ambiguous_episode_count = 0
        unbound_episode_count = 0
        bound_episode_count = 0
        unique_single_family_values: set[str] = set()

        for episode_ref in sorted(episodes):
            matched = [
                row
                for row in contexts_by_episode.get(episode_ref, [])
                if str(row.get("team_identity_candidate_id") or "") in teams
                and str(row.get("period_candidate") or "") in periods
            ]
            visible_families = {
                str(row.get("process_family_candidate") or "").strip()
                for row in matched
                if str(row.get("process_family_candidate") or "").strip()
            }
            if not visible_families:
                unbound_episode_count += 1
                continue
            bound_episode_count += 1
            for process_family in visible_families:
                family_episode_presence[process_family] = family_episode_presence.get(process_family, 0) + 1
            if len(visible_families) == 1:
                unique_single_family_values.update(visible_families)
            else:
                ambiguous_episode_count += 1

        if not episodes:
            state = "UNRESOLVED_NO_VISIBLE_EPISODE_LINEAGE"
        elif unbound_episode_count:
            state = "PARTIAL_PROCESS_CONTEXT_BINDING"
        elif ambiguous_episode_count:
            state = "AMBIGUOUS_MULTI_PROCESS_FAMILY_CONTEXT"
        elif len(unique_single_family_values) == 1:
            state = "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT"
        else:
            state = "MULTI_PROCESS_FAMILY_ACROSS_EPISODES"

        result[family_ref] = {
            "process_context_binding_state": state,
            "visible_episode_count": len(episodes),
            "bound_episode_count": bound_episode_count,
            "unbound_episode_count": unbound_episode_count,
            "ambiguous_episode_count": ambiguous_episode_count,
            "process_family_episode_presence_counts": dict(sorted(family_episode_presence.items())),
            "single_process_family_candidate": (
                next(iter(unique_single_family_values))
                if state == "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT"
                else None
            ),
            "binding_basis": "SAME_VARIANT_FAMILY_EPISODE_PLUS_SAME_TEAM_PLUS_SAME_PERIOD_PROVIDER_REVIEWED_CONTEXT_INTERVAL",
            "process_family_episode_presence_count_is_independent_support_count": False,
            "process_context_binding_is_process_identity_truth": False,
            "process_context_binding_is_tactical_pattern_truth": False,
            "process_context_binding_is_causal_mechanism_truth": False,
            "process_context_binding_can_authorize_emit": False,
            "claim_ceiling": "MATCH_LOCAL_SOURCE_BOUND_PROCESS_CONTEXT_BINDING_CANDIDATE_ONLY",
        }
    return result


def _challenge_summary_by_feature_delta(
    challenge_payload: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(challenge_payload, dict):
        return {}
    if str(challenge_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in challenge_payload.get("variant_feature_challenge_records") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("source_feature_delta_record_ref") or "").strip()
        if ref:
            grouped.setdefault(ref, []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for ref, rows in grouped.items():
        result[ref] = {
            "mechanism_challenge_binding_state": "SOURCE_BOUND_VARIANT_FEATURE_CHALLENGE_AVAILABLE",
            "challenge_record_count": len(rows),
            "challenge_reason_codes": sorted({
                str(value)
                for row in rows
                for value in (row.get("challenge_reasons") or [])
                if str(value)
            }),
            "counter_scenario_candidates": sorted({
                str(value)
                for row in rows
                for value in (row.get("counter_scenario_candidates") or [])
                if str(value)
            }),
            "withdrawal_conditions": sorted({
                str(value)
                for row in rows
                for value in (row.get("withdrawal_conditions") or [])
                if str(value)
            }),
            "feature_surface_counts": dict(sorted({
                surface: sum(str(row.get("feature_surface") or "") == surface for row in rows)
                for surface in {
                    str(row.get("feature_surface") or "").strip()
                    for row in rows
                    if str(row.get("feature_surface") or "").strip()
                }
            }.items())),
            "context_scope_states": sorted({
                str(row.get("context_scope_state") or "")
                for row in rows
                if str(row.get("context_scope_state") or "")
            }),
            "partition_visibility_states": sorted({
                str(row.get("partition_visibility_state") or "")
                for row in rows
                if str(row.get("partition_visibility_state") or "")
            }),
            "all_professional_finding_emit_disallowed": all(
                row.get("professional_finding_emit_allowed") is False for row in rows
            ),
            "all_hypothesis_candidate_truth_false": all(
                row.get("hypothesis_candidate_is_truth") is False for row in rows
            ),
            "dependency_independence_proven": all(
                row.get("dependency_independence_proven") is True for row in rows
            ),
            "statistical_independence_proven": all(
                row.get("statistical_independence_proven") is True for row in rows
            ),
            "challenge_records_are_independent_evidence_votes": False,
            "challenge_summary_is_counterfactual_truth": False,
            "challenge_summary_is_causal_explanation": False,
            "challenge_can_authorize_emit": False,
            "claim_ceiling": "MATCH_LOCAL_SOURCE_BOUND_MECHANISM_CHALLENGE_SUMMARY_ONLY",
        }
    return result


def build_mechanism_story_review_shortlist(
    feature_delta_payload: dict[str, Any],
    *,
    analyst_output_claim_payload: dict[str, Any] | None = None,
    process_variant_payload: dict[str, Any] | None = None,
    process_participation_payload: dict[str, Any] | None = None,
    variant_feature_challenge_payload: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Build an analyst-attention shortlist without promoting evidence or truth.

    Censoring may remain review-visible only when the same process-family has an
    already-admitted, source-bound numeric identification interval. This selector never
    recomputes bounds, scores confidence, or authorizes professional output.
    """
    if limit < 1:
        limit = 1
    records = [
        row
        for row in (feature_delta_payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(row, dict)
    ]
    if not records:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "no_mechanism_review_candidates",
            "shortlist": [],
            "shortlist_count": 0,
            "source_candidate_count": 0,
            "bounded_review_only_count": 0,
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_is_truth_ranking": False,
            "selection_can_authorize_emit": False,
            "production_release": False,
        }

    bounds = _bound_by_family(analyst_output_claim_payload)
    safe_finding_review_by_family = _safe_finding_review_by_family(analyst_output_claim_payload)
    process_context_by_family = _process_context_binding_by_variant_family(
        process_variant_payload,
        process_participation_payload,
    )
    challenge_by_feature_delta = _challenge_summary_by_feature_delta(
        variant_feature_challenge_payload
    )
    band_order = {
        "P0_REVIEW_RICH": 0,
        "P1_REVIEWABLE": 1,
        "P2_SUPPORTING_CONTEXT": 2,
        "BOUND_AWARE_REVIEW_ONLY": 3,
        "BLOCKED_CENSORING_UNBOUNDED": 4,
        "BLOCKED_INSUFFICIENT_RESOLVED_OUTCOMES": 5,
    }
    support_order = {
        "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 0,
        "MULTI_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 1,
        "MULTI_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST": 2,
        "SINGLE_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 3,
        "SINGLE_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST": 4,
        "DIVERGENCE_SUPPORT_UNRESOLVED": 5,
    }
    safe_review_order = {
        "SF_R0_REVIEW_RICH_MATCH_LOCAL_DESCRIPTION": 0,
        "SF_R1_REVIEWABLE_MATCH_LOCAL_DESCRIPTION": 1,
        "SF_R2_SUPPORTING_MATCH_LOCAL_CONTEXT": 2,
        "SF_R3_LOW_CONTEXT_OR_ABSTAIN": 3,
        "SF_UNBOUND": 4,
    }
    decorated: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for row in records:
        band = _priority_band(row, bounds)
        support_state = _review_support_state(row)
        family_ref = str(row.get("source_process_variant_family_ref") or "").strip()
        safe_summary = safe_finding_review_by_family.get(family_ref, {})
        safe_band = str(safe_summary.get("safe_finding_review_readiness_band") or "SF_UNBOUND")
        candidate_id = str(row.get("grammar_stable_variant_feature_delta_id") or "")
        decorated.append((
            band_order[band],
            safe_review_order[safe_band],
            support_order[support_state],
            candidate_id,
            row,
        ))
    decorated.sort(key=lambda item: (item[0], item[1], item[2], item[3]))

    selected: list[dict[str, Any]] = []
    seen_diversity: set[tuple[str, ...]] = set()
    for _, _, _, _, row in decorated:
        eligibility = _eligibility_state(row, bounds)
        band = _priority_band(row, bounds)
        if eligibility.startswith("BLOCKED_"):
            continue
        key = _diversity_key(row)
        if key in seen_diversity:
            continue
        seen_diversity.add(key)
        family_ref = str(row.get("source_process_variant_family_ref") or "").strip()
        bound = bounds.get(family_ref) if eligibility == "BOUND_AWARE_REVIEW_ONLY" else None
        process_context_binding = process_context_by_family.get(family_ref, {})
        safe_finding_review_summary = safe_finding_review_by_family.get(family_ref, {})
        challenge_summary = challenge_by_feature_delta.get(
            str(row.get("grammar_stable_variant_feature_delta_id") or ""), {}
        )
        selected.append({
            "source_mechanism_review_ref": row.get("grammar_stable_variant_feature_delta_id"),
            "source_process_variant_family_ref": row.get("source_process_variant_family_ref"),
            "priority_band": band,
            "safe_finding_review_readiness_band": safe_finding_review_summary.get(
                "safe_finding_review_readiness_band", "SF_UNBOUND"
            ),
            "safe_finding_review_contract_count": int(
                safe_finding_review_summary.get("safe_finding_review_contract_count") or 0
            ),
            "safe_finding_review_source_contract_refs": list(
                safe_finding_review_summary.get("safe_finding_review_source_contract_refs") or []
            ),
            "safe_finding_review_decision_counts": dict(
                safe_finding_review_summary.get("safe_finding_review_decision_counts") or {}
            ),
            "safe_finding_review_tier_counts": dict(
                safe_finding_review_summary.get("safe_finding_review_tier_counts") or {}
            ),
            "safe_finding_review_blocking_dimensions": list(
                safe_finding_review_summary.get("safe_finding_review_blocking_dimensions") or []
            ),
            "safe_finding_review_has_observed_episode_spread": (
                safe_finding_review_summary.get("safe_finding_review_has_observed_episode_spread") is True
            ),
            "safe_finding_review_has_challenge_surface": (
                safe_finding_review_summary.get("safe_finding_review_has_challenge_surface") is True
            ),
            "safe_finding_review_has_source_bound_rate": (
                safe_finding_review_summary.get("safe_finding_review_has_source_bound_rate") is True
            ),
            "safe_finding_review_has_outcome_debt": (
                safe_finding_review_summary.get("safe_finding_review_has_outcome_debt") is True
            ),
            "safe_finding_review_readiness_is_truth_ranking": False,
            "safe_finding_review_readiness_is_confidence_score": False,
            "safe_finding_review_readiness_can_authorize_emit": False,
            "safe_finding_review_readiness_can_increase_support": False,
            "story_eligibility_state": eligibility,
            "team_identity_candidate_ids": list(row.get("team_identity_candidate_ids") or []),
            "period_candidates": list(row.get("period_candidates") or []),
            "process_context_binding_state": process_context_binding.get(
                "process_context_binding_state", "UNRESOLVED_NO_SOURCE_BOUND_PROCESS_CONTEXT"
            ),
            "process_context_visible_episode_count": int(
                process_context_binding.get("visible_episode_count") or 0
            ),
            "process_context_bound_episode_count": int(
                process_context_binding.get("bound_episode_count") or 0
            ),
            "process_context_unbound_episode_count": int(
                process_context_binding.get("unbound_episode_count") or 0
            ),
            "process_context_ambiguous_episode_count": int(
                process_context_binding.get("ambiguous_episode_count") or 0
            ),
            "process_family_episode_presence_counts": dict(
                process_context_binding.get("process_family_episode_presence_counts") or {}
            ),
            "single_process_family_candidate": process_context_binding.get(
                "single_process_family_candidate"
            ),
            "process_context_binding_basis": process_context_binding.get("binding_basis"),
            "process_family_episode_presence_count_is_independent_support_count": False,
            "process_context_binding_is_process_identity_truth": False,
            "process_context_binding_is_tactical_pattern_truth": False,
            "process_context_binding_is_causal_mechanism_truth": False,
            "process_context_binding_can_authorize_emit": False,
            "process_context_binding_claim_ceiling": process_context_binding.get(
                "claim_ceiling",
                "MATCH_LOCAL_SOURCE_BOUND_PROCESS_CONTEXT_BINDING_CANDIDATE_ONLY",
            ),
            "mechanism_challenge_binding_state": challenge_summary.get(
                "mechanism_challenge_binding_state",
                "UNRESOLVED_NO_SOURCE_BOUND_VARIANT_FEATURE_CHALLENGE",
            ),
            "mechanism_challenge_record_count": int(
                challenge_summary.get("challenge_record_count") or 0
            ),
            "mechanism_challenge_reason_codes": list(
                challenge_summary.get("challenge_reason_codes") or []
            ),
            "mechanism_counter_scenario_candidates": list(
                challenge_summary.get("counter_scenario_candidates") or []
            ),
            "mechanism_withdrawal_conditions": list(
                challenge_summary.get("withdrawal_conditions") or []
            ),
            "mechanism_challenge_feature_surface_counts": dict(
                challenge_summary.get("feature_surface_counts") or {}
            ),
            "mechanism_challenge_context_scope_states": list(
                challenge_summary.get("context_scope_states") or []
            ),
            "mechanism_challenge_partition_visibility_states": list(
                challenge_summary.get("partition_visibility_states") or []
            ),
            "mechanism_challenge_all_professional_finding_emit_disallowed": (
                challenge_summary.get("all_professional_finding_emit_disallowed") is True
            ),
            "mechanism_challenge_all_hypothesis_candidate_truth_false": (
                challenge_summary.get("all_hypothesis_candidate_truth_false") is True
            ),
            "mechanism_challenge_dependency_independence_proven": (
                challenge_summary.get("dependency_independence_proven") is True
            ),
            "mechanism_challenge_statistical_independence_proven": (
                challenge_summary.get("statistical_independence_proven") is True
            ),
            "mechanism_challenge_records_are_independent_evidence_votes": False,
            "mechanism_challenge_summary_is_counterfactual_truth": False,
            "mechanism_challenge_summary_is_causal_explanation": False,
            "mechanism_challenge_can_authorize_emit": False,
            "mechanism_challenge_claim_ceiling": challenge_summary.get(
                "claim_ceiling",
                "MATCH_LOCAL_SOURCE_BOUND_MECHANISM_CHALLENGE_SUMMARY_ONLY",
            ),
            "grammar_signature_tokens": list(row.get("grammar_signature_tokens") or []),
            "resolved_variant_count": int(row.get("resolved_variant_count") or 0),
            "success_resolved_variant_count": int(row.get("success_resolved_variant_count") or 0),
            "failure_resolved_variant_count": int(row.get("failure_resolved_variant_count") or 0),
            "right_censored_variant_count": int(row.get("right_censored_variant_count") or 0),
            "rate_bound_state": bound.get("rate_bound_state") if bound else None,
            "rate_bound_lower": bound.get("rate_bound_lower") if bound else None,
            "rate_bound_upper": bound.get("rate_bound_upper") if bound else None,
            "rate_bound_width": bound.get("rate_bound_width") if bound else None,
            "rate_bound_source_analyst_output_contract_ref": (
                bound.get("analyst_output_contract_id") if bound else None
            ),
            "first_supported_context_difference_layer_candidate": row.get(
                "first_supported_context_difference_layer_candidate"
            ),
            "first_supported_consequence_difference_layer_candidate": row.get(
                "first_supported_consequence_difference_layer_candidate"
            ),
            "process_context_difference_visible": _has_process_context(row),
            "consequence_difference_visible": _has_consequence_difference(row),
            "review_support_state": _review_support_state(row),
            "visible_episode_spread_count": int(row.get("visible_episode_spread_count") or 0),
            "success_visible_episode_spread_count": int(
                row.get("success_visible_episode_spread_count") or 0
            ),
            "failure_visible_episode_spread_count": int(
                row.get("failure_visible_episode_spread_count") or 0
            ),
            "occurrence_disjoint_support_cluster_count": int(
                row.get("occurrence_disjoint_support_cluster_count") or 0
            ),
            "supported_branch_divergence_binding_count": int(
                row.get("supported_branch_divergence_binding_count") or 0
            ),
            "success_failure_supported_branch_divergence_count": int(
                row.get("success_failure_supported_branch_divergence_count") or 0
            ),
            "episode_spread_count_is_independent_support_count": False,
            "occurrence_disjoint_cluster_count_is_independent_support_count": False,
            "review_support_state_is_truth_ranking": False,
            "dependency_independence_proven": row.get("dependency_independence_proven") is True,
            "statistical_independence_proven": row.get("statistical_independence_proven") is True,
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_role": "ANALYST_REVIEW_ATTENTION_ONLY",
            "selection_is_truth_ranking": False,
            "selection_is_causal_ranking": False,
            "selection_is_confidence_score": False,
            "selection_can_authorize_emit": False,
            "bound_can_authorize_emit": False,
            "bound_can_strengthen_claim_ceiling": False,
        })
        if len(selected) >= limit:
            break

    for selected_row in selected:
        selected_grammar = tuple(str(v) for v in (selected_row.get("grammar_signature_tokens") or []))
        context_refs: list[str] = []
        seen_contexts: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
        for _, _, _, _, candidate in decorated:
            if _eligibility_state(candidate, bounds).startswith("BLOCKED_"):
                continue
            grammar = tuple(str(v) for v in (candidate.get("grammar_signature_tokens") or []))
            if grammar != selected_grammar:
                continue
            context_key = (
                tuple(sorted(str(v) for v in (candidate.get("team_identity_candidate_ids") or []))),
                tuple(sorted(str(v) for v in (candidate.get("period_candidates") or []))),
            )
            if context_key in seen_contexts:
                continue
            seen_contexts.add(context_key)
            ref = str(candidate.get("grammar_stable_variant_feature_delta_id") or "").strip()
            if ref:
                context_refs.append(ref)
        selected_row["same_grammar_context_review_refs"] = context_refs
        selected_row["same_grammar_context_review_ref_count"] = len(context_refs)
        selected_row["same_grammar_context_review_scope"] = (
            "ONE_ATTENTION_REPRESENTATIVE_PER_TEAM_PERIOD_CONTEXT"
        )

    return {
        "status": "PASS" if selected else "REVIEW_REQUIRED",
        "reason": None if selected else "no_eligible_mechanism_review_candidates",
        "shortlist": selected,
        "shortlist_count": len(selected),
        "source_candidate_count": len(records),
        "bounded_review_only_count": sum(
            row.get("story_eligibility_state") == "BOUND_AWARE_REVIEW_ONLY" for row in selected
        ),
        "diversity_deduplication_applied": True,
        "diversity_basis": "UNIQUE_GRAMMAR_SIGNATURE_ATTENTION_SLOT",
        "same_grammar_contexts_are_separate_comparison_not_extra_mechanism_slots": True,
        "review_support_attention_compression_applied": True,
        "review_support_attention_order_is_truth_ranking": False,
        "safe_finding_review_readiness_applied": bool(safe_finding_review_by_family),
        "safe_finding_review_readiness_is_truth_ranking": False,
        "safe_finding_review_readiness_is_confidence_score": False,
        "safe_finding_review_readiness_can_authorize_emit": False,
        "safe_finding_review_readiness_can_increase_support": False,
        "episode_spread_count_is_independent_support_count": False,
        "occurrence_disjoint_cluster_count_is_independent_support_count": False,
        "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
        "selection_is_truth_ranking": False,
        "selection_is_confidence_score": False,
        "selection_can_authorize_emit": False,
        "bound_recomputed_in_selector": False,
        "bound_width_is_confidence_score": False,
        "mechanism_candidate_is_tactical_plan_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
