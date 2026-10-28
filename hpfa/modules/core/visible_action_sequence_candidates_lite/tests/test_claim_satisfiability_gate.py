from hpfa.modules.core.visible_action_sequence_candidates_lite.src.claim_satisfiability_gate import (
    REVIEW,
    SATISFIED,
    UNSATISFIED,
    UNSATISFIABLE,
    assess_claim_satisfiability,
)


def test_match_local_visible_variation_satisfied_without_emit_authority():
    result = assess_claim_satisfiability(
        "MATCH_LOCAL_VISIBLE_VARIATION",
        admitted_capabilities=["ACTION", "TEMPORAL", "OUTCOME", "PROVENANCE"],
    )
    assert result["state"] == SATISFIED
    assert result["missing_required_capabilities"] == []
    assert result["gate_can_authorize_emit"] is False
    assert result["gate_can_strengthen_claim_ceiling"] is False
    assert result["production_release"] is False


def test_missing_required_capability_cannot_be_compensated_by_support_volume():
    result = assess_claim_satisfiability(
        "MATCH_LOCAL_VISIBLE_VARIATION",
        admitted_capabilities=["ACTION", "TEMPORAL", "PROVENANCE"],
        admitted_independent_support_count=999,
        dependency_independence_proven=True,
        statistical_independence_proven=True,
        episode_spread_observed=True,
    )
    assert result["state"] == UNSATISFIED
    assert result["missing_required_capabilities"] == ["OUTCOME"]
    assert "REQUIRED_OBSERVATION_CAPABILITY_MISSING" in result[
        "noncompensating_requirement_failures"
    ]


def test_causality_is_unsatisfiable_under_current_single_match_product_ceiling():
    result = assess_claim_satisfiability(
        "CAUSALITY",
        admitted_capabilities=[
            "ACTION",
            "ACTOR",
            "TEMPORAL",
            "SPATIAL",
            "OUTCOME",
            "RELATIONAL",
            "PROCESS",
            "STATE_TRANSITION",
            "TRACKING_VIDEO_PHYSICAL",
            "PROVENANCE",
        ],
        admitted_independent_support_count=100,
        dependency_independence_proven=True,
        statistical_independence_proven=True,
        episode_spread_observed=True,
    )
    assert result["state"] == UNSATISFIABLE
    assert result["claim_ceiling"] == "NO_CAUSAL_CLAIM_OUTPUT"
    assert result["recurrence_is_causality"] is False


def test_tracking_geometry_requires_tracking_video_capability():
    result = assess_claim_satisfiability(
        "TRACKING_GEOMETRY_DESCRIPTION",
        admitted_capabilities=["ACTION", "SPATIAL", "PROVENANCE"],
    )
    assert result["state"] == UNSATISFIED
    assert result["missing_required_capabilities"] == ["TRACKING_VIDEO_PHYSICAL"]


def test_recurrence_candidate_requires_noncompensating_independence_and_episode_spread():
    weak = assess_claim_satisfiability(
        "MATCH_LOCAL_RECURRENCE_CANDIDATE",
        admitted_capabilities=["ACTION", "TEMPORAL", "PROVENANCE"],
        admitted_independent_support_count=12,
        dependency_independence_proven=False,
        statistical_independence_proven=False,
        episode_spread_observed=False,
    )
    assert weak["state"] == UNSATISFIED
    assert "DEPENDENCY_INDEPENDENCE_NOT_PROVEN" in weak[
        "noncompensating_requirement_failures"
    ]
    assert "STATISTICAL_INDEPENDENCE_NOT_PROVEN" in weak[
        "noncompensating_requirement_failures"
    ]
    assert "EPISODE_SPREAD_NOT_OBSERVED" in weak[
        "noncompensating_requirement_failures"
    ]

    bounded = assess_claim_satisfiability(
        "MATCH_LOCAL_RECURRENCE_CANDIDATE",
        admitted_capabilities=["ACTION", "TEMPORAL", "PROVENANCE"],
        admitted_independent_support_count=2,
        dependency_independence_proven=True,
        statistical_independence_proven=True,
        episode_spread_observed=True,
    )
    assert bounded["state"] == SATISFIED
    assert bounded["claim_ceiling"] == "MATCH_LOCAL_RECURRENCE_CANDIDATE_ONLY"
    assert bounded["gate_can_authorize_emit"] is False


def test_unknown_claim_family_requires_review_and_never_opens_output():
    result = assess_claim_satisfiability(
        "SOME_NEW_UNREVIEWED_FAMILY",
        admitted_capabilities=["ACTION", "TEMPORAL", "PROVENANCE"],
    )
    assert result["state"] == REVIEW
    assert result["claim_ceiling"] == "NO_CLAIM_OUTPUT_PENDING_REVIEW"
    assert result["gate_can_authorize_emit"] is False


def test_provider_semantic_progression_does_not_become_tactical_truth():
    result = assess_claim_satisfiability(
        "PROGRESSION_ACCESS_DESCRIPTION",
        admitted_capabilities=["ACTION", "TEMPORAL", "PROVIDER_DERIVED", "PROVENANCE"],
    )
    assert result["state"] == SATISFIED
    assert result["provider_label_is_tactical_truth"] is False
    assert result["same_timestamp_is_total_order"] is False
    assert result["claim_ceiling"] == "MATCH_LOCAL_PROVIDER_SEMANTIC_PROGRESSION_ACCESS_ONLY"
