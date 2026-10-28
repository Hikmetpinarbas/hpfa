from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import active_match_spine_runner as runner
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)


def _feature_payload() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "right_censoring_is_failure": False,
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "delta_1",
                "source_process_variant_family_ref": "family_1",
                "context_coverage_incomplete_variant_count": 0,
                "consequence_coverage_incomplete_variant_count": 0,
                "context_feature_difference_candidates": [
                    {
                        "feature_token": "provider_zone_candidates:FINAL_THIRD",
                        "success_visible_numerator": 2,
                        "success_eligible_denominator": 3,
                        "failure_visible_numerator": 0,
                        "failure_eligible_denominator": 2,
                        "descriptive_rate_delta_success_minus_failure": 0.666667,
                        "dependency_independence_proven": False,
                        "statistical_independence_proven": False,
                    }
                ],
                "consequence_feature_difference_candidates": [],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_payload() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "team_identity_candidate_ids": ["team_b", "team_a"],
                "period_candidates": ["2", "1"],
                "dependency_group_ref_count": 2,
                "dependency_group_refs": ["dep_b", "dep_a"],
                "family_is_independent_recurrence_truth": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


@pytest.mark.parametrize(
    ("target", "key", "unsafe_value"),
    [
        ("feature", "canonical_event_count", 123),
        ("feature", "true_action_count", 456),
        ("feature", "production_release", True),
        ("feature", "feature_absence_is_counterevidence", True),
        ("feature", "no_visible_followup_is_failure", True),
        ("feature", "right_censoring_is_failure", True),
        ("process", "canonical_event_count", 123),
        ("process", "true_action_count", 456),
        ("process", "production_release", True),
    ],
)
def test_truth_lock_fault_injection_fails_closed_without_emit(target, key, unsafe_value) -> None:
    feature = _feature_payload()
    process = _process_payload()
    (feature if target == "feature" else process)[key] = unsafe_value

    result = build_variant_feature_challenge_projection(feature, process)

    assert result["status"] == "FAIL_CLOSED"
    assert result["variant_feature_challenge_records"] == []
    assert result["professional_finding_emit_allowed"] is False
    assert result["production_release"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"


def test_unresolved_dependency_family_fails_closed_without_partial_output() -> None:
    feature = _feature_payload()
    feature["grammar_stable_variant_feature_delta_records"][0]["source_process_variant_family_ref"] = "missing_family"

    result = build_variant_feature_challenge_projection(feature, _process_payload())

    assert result["status"] == "FAIL_CLOSED"
    assert result["variant_feature_challenge_record_count"] == 0
    assert any(hit.startswith("source_process_variant_family_unresolved:") for hit in result["hard_block_hits"])
    assert result["professional_finding_emit_allowed"] is False


def test_invalid_rate_contract_fails_closed_instead_of_silent_coercion() -> None:
    feature = _feature_payload()
    row = feature["grammar_stable_variant_feature_delta_records"][0]["context_feature_difference_candidates"][0]
    row["success_visible_numerator"] = 4
    row["success_eligible_denominator"] = 3

    result = build_variant_feature_challenge_projection(feature, _process_payload())

    assert result["status"] == "FAIL_CLOSED"
    assert result["variant_feature_challenge_record_count"] == 0
    assert "feature_difference_contract_invalid:delta_1" in result["hard_block_hits"]


def test_family_set_order_and_duplicate_whitespace_are_metamorphically_invariant() -> None:
    baseline = build_variant_feature_challenge_projection(_feature_payload(), _process_payload())
    mutated_process = _process_payload()
    family = mutated_process["observable_process_variant_families"][0]
    family["team_identity_candidate_ids"] = [" team_a ", "team_b", "team_a"]
    family["period_candidates"] = ["1", " 2 ", "1"]
    family["dependency_group_refs"] = ["dep_a", " dep_b ", "dep_a"]

    mutated = build_variant_feature_challenge_projection(_feature_payload(), mutated_process)

    assert mutated["status"] == baseline["status"]
    assert mutated["variant_feature_challenge_records"] == baseline["variant_feature_challenge_records"]
    assert mutated["hard_block_hits"] == baseline["hard_block_hits"]
    assert mutated["review_hits"] == baseline["review_hits"]


def test_source_record_permutation_preserves_semantic_challenge_set() -> None:
    feature = _feature_payload()
    second = deepcopy(feature["grammar_stable_variant_feature_delta_records"][0])
    second["grammar_stable_variant_feature_delta_id"] = "delta_2"
    feature["grammar_stable_variant_feature_delta_records"].append(second)

    forward = build_variant_feature_challenge_projection(feature, _process_payload())
    reversed_feature = deepcopy(feature)
    reversed_feature["grammar_stable_variant_feature_delta_records"].reverse()
    reverse = build_variant_feature_challenge_projection(reversed_feature, _process_payload())

    forward_rows = {row["variant_feature_challenge_id"]: row for row in forward["variant_feature_challenge_records"]}
    reverse_rows = {row["variant_feature_challenge_id"]: row for row in reverse["variant_feature_challenge_records"]}
    assert reverse_rows == forward_rows
    assert reverse["variant_feature_challenge_record_count"] == forward["variant_feature_challenge_record_count"]
    assert reverse["professional_finding_emit_allowed"] is False


def test_current_invocation_ledger_deduplicates_repeated_artifact_refs(tmp_path: Path, monkeypatch) -> None:
    challenge = tmp_path / "variant_feature_challenge_projection_v1.json"
    challenge.write_text("{}", encoding="utf-8")
    safe = tmp_path / "safe_finding_admission_projection_v1.json"

    monkeypatch.setattr(
        runner,
        "materialize_variant_feature_challenge",
        lambda _out: {
            "status": "REVIEW_REQUIRED",
            "artifact_materialized": True,
            "output": str(challenge),
            "post_sequence_current_invocation_artifacts": [str(safe), str(safe), str(challenge)],
            "projection_creates_new_evidence": False,
            "professional_finding_emit_allowed": False,
        },
    )
    result = {
        "status": "REVIEW_REQUIRED",
        "current_invocation_artifacts": [str(challenge), str(challenge)],
        "engineering_evidence": {},
    }

    runner._bind_variant_feature_challenge_runtime(result, tmp_path)

    assert result["current_invocation_artifacts"] == sorted({str(challenge), str(safe)})
    assert result["engineering_evidence"]["variant_feature_challenge_can_authorize_emit"] is False
