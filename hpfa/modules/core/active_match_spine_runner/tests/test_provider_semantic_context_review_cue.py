from __future__ import annotations

import json

from hpfa.modules.core.active_match_spine_runner.src.analyst_mechanism_review import (
    build_mechanism_review_lines,
)


def _full_spine(tmp_path) -> dict:
    return {
        "current_invocation_artifacts": [
            str(tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"),
        ]
    }


def _write_payload(tmp_path, record: dict) -> None:
    payload = {
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [record],
    }
    (tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_provider_semantic_context_is_separate_review_cue_not_mechanism_truth(tmp_path) -> None:
    provider = {
        "feature_token": "LAYER[0]::provider_direction_candidates:FORWARD",
        "success_visible_numerator": 4,
        "success_eligible_denominator": 5,
        "failure_visible_numerator": 2,
        "failure_eligible_denominator": 2,
        "descriptive_rate_delta_success_minus_failure": -0.2,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
    }
    process = {
        "feature_token": "LAYER[0]::process_family_candidate:POSITIONAL_ATTACK_CANDIDATE",
        "feature_surface_detail": "PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT",
        "feature_scope": "PARTIAL_ORDER_LAYER",
        "eligible_denominator_basis": "VARIANTS_WITH_MATCHED_PROVIDER_REVIEWED_PROCESS_ANNOTATION",
        "claim_ceiling": "MATCH_LOCAL_PROVIDER_PROCESS_CONTEXT_DIFFERENCE_CANDIDATE_ONLY",
        "success_visible_numerator": 4,
        "success_eligible_denominator": 5,
        "failure_visible_numerator": 1,
        "failure_eligible_denominator": 2,
        "descriptive_rate_delta_success_minus_failure": 0.3,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
    }
    actor = {
        "feature_token": "actor_identity_candidate_ids:actor_1",
        "success_visible_numerator": 1,
        "success_eligible_denominator": 5,
        "failure_visible_numerator": 0,
        "failure_eligible_denominator": 2,
        "descriptive_rate_delta_success_minus_failure": 0.2,
    }
    record = {
        "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
        "team_identity_candidate_ids": ["team_1"],
        "period_candidates": ["1"],
        "resolved_variant_count": 7,
        "success_resolved_variant_count": 5,
        "failure_resolved_variant_count": 2,
        "context_coverage_incomplete_variant_count": 0,
        "right_censored_variant_count": 0,
        "context_feature_difference_candidates": [provider, process, actor],
        "consequence_feature_difference_candidates": [],
        "base_context_feature_provenance_records": [
            {
                "feature_token": provider["feature_token"],
                "feature_source_surface": "occurrence_state_transition_projection_v1",
                "feature_dependency_surface": "spatial_transition_candidate_lite_v1",
                "feature_source_field": "provider_direction_candidates",
                "feature_information_role": "PROVIDER_SEMANTIC_CONTEXT_CANDIDATE_ONLY",
                "eligible_denominator_basis": "VARIANTS_WITH_COMPLETE_OCCURRENCE_STATE_CONTEXT_COVERAGE",
                "feature_is_physical_geometry_truth": False,
                "feature_is_tracking_truth": False,
                "feature_is_tactical_truth": False,
                "feature_is_causal_truth": False,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
                "claim_ceiling": "MATCH_LOCAL_DEPENDENCY_QUALIFIED_VARIANT_FEATURE_DIFFERENCE_CANDIDATE_ONLY",
            },
            {
                "feature_token": actor["feature_token"],
                "feature_information_role": "ACTOR_IDENTITY_CONTEXT_CANDIDATE_ONLY",
            },
        ],
        "dependency_independence_proven": False,
    }
    _write_payload(tmp_path, record)
    rendered = "\n".join(build_mechanism_review_lines(tmp_path, _full_spine(tmp_path)))

    assert "mechanism_context_review_focus: process_context_candidate=Positional Attack Candidate" in rendered
    assert "provider_semantic_context_review_cue: LAYER[0]::provider_direction=FORWARD success=4/5 failure=2/2 descriptive_rate_delta=-0.200" in rendered
    assert "role=PROVIDER_SEMANTIC_REVIEW_CUE_ONLY" in rendered
    assert "selection=MAX_ABS_DESCRIPTIVE_RATE_DELTA_NOT_STRENGTH_OR_SIGNIFICANCE" in rendered
    assert "provider_semantic_context_source: source_role=PROVIDER_SEMANTIC_CONTEXT_CANDIDATE_ONLY" in rendered
    assert "source_surface=occurrence_state_transition_projection_v1" in rendered
    assert "dependency_surface=spatial_transition_candidate_lite_v1" in rendered
    assert "provider_semantic_context_guard: physical_geometry_truth=false tracking_truth=false tactical_truth=false causal_truth=false success_probability_truth=false independent_evidence_vote=false" in rendered
    assert "professional_emit_allowed=false" in rendered


def test_provider_label_without_admitted_provenance_does_not_open_review_cue(tmp_path) -> None:
    provider = {
        "feature_token": "provider_zone_candidates:PENALTY_AREA",
        "success_visible_numerator": 1,
        "success_eligible_denominator": 2,
        "failure_visible_numerator": 0,
        "failure_eligible_denominator": 1,
        "descriptive_rate_delta_success_minus_failure": 0.5,
    }
    record = {
        "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
        "team_identity_candidate_ids": ["team_1"],
        "period_candidates": ["1"],
        "resolved_variant_count": 3,
        "success_resolved_variant_count": 2,
        "failure_resolved_variant_count": 1,
        "context_coverage_incomplete_variant_count": 0,
        "right_censored_variant_count": 0,
        "context_feature_difference_candidates": [provider],
        "consequence_feature_difference_candidates": [],
        "base_context_feature_provenance_records": [
            {
                "feature_token": provider["feature_token"],
                "feature_information_role": "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED",
            }
        ],
        "dependency_independence_proven": False,
    }
    _write_payload(tmp_path, record)
    rendered = "\n".join(build_mechanism_review_lines(tmp_path, _full_spine(tmp_path)))

    assert "mechanism_context_review_focus: NO_NON_ACTOR_CONTEXT_DIAGNOSTIC_EXPOSED" in rendered
    assert "provider_semantic_context_review_cue: NO_PROVIDER_SEMANTIC_CONTEXT_CUE_EXPOSED" in rendered
    assert "provider_semantic_context_source: source_role=NO_PROVIDER_SEMANTIC_CONTEXT_SOURCE_EXPOSED" in rendered
    assert "provider_semantic_context_guard: NOT_APPLICABLE_NO_PROVIDER_SEMANTIC_CONTEXT_CUE" in rendered
    assert "professional_emit_allowed=false" in rendered
