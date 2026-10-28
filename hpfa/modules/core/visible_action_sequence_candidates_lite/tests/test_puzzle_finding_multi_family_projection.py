from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.puzzle_finding_contract_adapter import (
    build_puzzle_finding_contract,
)


def _handoff() -> dict:
    return {
        "safe_finding_handoff_candidate_id": "sfh_family_test",
        "source_first_supported_branch_divergence_ref": "fsbd_family_test",
        "professional_finding_emit_allowed": False,
        "what_visible": {"state": "VISIBLE_VARIATION"},
        "where_when": {
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "shared_anchor_time_layer_ref": "layer_1",
            "anchor_centered_sequence_branch_map_ref": "map_1",
        },
        "support": {
            "visible_success_sequence_refs": ["seq_s"],
            "visible_success_numerator": 1,
            "eligible_denominator": 2,
            "admitted_independent_support_count": 0,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
        },
        "counterevidence": {
            "visible_failure_sequence_refs": ["seq_f"],
            "comparable_counterexample_refs": [],
            "absence_used_as_counterevidence": False,
        },
        "evidence_sufficiency": {
            "state": "INSUFFICIENT_FOR_PROFESSIONAL_EMIT",
            "blocking_dimensions": ["INDEPENDENT_SUPPORT_NOT_ADMITTED"],
        },
        "alternative_explanations": [],
        "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIATION_ONLY",
        "forbidden_inference": ["TACTICAL_PATTERN_TRUTH", "CAUSALITY"],
        "uncertainty": {"independent_support_count": 0},
        "withdrawal_conditions": ["WITHDRAW_IF_SOURCE_INVALIDATED"],
        "analyst_action": "REVIEW_VISIBLE_EXAMPLES",
        "analyst_summary_tr": "Görünür varyasyon.",
        "safe_finding_handoff_is_professional_finding_truth": False,
        "safe_finding_handoff_is_tactical_truth": False,
        "safe_finding_handoff_is_causal_truth": False,
        "safe_finding_handoff_is_coach_intention_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _divergence(*, progression: bool = False, turnover: bool = False, recovery: bool = False) -> dict:
    family_counts: dict[str, int] = {"PASS": 1}
    if turnover:
        family_counts["TURNOVER"] = 1
    if recovery:
        family_counts["RECOVERY"] = 1
    return {
        "first_supported_branch_divergence_id": "fsbd_family_test",
        "branch_profiles": [
            {
                "neighbor_action_family_counts": family_counts,
                "semantic_profiles": [
                    {
                        "progression_values": ["PROGRESSIVE_CANDIDATE"] if progression else [],
                    }
                ],
            }
        ],
        "divergence_is_tactical_truth": False,
        "divergence_is_failure_cause_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _sequence(divergence: dict | None) -> dict:
    payload = {
        "safe_finding_handoff_candidates": [_handoff()],
        "safe_finding_handoff_professional_emit_allowed": False,
        "first_supported_branch_divergence_candidates": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    if divergence is not None:
        payload["first_supported_branch_divergence_candidates"] = [divergence]
    return payload


def _admission() -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_family_test",
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
                "claim_ceiling": "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _by_id(result: dict) -> dict[str, dict]:
    return {row["puzzle_id"]: row for row in result["puzzle_findings"]}


def test_progression_family_view_preserves_safe_finding_and_denominator_lineage() -> None:
    result = build_puzzle_finding_contract(_sequence(_divergence(progression=True)), _admission())

    assert result["status"] == "PASS"
    assert result["puzzle_finding_count"] == 2
    assert result["bound_puzzle_ids"] == ["P6_PROCESS_VARIANT_DIVERGENCE", "PROGRESSION_ACCESS"]
    rows = _by_id(result)
    base = rows["P6_PROCESS_VARIANT_DIVERGENCE"]
    progression = rows["PROGRESSION_ACCESS"]

    assert base["finding_status"] == "DOWNGRADE"
    assert progression["finding_status"] == "DOWNGRADE"
    assert progression["claim_output_allowed"] is False
    assert progression["support"] == base["support"]
    assert progression["comparison_surface"]["visible_success_numerator"] == 1
    assert progression["comparison_surface"]["eligible_denominator"] == 2
    assert progression["family_projection"]["creates_new_evidence"] is False
    assert progression["family_projection"]["family_view_is_independent_support"] is False
    assert progression["fusion_surface"]["admitted_independent_support_count"] == 0
    assert progression["same_timestamp_internal_ordering_allowed"] is False
    assert progression["puzzle_finding_is_tactical_truth"] is False
    assert progression["puzzle_finding_is_causal_truth"] is False
    assert progression["family_projection"]["tracking_claim_introduced"] is False
    assert progression["canonical_event_count"] == "UNKNOWN"
    assert progression["true_action_count"] == "UNKNOWN"
    assert progression["production_release"] is False


def test_turnover_and_progression_can_create_two_non_independent_family_views() -> None:
    result = build_puzzle_finding_contract(
        _sequence(_divergence(progression=True, turnover=True)),
        _admission(),
    )

    assert result["puzzle_finding_count"] == 3
    assert result["additional_family_projection_counts"] == {
        "PROGRESSION_ACCESS": 1,
        "RETENTION_LOSS": 1,
    }
    rows = _by_id(result)
    retention = rows["RETENTION_LOSS"]
    assert retention["finding_status"] == "DOWNGRADE"
    assert retention["family_view_is_independent_support"] is False
    assert retention["family_projection"]["observed_signals"] == {
        "turnover_family_visible_count": 1
    }
    assert result["family_view_count_is_independent_support_count"] is False
    assert result["cross_mechanism_fusion_performed"] is False
    assert result["mechanism_candidate_emitted"] is False


def test_missing_or_stale_divergence_source_does_not_create_extra_family_view() -> None:
    result = build_puzzle_finding_contract(_sequence(None), _admission())

    assert result["status"] == "PASS"
    assert result["puzzle_finding_count"] == 1
    assert result["bound_puzzle_ids"] == ["P6_PROCESS_VARIANT_DIVERGENCE"]
    assert result["additional_family_projection_counts"] == {}
    assert result["additional_family_projection_missing_source_count"] == 1
    assert result["creates_new_evidence"] is False


def test_recovery_name_alone_is_not_enabled_as_a_family_without_accepted_v1_binding() -> None:
    result = build_puzzle_finding_contract(_sequence(_divergence(recovery=True)), _admission())

    assert result["puzzle_finding_count"] == 1
    assert "RECOVERY_TRANSITION" not in result["bound_puzzle_ids"]
    assert result["recovery_transition_family_enabled"] is False
    assert result["cross_mechanism_fusion_performed"] is False
    assert result["tracking_claim_introduced"] is False
    assert result["provider_label_promoted_to_tactical_truth"] is False
    assert result["absence_promoted_to_counterevidence"] is False
