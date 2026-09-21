from __future__ import annotations

import copy
from collections import Counter
from typing import Any

MODULE_ID = "puzzle_finding_contract_adapter_v1"
CONTRACT_VERSION = "PUZZLE_FINDING_V1"
PUZZLE_ID = "P6_PROCESS_VARIANT_DIVERGENCE"
PUZZLE_FAMILY = "PROCESS_VARIANT_AND_DIVERGENCE"
CLAIM_CEILING = "MATCH_LOCAL_PUZZLE_FINDING_CONTRACT_CANDIDATE_ONLY"

ADDITIONAL_FAMILY_RULES = (
    {
        "puzzle_id": "PROGRESSION_ACCESS",
        "puzzle_family": "PROGRESSION_AND_ACCESS",
        "family_basis": "ADMITTED_PROGRESSIVE_SEMANTIC_IN_SOURCE_DIVERGENCE",
        "discovery_state": "VISIBLE_PROGRESSION_ACCESS_FAMILY_VIEW_BOUND",
    },
    {
        "puzzle_id": "RETENTION_LOSS",
        "puzzle_family": "RETENTION_AND_LOSS",
        "family_basis": "ADMITTED_TURNOVER_FAMILY_IN_SOURCE_DIVERGENCE",
        "discovery_state": "VISIBLE_RETENTION_LOSS_FAMILY_VIEW_BOUND",
    },
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _admission_index(
    admission_payload: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    if admission_payload is None:
        return {}, [], []
    blocks: list[str] = []
    reviews: list[str] = []
    if admission_payload.get("production_release") is True:
        blocks.append("admission_production_release_claimed")
    if admission_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("admission_canonical_event_count_claimed")
    if admission_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("admission_true_action_count_claimed")
    status = _clean(admission_payload.get("status")).upper()
    if status == "FAIL_CLOSED":
        blocks.append("safe_finding_admission_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("safe_finding_admission_review_required")
    elif status != "PASS":
        reviews.append(f"safe_finding_admission_status_unrecognized:{status or 'UNKNOWN'}")

    index: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(
        admission_payload.get("safe_finding_admission_decisions") or []
    ):
        if not isinstance(row, dict):
            reviews.append(f"admission_row_not_object:{position}")
            continue
        source_ref = _clean(row.get("source_safe_finding_handoff_ref"))
        if not source_ref:
            reviews.append(f"admission_source_ref_missing:{position}")
            continue
        if source_ref in index:
            blocks.append(f"duplicate_admission_decision:{source_ref}")
            continue
        index[source_ref] = dict(row)
    return index, blocks, reviews


def _finding_decision(
    admission_row: dict[str, Any] | None,
    admission_supplied: bool,
) -> tuple[str, bool, str]:
    if not admission_supplied:
        return "NOT_EVALUATED", False, "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
    if admission_row is None:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    decision = _clean(admission_row.get("decision")).upper()
    if decision not in {"EMIT", "DOWNGRADE", "ABSTAIN"}:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    claim_allowed = decision == "EMIT" and admission_row.get("claim_output_allowed") is True
    if decision == "EMIT" and not claim_allowed:
        return "ABSTAIN", False, "NO_CLAIM_OUTPUT"
    return (
        decision,
        claim_allowed,
        _clean(admission_row.get("claim_ceiling")) or "NO_CLAIM_OUTPUT",
    )


def _context_refs(where_when: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in (
        "team_identity_candidate_id",
        "period_candidate",
        "shared_anchor_time_layer_ref",
        "anchor_centered_sequence_branch_map_ref",
    ):
        value = _clean(where_when.get(key))
        if value:
            refs.append(f"{key}:{value}")
    return refs


def _late_bound_episode_spread_sufficiency(
    sufficiency: dict[str, Any],
    admission_row: dict[str, Any] | None,
) -> dict[str, Any]:
    result = copy.deepcopy(sufficiency)
    observed = (
        isinstance(admission_row, dict)
        and admission_row.get("variant_support_episode_spread_observed") is True
    )
    result["late_bound_episode_spread_resolution_applied"] = False
    result["late_bound_episode_spread_is_independent_support"] = False
    result["late_bound_episode_spread_is_recurrence_truth"] = False
    if not observed:
        return result

    blocking = [
        value
        for value in (result.get("blocking_dimensions") or [])
        if _clean(value) != "EPISODE_SPREAD_UNKNOWN"
    ]
    result["blocking_dimensions"] = sorted(
        {_clean(value) for value in blocking if _clean(value)}
    )
    dimensions = dict(result.get("dimensions") or {})
    dimensions["episode_spread"] = {
        "count": int(
            admission_row.get("variant_support_episode_spread_max_visible_count") or 0
        ),
        "state": _clean(
            admission_row.get("variant_support_episode_spread_resolution_state")
        )
        or "OBSERVED_LATE_BOUND_VARIANT_FAMILY_SPREAD",
        "count_is_independent_support_count": False,
        "spread_is_recurrence_truth": False,
    }
    result["dimensions"] = dimensions
    result["late_bound_episode_spread_resolution_applied"] = True
    return result


def _divergence_index(sequence_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in sequence_payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(row, dict):
            continue
        source_id = _clean(row.get("first_supported_branch_divergence_id"))
        if source_id and source_id not in index:
            index[source_id] = row
    return index


def _family_projection_signals(divergence: dict[str, Any]) -> dict[str, Any]:
    progression_values: set[str] = set()
    action_families: Counter[str] = Counter()

    for branch in divergence.get("branch_profiles") or []:
        if not isinstance(branch, dict):
            continue
        for family, raw_count in (branch.get("neighbor_action_family_counts") or {}).items():
            family_name = _clean(family).upper()
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                count = 0
            if family_name and count > 0:
                action_families[family_name] += count
        for profile in branch.get("semantic_profiles") or []:
            if not isinstance(profile, dict):
                continue
            for value in profile.get("progression_values") or []:
                cleaned = _clean(value).upper()
                if cleaned:
                    progression_values.add(cleaned)

    return {
        "progression_values": sorted(progression_values),
        "action_family_counts": dict(sorted(action_families.items())),
    }


def _eligible_family_rules(
    handoff: dict[str, Any],
    divergence_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    source_ref = _clean(handoff.get("source_first_supported_branch_divergence_ref"))
    divergence = divergence_by_id.get(source_ref)
    if not source_ref or not isinstance(divergence, dict):
        return [], bool(source_ref)

    if divergence.get("production_release") is True:
        return [], False
    if divergence.get("canonical_event_count") != "UNKNOWN":
        return [], False
    if divergence.get("true_action_count") != "UNKNOWN":
        return [], False
    if divergence.get("same_timestamp_internal_ordering_allowed") is not False:
        return [], False
    if divergence.get("source_row_order_is_temporal_truth") is not False:
        return [], False
    if divergence.get("divergence_is_tactical_truth") is not False:
        return [], False
    if divergence.get("divergence_is_failure_cause_truth") is not False:
        return [], False

    signals = _family_projection_signals(divergence)
    rules: list[dict[str, Any]] = []
    if signals["progression_values"]:
        rules.append(
            {
                **ADDITIONAL_FAMILY_RULES[0],
                "observed_signals": {
                    "progression_values": signals["progression_values"],
                },
            }
        )
    if int(signals["action_family_counts"].get("TURNOVER", 0)) > 0:
        rules.append(
            {
                **ADDITIONAL_FAMILY_RULES[1],
                "observed_signals": {
                    "turnover_family_visible_count": int(
                        signals["action_family_counts"].get("TURNOVER", 0)
                    ),
                },
            }
        )
    return rules, False


def _base_finding(
    handoff: dict[str, Any],
    handoff_id: str,
    decision: str,
    claim_allowed: bool,
    admission_claim_ceiling: str,
    sufficiency: dict[str, Any],
    dependency_state: str,
    independent_support: int,
    dependency_independence_proven: bool,
    statistical_independence_proven: bool,
) -> dict[str, Any]:
    what_visible = handoff.get("what_visible") if isinstance(handoff.get("what_visible"), dict) else {}
    where_when = handoff.get("where_when") if isinstance(handoff.get("where_when"), dict) else {}
    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    counterevidence = handoff.get("counterevidence") if isinstance(handoff.get("counterevidence"), dict) else {}
    uncertainty = handoff.get("uncertainty") if isinstance(handoff.get("uncertainty"), dict) else {}
    alternatives = handoff.get("alternative_explanations") if isinstance(handoff.get("alternative_explanations"), list) else []
    withdrawals = _refs(handoff.get("withdrawal_conditions"))
    forbidden = _refs(handoff.get("forbidden_inference"))
    success_refs = _refs(support.get("visible_success_sequence_refs"))
    failure_refs = _refs(counterevidence.get("visible_failure_sequence_refs"))
    counterexample_refs = _refs(counterevidence.get("comparable_counterexample_refs"))
    context_refs = _context_refs(where_when)

    return {
        "puzzle_finding_id": f"pf_{handoff_id}",
        "puzzle_finding_contract_version": CONTRACT_VERSION,
        "puzzle_id": PUZZLE_ID,
        "puzzle_family": PUZZLE_FAMILY,
        "source_safe_finding_handoff_ref": handoff_id,
        "source_first_supported_branch_divergence_ref": handoff.get(
            "source_first_supported_branch_divergence_ref"
        ),
        "finding_status": decision,
        "claim_output_allowed": claim_allowed,
        "admission_claim_ceiling": admission_claim_ceiling,
        "what_visible": what_visible,
        "where_when": where_when,
        "support": support,
        "counterevidence": counterevidence,
        "evidence_sufficiency": sufficiency,
        "late_bound_episode_spread_resolution_applied": (
            sufficiency.get("late_bound_episode_spread_resolution_applied") is True
        ),
        "late_bound_episode_spread_is_independent_support": False,
        "late_bound_episode_spread_is_recurrence_truth": False,
        "alternative_explanations": alternatives,
        "safe_meaning": handoff.get("safe_meaning"),
        "forbidden_inference": forbidden,
        "uncertainty": uncertainty,
        "withdrawal_conditions": withdrawals,
        "analyst_action": handoff.get("analyst_action"),
        "analyst_summary_tr": handoff.get("analyst_summary_tr"),
        "discovery_surface": {
            "state": "VISIBLE_PROCESS_VARIANT_DIVERGENCE_DISCOVERY_BOUND",
            "source_divergence_ref": handoff.get(
                "source_first_supported_branch_divergence_ref"
            ),
            "visible_success_sequence_refs": success_refs,
            "visible_failure_sequence_refs": failure_refs,
            "creates_new_evidence": False,
        },
        "comparison_surface": {
            "comparison_unit": "COMPARABLE_PARTIAL_ORDER_PROCESS_VARIANT",
            "comparison_eligibility_required": True,
            "visible_success_numerator": support.get("visible_success_numerator"),
            "eligible_denominator": support.get("eligible_denominator"),
            "visible_success_sequence_refs": success_refs,
            "visible_failure_sequence_refs": failure_refs,
            "raw_rate_is_true_probability": False,
        },
        "falsification_surface": {
            "comparable_counterexample_refs": counterexample_refs,
            "alternative_explanation_count": len(alternatives),
            "withdrawal_conditions": withdrawals,
            "absence_used_as_counterevidence": (
                counterevidence.get("absence_used_as_counterevidence") is True
            ),
            "counterexample_pair_count_is_independent_evidence_count": False,
        },
        "evolution_surface": {
            "period_candidate": where_when.get("period_candidate"),
            "score_state": "NOT_AVAILABLE",
            "game_state_conditioning_ready": False,
            "period_only_is_full_game_state_truth": False,
        },
        "fusion_surface": {
            "support_refs": success_refs,
            "counterevidence_refs": counterexample_refs,
            "context_refs": context_refs,
            "dependency_state": dependency_state,
            "admitted_independent_support_count": independent_support,
            "dependency_independence_proven": dependency_independence_proven,
            "statistical_independence_proven": statistical_independence_proven,
            "relation_candidates": [
                "SUPPORTS_PUZZLE_FINDING",
                "COUNTEREXAMPLE_TO_PUZZLE_FINDING",
                "CONTEXTUALIZES_PUZZLE_FINDING",
                "SHARES_PROCESS_FAMILY_CANDIDATE",
            ],
            "same_process_truth": False,
            "same_episode_truth": False,
            "mechanism_candidate_truth": False,
            "creates_new_evidence": False,
        },
        "puzzle_finding_is_professional_finding_truth": False,
        "puzzle_finding_is_tactical_truth": False,
        "puzzle_finding_is_causal_truth": False,
        "puzzle_finding_is_coach_intention_truth": False,
        "absence_is_counterevidence": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _family_view(
    base: dict[str, Any],
    rule: dict[str, Any],
) -> dict[str, Any]:
    row = copy.deepcopy(base)
    handoff_id = _clean(base.get("source_safe_finding_handoff_ref"))
    puzzle_id = _clean(rule.get("puzzle_id"))
    row["puzzle_finding_id"] = f"pf_{puzzle_id.lower()}_{handoff_id}"
    row["puzzle_id"] = puzzle_id
    row["puzzle_family"] = _clean(rule.get("puzzle_family"))
    row["family_projection"] = {
        "state": "ADMITTED_SOURCE_LINEAGE_FAMILY_VIEW",
        "basis": _clean(rule.get("family_basis")),
        "observed_signals": copy.deepcopy(rule.get("observed_signals") or {}),
        "source_divergence_ref": base.get(
            "source_first_supported_branch_divergence_ref"
        ),
        "creates_new_evidence": False,
        "recomputes_occurrence": False,
        "recomputes_sequence": False,
        "recomputes_process": False,
        "recomputes_consequence": False,
        "family_view_is_independent_support": False,
        "provider_label_is_tactical_truth": False,
        "tracking_claim_introduced": False,
    }
    row["source_safe_finding_shared_across_family_views"] = True
    row["family_view_is_independent_support"] = False
    row["family_view_count_is_independent_support_count"] = False
    row["discovery_surface"]["state"] = _clean(rule.get("discovery_state"))
    row["discovery_surface"]["family_projection_only"] = True
    row["fusion_surface"]["family_view_is_independent_support"] = False
    row["fusion_surface"]["cross_mechanism_fusion_performed"] = False
    return row



def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bind_game_state_context(
    finding: dict[str, Any],
    context_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    out = copy.deepcopy(finding)
    evolution = (
        out.get("evolution_surface")
        if isinstance(out.get("evolution_surface"), dict)
        else {}
    )
    if not isinstance(context_payload, dict):
        return out

    mix = context_payload.get("game_state_process_mix_context")
    if not isinstance(mix, dict) or str(mix.get("status") or "") not in {"PASS", "REVIEW_REQUIRED"}:
        return out

    where_when = (
        out.get("where_when")
        if isinstance(out.get("where_when"), dict)
        else {}
    )
    team_id = _clean(where_when.get("team_identity_candidate_id"))
    anchor_time = _as_float(where_when.get("shared_anchor_time_candidate"))
    if not team_id or anchor_time is None:
        return out

    candidates: list[dict[str, Any]] = []
    for profile in mix.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        if _clean(profile.get("team_identity_candidate_id")) != team_id:
            continue
        start = _as_float(profile.get("segment_start_second_candidate"))
        end = _as_float(profile.get("segment_end_second_candidate"))
        if start is None or end is None:
            continue
        if start <= anchor_time < end or (start == end == anchor_time):
            candidates.append(profile)

    if len(candidates) != 1:
        evolution["game_state_conditioning_ready"] = False
        evolution["game_state_binding_state"] = (
            "MULTIPLE_MATCHING_SCORE_STATE_SEGMENTS_REVIEW_REQUIRED"
            if len(candidates) > 1
            else "NO_MATCHING_SCORE_STATE_SEGMENT"
        )
        out["evolution_surface"] = evolution
        return out

    profile = candidates[0]
    evolution.update({
        "score_state": copy.deepcopy(profile.get("score_state_candidate") or {}),
        "game_state_conditioning_ready": True,
        "game_state_binding_state": "SINGLE_SCORE_STATE_SEGMENT_MATCH",
        "score_state_segment_start_second_candidate": profile.get(
            "segment_start_second_candidate"
        ),
        "score_state_segment_end_second_candidate": profile.get(
            "segment_end_second_candidate"
        ),
        "score_state_segment_duration_second_candidate": profile.get(
            "segment_duration_second_candidate"
        ),
        "team_process_family_counts_in_score_state": copy.deepcopy(
            profile.get("process_family_counts") or {}
        ),
        "team_process_family_rate_per_10_minutes_in_score_state": copy.deepcopy(
            profile.get("process_family_rate_per_10_minutes") or {}
        ),
        "score_state_is_causal_explanation": False,
        "process_mix_is_tactical_intention_truth": False,
        "creates_new_evidence": False,
        "creates_independent_support": False,
    })
    out["evolution_surface"] = evolution
    return out


def build_puzzle_finding_contract(
    sequence_payload: dict[str, Any],
    admission_payload: dict[str, Any] | None = None,
    context_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project admitted Safe Finding handoffs into puzzle-facing contract views.

    P6 remains the canonical base view. Additional bounded family views are projected only
    from already-admitted source divergence semantics. They do not discover actions,
    recompute sequence/process/consequence, create evidence, create independent support,
    or widen claim ceilings.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("production_release") is True:
        blocks.append("sequence_production_release_claimed")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("sequence_canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("sequence_true_action_count_claimed")
    if sequence_payload.get("safe_finding_handoff_professional_emit_allowed") is not False:
        blocks.append("sequence_professional_emit_lock_not_false")

    admission_by_ref, admission_blocks, admission_reviews = _admission_index(
        admission_payload
    )
    blocks.extend(admission_blocks)
    reviews.extend(admission_reviews)
    divergence_by_id = _divergence_index(sequence_payload)

    findings: list[dict[str, Any]] = []
    family_projection_missing_source_count = 0
    additional_family_counts: Counter[str] = Counter()

    if not blocks:
        for position, handoff in enumerate(
            sequence_payload.get("safe_finding_handoff_candidates") or []
        ):
            if not isinstance(handoff, dict):
                reviews.append(f"safe_finding_handoff_not_object:{position}")
                continue
            handoff_id = _clean(handoff.get("safe_finding_handoff_candidate_id"))
            if not handoff_id:
                reviews.append(f"safe_finding_handoff_id_missing:{position}")
                continue
            if handoff.get("professional_finding_emit_allowed") is not False:
                reviews.append(f"handoff_emit_lock_not_false:{handoff_id}")
                continue
            if any(
                handoff.get(key) is not False
                for key in (
                    "safe_finding_handoff_is_professional_finding_truth",
                    "safe_finding_handoff_is_tactical_truth",
                    "safe_finding_handoff_is_causal_truth",
                    "safe_finding_handoff_is_coach_intention_truth",
                    "same_timestamp_internal_ordering_allowed",
                    "source_row_order_is_temporal_truth",
                )
            ):
                reviews.append(f"handoff_truth_lock_missing:{handoff_id}")
                continue

            support = (
                handoff.get("support")
                if isinstance(handoff.get("support"), dict)
                else {}
            )
            source_sufficiency = (
                handoff.get("evidence_sufficiency")
                if isinstance(handoff.get("evidence_sufficiency"), dict)
                else {}
            )
            independent_support = support.get("admitted_independent_support_count")
            dependency_independence_proven = (
                support.get("dependency_independence_proven") is True
            )
            statistical_independence_proven = (
                support.get("statistical_independence_proven") is True
            )
            if (
                isinstance(independent_support, bool)
                or not isinstance(independent_support, int)
                or independent_support < 0
            ):
                independent_support = 0
                reviews.append(f"independent_support_count_invalid:{handoff_id}")

            admission_row = admission_by_ref.get(handoff_id)
            decision, claim_allowed, admission_claim_ceiling = _finding_decision(
                admission_row,
                admission_payload is not None,
            )
            if admission_payload is not None and handoff_id not in admission_by_ref:
                reviews.append(f"admission_decision_missing:{handoff_id}")

            sufficiency = _late_bound_episode_spread_sufficiency(
                source_sufficiency,
                admission_row,
            )
            if (
                dependency_independence_proven
                and statistical_independence_proven
                and independent_support > 0
            ):
                dependency_state = "INDEPENDENT_SUPPORT_ADMITTED"
            elif independent_support > 0 or dependency_independence_proven:
                dependency_state = "DEPENDENT_OR_PARTIAL_LINEAGE"
            else:
                dependency_state = "INDEPENDENCE_UNKNOWN"

            base = _base_finding(
                handoff,
                handoff_id,
                decision,
                claim_allowed,
                admission_claim_ceiling,
                sufficiency,
                dependency_state,
                independent_support,
                dependency_independence_proven,
                statistical_independence_proven,
            )
            base = _bind_game_state_context(base, context_payload)
            findings.append(base)

            rules, missing_source = _eligible_family_rules(handoff, divergence_by_id)
            if missing_source:
                family_projection_missing_source_count += 1
            for rule in rules:
                family_row = _family_view(base, rule)
                findings.append(family_row)
                additional_family_counts[family_row["puzzle_id"]] += 1

    counts = Counter(row.get("finding_status") for row in findings)
    bound_puzzle_ids = sorted(
        {
            _clean(row.get("puzzle_id"))
            for row in findings
            if _clean(row.get("puzzle_id"))
        }
    )
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "puzzle_finding_contract_version": CONTRACT_VERSION,
        "puzzle_findings": findings if not blocks else [],
        "puzzle_finding_count": len(findings) if not blocks else 0,
        "puzzle_finding_status_counts": (
            dict(sorted(counts.items())) if not blocks else {}
        ),
        "bound_puzzle_ids": bound_puzzle_ids if not blocks else [],
        "base_p6_behavior_preserved": True,
        "additional_family_projection_enabled": True,
        "additional_family_projection_counts": (
            dict(sorted(additional_family_counts.items())) if not blocks else {}
        ),
        "additional_family_projection_missing_source_count": (
            family_projection_missing_source_count if not blocks else 0
        ),
        "additional_family_projection_source": (
            "EXISTING_SAFE_FINDING_HANDOFF_PLUS_FIRST_SUPPORTED_DIVERGENCE_LINEAGE"
        ),
        "additional_family_projection_recomputes_evidence": False,
        "additional_family_projection_recomputes_sequence": False,
        "additional_family_projection_recomputes_process": False,
        "additional_family_projection_recomputes_consequence": False,
        "family_view_count_is_independent_support_count": False,
        "supported_additional_family_ids": [
            rule["puzzle_id"] for rule in ADDITIONAL_FAMILY_RULES
        ],
        "recovery_transition_family_enabled": False,
        "recovery_transition_family_state": (
            "LATER_NO_CURRENT_SAFE_FINDING_LINEAGE_PHYSICALLY_OBSERVED"
        ),
        "safe_finding_handoff_consumed": True,
        "safe_finding_admission_consumed": admission_payload is not None,
        "late_bound_episode_spread_can_only_resolve_stale_unknown": True,
        "late_bound_episode_spread_is_independent_support": False,
        "late_bound_episode_spread_is_recurrence_truth": False,
        "discovery_recomputed": False,
        "comparison_recomputed": False,
        "falsification_recomputed": False,
        "creates_new_evidence": False,
        "creates_new_finding": False,
        "cross_mechanism_fusion_performed": False,
        "mechanism_candidate_emitted": False,
        "game_state_conditioning_ready": any(
            isinstance(row.get("evolution_surface"), dict)
            and row["evolution_surface"].get("game_state_conditioning_ready") is True
            for row in findings
        ),
        "tracking_claim_introduced": False,
        "provider_label_promoted_to_tactical_truth": False,
        "absence_promoted_to_counterevidence": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
