from __future__ import annotations

import copy

from hpfa.modules.core.visible_action_sequence_candidates_lite.src import (
    grammar_stable_variant_feature_delta_projection as target,
)


def _base_payload(context_rows: list[dict]) -> dict:
    return {
        "status": "PASS",
        "review_hits": [],
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "gsvfd_identity_must_not_change",
                "source_process_variant_family_ref": "family_1",
                "context_feature_difference_candidates": context_rows,
                "context_feature_difference_candidate_count": len(context_rows),
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _call_public_builder(monkeypatch, payload: dict) -> dict:
    monkeypatch.setattr(
        target,
        "_BASE_BUILD_GRAMMAR_STABLE_VARIANT_FEATURE_DELTA",
        lambda *_args, **_kwargs: copy.deepcopy(payload),
    )
    return target.build_grammar_stable_variant_feature_delta({}, {}, {}, {})


def test_base_context_provenance_binds_provider_semantics_and_actor_identity_without_mutating_feature_rows(
    monkeypatch,
) -> None:
    context_rows = [
        {
            "feature_token": "LAYER[1]::provider_direction_candidates:FORWARD",
            "feature_scope": "PARTIAL_ORDER_LAYER",
            "success_visible_numerator": 4,
            "success_eligible_denominator": 5,
            "failure_visible_numerator": 1,
            "failure_eligible_denominator": 2,
            "descriptive_rate_delta_success_minus_failure": 0.3,
        },
        {
            "feature_token": "actor_identity_candidate_ids:actor_1",
            "feature_scope": "VARIANT_AGGREGATE",
            "success_visible_numerator": 1,
            "success_eligible_denominator": 5,
            "failure_visible_numerator": 0,
            "failure_eligible_denominator": 2,
            "descriptive_rate_delta_success_minus_failure": 0.2,
        },
        {
            "feature_token": "LAYER[0]::process_family_candidate:POSITIONAL_ATTACK_CANDIDATE",
            "feature_surface_detail": "PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT",
            "feature_scope": "PARTIAL_ORDER_LAYER",
            "success_visible_numerator": 5,
            "success_eligible_denominator": 5,
            "failure_visible_numerator": 1,
            "failure_eligible_denominator": 2,
            "descriptive_rate_delta_success_minus_failure": 0.5,
        },
    ]
    original_rows = copy.deepcopy(context_rows)
    result = _call_public_builder(monkeypatch, _base_payload(context_rows))

    family = result["grammar_stable_variant_feature_delta_records"][0]
    assert family["grammar_stable_variant_feature_delta_id"] == "gsvfd_identity_must_not_change"
    assert family["context_feature_difference_candidates"] == original_rows
    assert family["context_feature_difference_candidate_count"] == 3

    provenance = {
        row["feature_token"]: row
        for row in family["base_context_feature_provenance_records"]
    }
    assert set(provenance) == {
        "LAYER[1]::provider_direction_candidates:FORWARD",
        "actor_identity_candidate_ids:actor_1",
    }

    provider = provenance["LAYER[1]::provider_direction_candidates:FORWARD"]
    assert provider["feature_source_surface"] == "occurrence_state_transition_projection_v1"
    assert provider["feature_dependency_surface"] == "spatial_transition_candidate_lite_v1"
    assert provider["feature_source_field"] == "provider_direction_candidates"
    assert provider["feature_information_role"] == "PROVIDER_SEMANTIC_CONTEXT_CANDIDATE_ONLY"

    actor = provenance["actor_identity_candidate_ids:actor_1"]
    assert actor["feature_dependency_surface"] == "occurrence_consequence_projection_v1"
    assert actor["feature_information_role"] == "ACTOR_IDENTITY_CONTEXT_CANDIDATE_ONLY"

    for row in provenance.values():
        assert row["eligible_denominator_basis"] == "VARIANTS_WITH_COMPLETE_OCCURRENCE_STATE_CONTEXT_COVERAGE"
        assert row["feature_is_physical_geometry_truth"] is False
        assert row["feature_is_tracking_truth"] is False
        assert row["feature_is_tactical_truth"] is False
        assert row["feature_is_causal_truth"] is False
        assert row["dependency_independence_proven"] is False
        assert row["statistical_independence_proven"] is False
        assert row["claim_ceiling"] == target.CLAIM_CEILING

    assert family["base_context_feature_provenance_record_count"] == 2
    assert family["base_context_feature_provenance_complete"] is True
    assert family["base_context_feature_provenance_is_independent_evidence_vote"] is False
    assert family["base_context_feature_provenance_changes_feature_difference"] is False
    assert result["base_context_feature_provenance_contract_applied"] is True
    assert result["base_context_feature_provenance_record_count"] == 2
    assert result["base_context_feature_provenance_unresolved_count"] == 0
    assert result["base_context_feature_provenance_is_independent_evidence_vote"] is False
    assert result["base_context_feature_provenance_changes_feature_difference"] is False
    assert result["status"] == "PASS"


def test_unknown_base_context_source_role_fails_closed_to_review_without_promoting_truth(monkeypatch) -> None:
    payload = _base_payload(
        [
            {
                "feature_token": "future_context_dimension:SOMETHING_NEW",
                "feature_scope": "VARIANT_AGGREGATE",
                "success_visible_numerator": 1,
                "success_eligible_denominator": 2,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 2,
                "descriptive_rate_delta_success_minus_failure": 0.5,
            }
        ]
    )
    result = _call_public_builder(monkeypatch, payload)
    family = result["grammar_stable_variant_feature_delta_records"][0]
    provenance = family["base_context_feature_provenance_records"][0]

    assert provenance["feature_information_role"] == "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED"
    assert provenance["feature_dependency_surface"] == "UNRESOLVED_DEPENDENCY_SURFACE"
    assert provenance["feature_is_physical_geometry_truth"] is False
    assert provenance["feature_is_tracking_truth"] is False
    assert provenance["feature_is_tactical_truth"] is False
    assert provenance["feature_is_causal_truth"] is False
    assert family["base_context_feature_provenance_complete"] is False
    assert result["base_context_feature_provenance_unresolved_count"] == 1
    assert "base_context_feature_provenance_unresolved:family_1" in result["review_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_fail_closed_feature_delta_never_opens_provenance_admission(monkeypatch) -> None:
    payload = _base_payload([])
    payload["status"] = "FAIL_CLOSED"
    result = _call_public_builder(monkeypatch, payload)

    assert result["status"] == "FAIL_CLOSED"
    assert result["base_context_feature_provenance_contract_applied"] is False
    assert result["base_context_feature_provenance_record_count"] == 0
    assert result["base_context_feature_provenance_unresolved_count"] == 0
    assert result["base_context_feature_provenance_is_independent_evidence_vote"] is False
    assert result["base_context_feature_provenance_changes_feature_difference"] is False
