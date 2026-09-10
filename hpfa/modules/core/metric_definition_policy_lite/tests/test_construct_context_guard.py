from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import (
    assess_construct_comparison,
    load_guard,
)

ROOT = Path(__file__).resolve().parents[5]
GUARD = load_guard(ROOT / "configs/metrics/construct_context_guard_v1.json")


def _record(**overrides):
    record = {
        "denominator_set_id": "eligible_progression_anchors_v1",
        "observation_window": "FULL_MATCH",
        "entity_scope": "TEAM",
        "team_scope": "TEAM_LOCAL",
        "period_scope": "ALL_PERIODS",
        "context_policy_id": "match_context_v1",
        "source_surface_roles": ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
        "required_event_families": ["PASS", "CARRY", "PROGRESSION"],
        "construct_target": "PROGRESSION_EFFECTIVENESS",
        "dependency_group": "provider_match_population_a",
        "provenance_root": "provider_match_population_a",
    }
    record.update(overrides)
    return record


def test_aligned_construct_context_is_comparable_candidate():
    result = assess_construct_comparison(_record(), _record(), GUARD)
    assert result["status"] == "CONSTRUCT_COMPARABLE_CANDIDATE"
    assert result["comparison_admitted"] is True
    assert result["construct_validity_truth"] is False
    assert result["event_only_is_product_ceiling"] is False


def test_denominator_mismatch_blocks_comparison():
    result = assess_construct_comparison(
        _record(), _record(denominator_set_id="all_visible_actions_v1"), GUARD
    )
    assert result["status"] == "COMPARISON_BLOCKED"
    assert result["comparison_admitted"] is False
    assert "comparison_blocked:denominator_set_id" in result["hard_block_hits"]


def test_missing_required_dimension_blocks_comparison():
    result = assess_construct_comparison(_record(), _record(observation_window=""), GUARD)
    assert result["status"] == "COMPARISON_BLOCKED"
    assert "missing_required_dimension:observation_window" in result["hard_block_hits"]


def test_period_or_source_surface_drift_requires_review():
    result = assess_construct_comparison(
        _record(),
        _record(period_scope="SECOND_HALF", source_surface_roles=["PLAYER_SURFACE_CANDIDATE"]),
        GUARD,
    )
    assert result["status"] == "CONSTRUCT_CONTEXT_WARNING"
    assert result["comparison_admitted"] is False
    assert "construct_context_warning:period_scope" in result["review_hits"]
    assert "construct_context_warning:source_surface_roles" in result["review_hits"]


def test_shared_provider_dependency_never_becomes_independent_support_vote():
    result = assess_construct_comparison(_record(), _record(), GUARD)
    assert result["shared_dependency_group"] is True
    assert result["dependent_support_only"] is True
    assert result["same_provider_reflection_adds_independent_vote"] is False
    assert result["independent_support_vote_count"] == 0


def test_different_dependency_group_does_not_claim_independence_truth():
    result = assess_construct_comparison(
        _record(), _record(dependency_group="provider_match_population_b", provenance_root="provider_match_population_b"), GUARD
    )
    assert result["dimension_states"]["dependency_group"] == "DEPENDENCY_DIFFERENT"
    assert result["dependent_support_only"] is False
    assert result["independent_support_vote_count"] is None
    assert result["same_provider_reflection_adds_independent_vote"] is False


def test_claim_locks_remain_closed():
    result = assess_construct_comparison(_record(), _record(), GUARD)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["causal_truth"] is False
    assert result["tactical_truth"] is False
    assert result["missing_context_is_counterevidence"] is False


def test_no_sample_match_identity_leak():
    source = (ROOT / "hpfa/modules/core/metric_definition_policy_lite/src/construct_context_guard.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Galatasaray", "Roma", "Atalanta"):
        assert token not in source
