from __future__ import annotations

from copy import deepcopy

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
)


def _sequence() -> dict:
    return {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "support": {"visible_success_sequence_refs": ["s1"]},
                "counterevidence": {"visible_failure_sequence_refs": ["s2"]},
            }
        ]
    }


def _admission() -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "DOWNGRADE",
                "decision_reasons": [],
                "claim_output_allowed": False,
                "claim_ceiling": "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY",
                "admitted_independent_support_count": 2,
                "dependency_independence_proven": True,
                "statistical_independence_proven": True,
                "episode_spread_state": "UNKNOWN",
                "episode_spread_count": "UNKNOWN",
            }
        ],
        "safe_finding_admission_decision_count": 1,
        "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0},
        "professional_finding_emitted_count": 0,
        "claim_output_allowed_count": 0,
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_minimum() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "visible_episode_spread_count": 2,
                "visible_episode_spread_state": "MULTIPLE_VISIBLE_EPISODE_CANDIDATES",
                "occurrence_disjoint_support_cluster_count": 2,
                "occurrence_disjoint_support_cluster_state": "MULTIPLE_OCCURRENCE_DISJOINT_SUPPORT_CLUSTERS_VISIBLE",
                "success_visible_episode_spread_count": 1,
                "failure_visible_episode_spread_count": 1,
                "member_records": [
                    {"sequence_ref": "s1", "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE"},
                    {"sequence_ref": "s2", "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE"},
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _challenge_minimum() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "vfc_1",
                "source_process_variant_family_ref": "family_1",
                "challenge_reasons": ["SAMPLE_STRENGTH_UNCALIBRATED"],
                "counter_scenario_candidates": ["SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"],
                "withdrawal_conditions": [
                    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_DISAPPEARS_IN_ADMITTED_COMPARABLE_CONTEXT"
                ],
                "relevant_coverage_incomplete_variant_count": 0,
                "dependency_independence_proven": True,
                "statistical_independence_proven": True,
            }
        ],
        "difference_rows_are_independent_evidence_votes": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "unassessed_censoring_can_be_treated_as_failure": False,
        "professional_finding_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _run(challenge: dict, process: dict) -> dict:
    return apply_variant_feature_challenge_to_admission(
        _sequence(), _admission(), challenge, process
    )


def _consumer_view(result: dict) -> dict:
    row = result["safe_finding_admission_decisions"][0] if result.get("safe_finding_admission_decisions") else {}
    return {
        "status": result.get("status"),
        "decision": row.get("decision"),
        "claim_output_allowed": row.get("claim_output_allowed"),
        "decision_reasons": row.get("decision_reasons"),
        "challenge_refs": row.get("variant_feature_challenge_refs"),
        "challenge_reason_codes": row.get("variant_feature_challenge_reason_codes"),
        "counter_scenarios": row.get("counter_scenario_candidates"),
        "withdrawals": row.get("withdrawal_condition_candidates"),
        "episode_spread_state": row.get("episode_spread_state"),
        "episode_spread_count": row.get("episode_spread_count"),
        "support_count": row.get("admitted_independent_support_count"),
        "professional_finding_emitted_count": result.get("professional_finding_emitted_count"),
        "can_increase_support": result.get("variant_feature_challenge_can_increase_support"),
        "can_authorize_emit": result.get("variant_feature_challenge_can_authorize_emit"),
        "canonical_event_count": result.get("canonical_event_count"),
        "true_action_count": result.get("true_action_count"),
        "production_release": result.get("production_release"),
    }


def test_rich_producer_payload_is_differentially_equivalent_to_consumer_minimum() -> None:
    baseline = _run(_challenge_minimum(), _process_minimum())
    rich_challenge = deepcopy(_challenge_minimum())
    rich_challenge.update({
        "producer_internal_debug": {"cache_key": "opaque", "rows_scanned": 999},
        "source_feature_delta_record_count": 77,
        "claim_ceiling": "MATCH_LOCAL_DESCRIPTIVE_VARIANT_FEATURE_CHALLENGE_PACKET_ONLY",
        "review_hits": ["producer_internal_review_marker"],
    })
    rich_challenge["variant_feature_challenge_records"][0].update({
        "feature_surface": "CONTEXT",
        "feature_token": "provider_zone_candidates:FINAL_THIRD",
        "descriptive_rate_delta_success_minus_failure": 0.5,
        "analyst_hypothesis_review_candidate": True,
        "producer_only_diagnostic": "ignored_by_consumer_contract",
    })
    rich_process = deepcopy(_process_minimum())
    rich_process.update({"producer_internal_debug": {"source_rows": 1234}, "family_count": 1})
    rich_process["observable_process_variant_families"][0].update({
        "member_count": 2,
        "supporting_occurrence_slot_count": 8,
        "producer_only_metric": 42,
    })

    rich = _run(rich_challenge, rich_process)

    assert _consumer_view(rich) == _consumer_view(baseline)


def test_unused_top_level_producer_field_removal_is_differentially_invariant() -> None:
    rich = deepcopy(_challenge_minimum())
    rich["unused_optional_field"] = {"anything": [1, 2, 3]}
    with_extra = _run(rich, _process_minimum())
    without_extra = _run(_challenge_minimum(), _process_minimum())
    assert _consumer_view(with_extra) == _consumer_view(without_extra)


def test_challenge_record_order_is_differentially_invariant_for_consumer_semantics() -> None:
    challenge = _challenge_minimum()
    second = deepcopy(challenge["variant_feature_challenge_records"][0])
    second["variant_feature_challenge_id"] = "vfc_2"
    second["challenge_reasons"] = ["CONTEXT_ROBUSTNESS_NOT_TESTED"]
    challenge["variant_feature_challenge_records"].append(second)

    forward = _run(challenge, _process_minimum())
    reversed_payload = deepcopy(challenge)
    reversed_payload["variant_feature_challenge_records"].reverse()
    reverse = _run(reversed_payload, _process_minimum())

    assert _consumer_view(reverse) == _consumer_view(forward)


def test_process_member_order_is_differentially_invariant() -> None:
    forward = _run(_challenge_minimum(), _process_minimum())
    reversed_process = deepcopy(_process_minimum())
    reversed_process["observable_process_variant_families"][0]["member_records"].reverse()
    reverse = _run(_challenge_minimum(), reversed_process)
    assert _consumer_view(reverse) == _consumer_view(forward)


def test_missing_consumed_emit_lock_fails_closed() -> None:
    challenge = _challenge_minimum()
    challenge.pop("professional_finding_emit_allowed")
    result = _run(challenge, _process_minimum())
    assert result["status"] == "FAIL_CLOSED"
    assert result["safe_finding_admission_decisions"] == []
    assert "variant_feature_challenge_emit_lock_not_false" in result["hard_block_hits"]
    assert result["professional_finding_emitted_count"] == 0


def test_missing_consumed_independent_vote_lock_fails_closed() -> None:
    challenge = _challenge_minimum()
    challenge.pop("difference_rows_are_independent_evidence_votes")
    result = _run(challenge, _process_minimum())
    assert result["status"] == "FAIL_CLOSED"
    assert "variant_feature_challenge_independent_vote_lock_breached" in result["hard_block_hits"]


def test_extra_producer_support_claim_cannot_increase_consumer_support() -> None:
    challenge = _challenge_minimum()
    challenge["variant_feature_challenge_records"][0]["producer_claimed_support_count"] = 999
    result = _run(challenge, _process_minimum())
    row = result["safe_finding_admission_decisions"][0]
    assert row["admitted_independent_support_count"] == 2
    assert result["variant_feature_challenge_can_increase_support"] is False
    assert result["variant_feature_challenge_refs_are_independent_evidence_votes"] is False


def test_consumer_contract_preserves_downstream_non_strengthening_ceiling() -> None:
    result = _run(_challenge_minimum(), _process_minimum())
    row = result["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert result["professional_finding_emitted_count"] == 0
    assert result["variant_feature_challenge_can_authorize_emit"] is False
    assert result["variant_feature_challenge_can_increase_support"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
