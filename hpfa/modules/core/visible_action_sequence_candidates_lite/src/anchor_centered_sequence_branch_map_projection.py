from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "OUTCOME_BLIND_SHARED_ANCHOR_BRANCH_MAP_CANDIDATE_ONLY"
COMPARABLE_SET_CLAIM_CEILING = "SHARED_ORIGIN_OUTCOME_BLIND_BRANCH_COMPARABLE_SET_CANDIDATE_ONLY"
BRANCH_COMPARISON_QUESTION_CONTRACT = {
    "comparison_question_id": "shared_visible_anchor_branch_contrast_v1",
    "football_question": "After the same admitted visible occurrence-temporal anchor, which immediate visible successor branches differ before their consequences are read?",
    "analysis_scale": "OCCURRENCE_TEMPORAL_EDGE_VARIANT",
    "candidate_universe": "CURRENT_MATCH_OCCURRENCE_TEMPORAL_PRIMARY_SEQUENCE_CANDIDATES",
    "anchor_process_family": "SHARED_VISIBLE_TIME_LAYER_ANCHOR_CANDIDATE",
    "comparison_target": "IMMEDIATE_POST_ANCHOR_VISIBLE_BRANCH_CONTRAST",
    "required_exact_dimensions": ["team", "period", "shared_visible_anchor"],
    "required_coarsened_dimensions": [],
    "allowed_test_dimensions": ["post_anchor_branch_structure"],
    "optional_similarity_dimensions": [],
    "forbidden_leakage_dimensions": [
        "branch_outcome",
        "provider_success_failure",
        "terminal_consequence",
        "post_divergence_actor",
        "post_divergence_zone",
        "post_divergence_route",
    ],
    "required_observation_capabilities": [
        "TEAM_IDENTITY",
        "PERIOD_CONTEXT",
        "OCCURRENCE_IDENTITY",
        "TEMPORAL_LAYER",
        "CONFIRMED_AFTER_RELATION",
    ],
    "optional_observation_capabilities": [],
    "consequence_horizon": "ATTACH_ONLY_AFTER_COMPARABLE_SET_FREEZE",
    "minimum_support_rule": "AT_LEAST_TWO_ELIGIBLE_EDGE_VARIANTS_FROM_THE_SAME_VISIBLE_ANCHOR",
    "minimum_spread_rule": "DESCRIBE_BRANCH_SUPPORT_DO_NOT_INFER_INDEPENDENCE",
    "claim_ceiling": COMPARABLE_SET_CLAIM_CEILING,
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _branch_partition_id(anchor_layer_id: str, successor_layer_id: str) -> str:
    return "branch_" + _digest(anchor_layer_id, successor_layer_id)[:20]


def _build_branch_comparable_sets(
    sequences: list[dict[str, Any]],
    layer_by_id: dict[str, dict[str, Any]],
    blocks: list[str],
    reviews: list[str],
) -> list[dict[str, Any]]:
    members_by_anchor: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    sequence_by_id: dict[str, dict[str, Any]] = {}

    for sequence in sequences:
        sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
        team = _clean(sequence.get("team_identity_candidate_id"))
        period = _clean(sequence.get("period_candidate"))
        layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
        if not sequence_id or not team or not period or len(layer_ids) < 2:
            reviews.append(f"branch_comparison_sequence_not_eligible:{sequence_id or 'UNKNOWN'}")
            continue
        if sequence.get("same_timestamp_internal_ordering_allowed") is not False:
            blocks.append(f"branch_comparison_sequence_same_time_policy_breached:{sequence_id}")
            continue
        if sequence.get("source_row_order_is_temporal_truth") is not False:
            blocks.append(f"branch_comparison_sequence_row_order_policy_breached:{sequence_id}")
            continue
        if sequence.get("visible_sequence_candidate_is_sequence_truth") is True:
            blocks.append(f"branch_comparison_sequence_truth_promotion_breached:{sequence_id}")
            continue
        if any(layer_id not in layer_by_id for layer_id in layer_ids[:2]):
            blocks.append(f"branch_comparison_layer_reference_missing:{sequence_id}")
            continue
        sequence_by_id[sequence_id] = sequence
        members_by_anchor[(team, period, layer_ids[0])].add(sequence_id)

    comparable_sets: list[dict[str, Any]] = []
    for (team, period, anchor_layer_id), member_ids_set in sorted(members_by_anchor.items()):
        member_ids = sorted(member_ids_set)
        if len(member_ids) < 2:
            continue
        anchor = layer_by_id.get(anchor_layer_id)
        if anchor is None:
            blocks.append(f"branch_comparison_anchor_layer_missing:{anchor_layer_id}")
            continue
        anchor_occurrence_ids = sorted({
            _clean(value)
            for value in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
            if _clean(value)
        })
        if not anchor_occurrence_ids:
            reviews.append(f"branch_comparison_anchor_occurrence_identity_missing:{anchor_layer_id}")
            continue
        successor_layer_ids = sorted({
            _clean((sequence_by_id[sequence_id].get("time_layer_candidate_ids") or [None, None])[1])
            for sequence_id in member_ids
            if len(sequence_by_id[sequence_id].get("time_layer_candidate_ids") or []) >= 2
            and _clean((sequence_by_id[sequence_id].get("time_layer_candidate_ids") or [None, None])[1])
        })
        comparable_set_id = "bcs_" + _digest(
            BRANCH_COMPARISON_QUESTION_CONTRACT["comparison_question_id"],
            team,
            period,
            anchor_layer_id,
            member_ids,
        )[:24]
        comparable_sets.append({
            "comparable_set_id": comparable_set_id,
            "comparison_question_id": BRANCH_COMPARISON_QUESTION_CONTRACT["comparison_question_id"],
            "team": team,
            "analysis_scale": BRANCH_COMPARISON_QUESTION_CONTRACT["analysis_scale"],
            "anchor_process_family": BRANCH_COMPARISON_QUESTION_CONTRACT["anchor_process_family"],
            "eligibility_grade": "STRICT_ELIGIBLE",
            "member_process_candidate_ids": member_ids,
            "eligible_case_count": len(member_ids),
            "unique_dependency_group_count": "UNKNOWN",
            "required_exact_dimensions": list(BRANCH_COMPARISON_QUESTION_CONTRACT["required_exact_dimensions"]),
            "required_coarsened_dimensions": [],
            "allowed_test_dimensions": list(BRANCH_COMPARISON_QUESTION_CONTRACT["allowed_test_dimensions"]),
            "resolved_context": {
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "shared_anchor_time_layer_ref": anchor_layer_id,
                "shared_anchor_action_family_counts": dict(sorted((anchor.get("action_family_counts") or {}).items())),
                "shared_anchor_occurrence_candidate_ids": anchor_occurrence_ids,
            },
            "unresolved_context": [],
            "prefix_support_summary": {
                "prefix_type": "SAME_ADMITTED_VISIBLE_TIME_LAYER_ANCHOR",
                "prefix_layer_count": 1,
                "shared_anchor_time_layer_ref": anchor_layer_id,
                "shared_anchor_occurrence_candidate_ids": anchor_occurrence_ids,
                "shared_prefix_support_n": len(member_ids),
            },
            "partial_order_state": "SAME_TIME_UNORDERED_PRESERVED",
            "censoring_burden": "NOT_EVALUATED_BEFORE_OUTCOME_ATTACHMENT",
            "dependency_burden": "SHARED_VISIBLE_ANCHOR_DEPENDENCY_DOMINATED",
            "episode_spread": "UNKNOWN",
            "actor_spread": "UNKNOWN",
            "context_spread": {"period_count": 1, "successor_layer_candidate_count": len(successor_layer_ids)},
            "successor_layer_candidate_ids": successor_layer_ids,
            "eligible_denominator_frozen_before_outcome_attachment": True,
            "outcome_used_in_eligibility": False,
            "post_anchor_branch_structure_used_in_eligibility": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "comparable_set_is_finding": False,
            "comparable_set_is_recurrence_truth": False,
            "comparable_set_is_process_identity_truth": False,
            "comparable_set_is_tactical_pattern_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": COMPARABLE_SET_CLAIM_CEILING,
        })
    return comparable_sets


def build_anchor_centered_sequence_branch_maps(payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if payload.get("primary_sequence_projection_mode") != "OCCURRENCE_TEMPORAL_PRIMARY":
        blocks.append("occurrence_temporal_primary_inventory_not_admitted")
    if payload.get("occurrence_temporal_primary_inventory_admitted") is not True:
        blocks.append("occurrence_temporal_primary_inventory_flag_not_true")
    if payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if payload.get("sequence_truth") is True or payload.get("possession_truth") is True:
        blocks.append("upstream_truth_promotion_breached")
    if payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    layers = [row for row in (payload.get("visible_action_time_layer_candidates") or []) if isinstance(row, dict)]
    sequences = [row for row in (payload.get("visible_action_sequence_candidates") or []) if isinstance(row, dict)]
    layer_by_id = {
        _clean(row.get("visible_action_time_layer_candidate_id")): row
        for row in layers
        if _clean(row.get("visible_action_time_layer_candidate_id"))
    }
    sequence_by_id = {
        _clean(row.get("visible_action_sequence_candidate_id")): row
        for row in sequences
        if _clean(row.get("visible_action_sequence_candidate_id"))
    }

    # Stage 1: freeze the question-conditioned comparable set using only pre-divergence
    # admitted context and the shared physical anchor. No consequence or successor
    # structure participates in admission.
    comparable_sets = _build_branch_comparable_sets(
        sequences,
        layer_by_id,
        blocks,
        reviews,
    )

    # Stage 2: only after the eligible denominator is frozen, partition immediate
    # successors and attach their visible consequence descriptors.
    branch_maps: list[dict[str, Any]] = []
    for comparable_set in comparable_sets:
        member_ids = [
            _clean(value)
            for value in (comparable_set.get("member_process_candidate_ids") or [])
            if _clean(value)
        ]
        anchor_layer_id = _clean(
            (comparable_set.get("resolved_context") or {}).get("shared_anchor_time_layer_ref")
        )
        team = _clean(comparable_set.get("team"))
        period = _clean((comparable_set.get("resolved_context") or {}).get("period_candidate"))
        anchor = layer_by_id.get(anchor_layer_id)
        if anchor is None:
            blocks.append(f"branch_map_anchor_layer_missing:{anchor_layer_id or 'UNKNOWN'}")
            continue

        sequences_by_successor: dict[str, set[str]] = defaultdict(set)
        for sequence_id in member_ids:
            sequence = sequence_by_id.get(sequence_id)
            if sequence is None:
                blocks.append(f"branch_map_comparable_member_missing:{sequence_id}")
                continue
            layer_ids = [_clean(value) for value in (sequence.get("time_layer_candidate_ids") or []) if _clean(value)]
            if len(layer_ids) < 2 or layer_ids[0] != anchor_layer_id:
                blocks.append(f"branch_map_comparable_member_anchor_mismatch:{sequence_id}")
                continue
            sequences_by_successor[layer_ids[1]].add(sequence_id)

        # No visible divergence exists unless at least two distinct immediate
        # successor partitions survive after the outcome-blind denominator freeze.
        if len(sequences_by_successor) < 2:
            continue

        branch_records: list[dict[str, Any]] = []
        branch_partition: list[dict[str, Any]] = []
        branch_support_counts: dict[str, int] = {}
        branch_consequence_profiles: list[dict[str, Any]] = []
        supporting_sequence_ids: set[str] = set()
        supporting_occurrence_ids: set[str] = {
            _clean(value)
            for value in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
            if _clean(value)
        }

        for successor_layer_id, sequence_ids_set in sorted(sequences_by_successor.items()):
            successor = layer_by_id.get(successor_layer_id)
            if successor is None:
                blocks.append(f"branch_map_successor_layer_missing:{successor_layer_id}")
                continue
            sequence_ids = sorted(sequence_ids_set)
            supporting_sequence_ids.update(sequence_ids)
            branch_occurrence_ids = sorted({
                _clean(value)
                for value in (successor.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(value)
            })
            supporting_occurrence_ids.update(branch_occurrence_ids)

            branch_id = _branch_partition_id(anchor_layer_id, successor_layer_id)
            branch_partition.append({
                "branch_id": branch_id,
                "successor_time_layer_ref": successor_layer_id,
                "member_process_candidate_ids": sequence_ids,
                "branch_support_n": len(sequence_ids),
            })
            branch_support_counts[branch_id] = len(sequence_ids)

            consequence_counts: Counter[str] = Counter()
            consequence_ids: set[str] = set()
            for sequence_id in sequence_ids:
                sequence = sequence_by_id.get(sequence_id) or {}
                consequence_counts.update(sequence.get("consequence_candidate_counts") or {})
                consequence_ids.update(
                    _clean(value)
                    for value in (sequence.get("supporting_consequence_candidate_ids") or [])
                    if _clean(value)
                )
            consequence_profile = {
                "branch_id": branch_id,
                "successor_time_layer_ref": successor_layer_id,
                "supporting_consequence_candidate_ids": sorted(consequence_ids),
                "observed_consequence_candidate_counts": dict(sorted(consequence_counts.items())),
                "consequence_attached_after_comparable_set_freeze": True,
            }
            branch_consequence_profiles.append(consequence_profile)

            branch_records.append({
                "branch_id": branch_id,
                "branch_direction": "SUCCESSOR",
                "neighbor_time_layer_ref": successor_layer_id,
                "neighbor_time_candidate": successor.get("start_candidate"),
                "neighbor_action_family_counts": dict(sorted((successor.get("action_family_counts") or {}).items())),
                "neighbor_supporting_action_occurrence_candidate_ids": branch_occurrence_ids,
                "supporting_visible_sequence_candidate_ids": sequence_ids,
                "supporting_consequence_candidate_ids": sorted(consequence_ids),
                "observed_consequence_candidate_counts": dict(sorted(consequence_counts.items())),
                "branch_supporting_sequence_count": len(sequence_ids),
                "branch_support_count_is_recurrence_count": False,
                "consequence_attached_after_comparable_set_freeze": True,
                "branch_is_tactical_route_truth": False,
                "branch_is_causal_path_truth": False,
            })

        if blocks:
            continue

        # Structural identity is outcome-blind: changing consequence labels must not
        # create a different branch-map identity for the same frozen set/partition.
        structural_partition_identity = [
            {
                "branch_id": row["branch_id"],
                "successor_time_layer_ref": row["successor_time_layer_ref"],
                "member_process_candidate_ids": row["member_process_candidate_ids"],
            }
            for row in branch_partition
        ]
        map_id = "acbm_" + _digest(
            comparable_set.get("comparable_set_id"),
            structural_partition_identity,
        )[:24]
        eligible_denominator = int(comparable_set.get("eligible_case_count") or 0)
        branch_maps.append({
            "branch_map_id": map_id,
            "anchor_centered_sequence_branch_map_id": map_id,
            "comparable_set_id": comparable_set.get("comparable_set_id"),
            "comparison_question_id": comparable_set.get("comparison_question_id"),
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "anchor_type": "OCCURRENCE_TEMPORAL_TIME_LAYER_CANDIDATE",
            "anchor_time_layer_ref": anchor_layer_id,
            "anchor_time_candidate": anchor.get("start_candidate"),
            "anchor_action_family_counts": dict(sorted((anchor.get("action_family_counts") or {}).items())),
            "anchor_supporting_action_occurrence_candidate_ids": sorted({
                _clean(value)
                for value in (anchor.get("supporting_action_occurrence_candidate_ids") or [])
                if _clean(value)
            }),
            "shared_prefix_candidate": comparable_set.get("prefix_support_summary"),
            "shared_prefix_support_n": eligible_denominator,
            "eligible_denominator_n": eligible_denominator,
            "branch_partition": branch_partition,
            "branch_support_counts": dict(sorted(branch_support_counts.items())),
            "branch_consequence_profiles": branch_consequence_profiles,
            "no_visible_followup_count": "NOT_CLASSIFIED_AT_BRANCH_MAP_STAGE",
            "censored_count": "NOT_CLASSIFIED_AT_BRANCH_MAP_STAGE",
            "unresolved_count": "NOT_CLASSIFIED_AT_BRANCH_MAP_STAGE",
            "counterexample_refs": [],
            "predecessor_branch_count": 0,
            "successor_branch_count": len(branch_records),
            "total_visible_branch_count": len(branch_records),
            "branch_records": branch_records,
            "supporting_visible_sequence_candidate_ids": sorted(supporting_sequence_ids),
            "supporting_action_occurrence_candidate_ids": sorted(supporting_occurrence_ids),
            "eligible_denominator_frozen_before_branch_consequence_attachment": True,
            "outcome_used_in_comparison_admission": False,
            "outcome_used_in_branch_partition": False,
            "post_anchor_branch_structure_used_in_comparison_admission": False,
            "branch_count_is_recurrence_count": False,
            "branch_map_is_sequence_truth": False,
            "branch_map_is_possession_truth": False,
            "branch_map_is_tactical_plan_truth": False,
            "branch_map_is_causal_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or str(payload.get("status") or "").upper() == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "branch_comparison_question_contract": dict(BRANCH_COMPARISON_QUESTION_CONTRACT),
        "branch_comparison_question_contract_status": "PASS" if not blocks else "FAIL_CLOSED",
        "branch_comparable_sets": comparable_sets if not blocks else [],
        "branch_comparable_set_count": len(comparable_sets) if not blocks else 0,
        "anchor_centered_sequence_branch_maps": branch_maps if not blocks else [],
        "anchor_centered_sequence_branch_map_count": len(branch_maps) if not blocks else 0,
        "source_visible_action_sequence_candidate_count": len(sequences),
        "source_visible_action_time_layer_candidate_count": len(layers),
        "total_visible_branch_count": sum(row.get("total_visible_branch_count", 0) for row in branch_maps) if not blocks else 0,
        "comparable_set_frozen_before_branch_map": True,
        "eligible_denominator_frozen_before_branch_consequence_attachment": True,
        "outcome_used_in_comparison_admission": False,
        "outcome_used_in_branch_partition": False,
        "post_anchor_branch_structure_used_in_comparison_admission": False,
        "branch_count_is_recurrence_count": False,
        "branch_map_is_sequence_truth": False,
        "branch_map_is_possession_truth": False,
        "branch_map_is_tactical_plan_truth": False,
        "branch_map_is_causal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
