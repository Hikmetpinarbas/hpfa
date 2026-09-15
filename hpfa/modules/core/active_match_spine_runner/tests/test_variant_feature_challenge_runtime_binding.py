from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.variant_feature_challenge_runtime_binding import (
    FEATURE_DELTA_JSON,
    OUTPUT_JSON,
    PROCESS_VARIANT_JSON,
    materialize_variant_feature_challenge,
)


def _feature_delta() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "feature_absence_is_counterevidence": False,
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


def _process_variant() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["1"],
                "dependency_group_ref_count": 1,
                "dependency_group_refs": ["dep_1"],
                "family_is_independent_recurrence_truth": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_materializes_existing_challenge_projection_without_claim_inflation(tmp_path: Path) -> None:
    (tmp_path / FEATURE_DELTA_JSON).write_text(
        json.dumps(_feature_delta()), encoding="utf-8"
    )
    (tmp_path / PROCESS_VARIANT_JSON).write_text(
        json.dumps(_process_variant()), encoding="utf-8"
    )

    result = materialize_variant_feature_challenge(tmp_path)

    assert result["artifact_materialized"] is True
    assert result["projection_creates_new_evidence"] is False
    assert result["difference_rows_are_independent_evidence_votes"] is False
    assert result["professional_finding_emit_allowed"] is False
    target = tmp_path / OUTPUT_JSON
    assert target.is_file()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["variant_feature_challenge_record_count"] == 1
    assert payload["professional_finding_emit_allowed"] is False
    assert payload["feature_absence_is_counterevidence"] is False


def test_missing_current_inputs_removes_stale_challenge_artifact(tmp_path: Path) -> None:
    stale = tmp_path / OUTPUT_JSON
    stale.write_text("{}", encoding="utf-8")

    result = materialize_variant_feature_challenge(tmp_path)

    assert result["status"] == "NOT_APPLICABLE_PREREQUISITE_MISSING"
    assert result["artifact_materialized"] is False
    assert not stale.exists()
