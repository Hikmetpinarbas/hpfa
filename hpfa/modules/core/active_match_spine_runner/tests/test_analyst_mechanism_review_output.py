import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analyst_mechanism_review import build_mechanism_review_lines
from user_output_bundle import build_analyst_report


def _full_spine(tmp_path: Path, *, declared: bool = True) -> dict:
    artifacts = []
    if declared:
        artifacts = [
            str(tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"),
            str(tmp_path / "match_local_identity_candidates_lite_v1.json"),
            str(tmp_path / "occurrence_consequence_projection_v1.json"),
            str(tmp_path / "visible_action_sequence_candidates_lite_v1.json"),
            str(tmp_path / "observable_process_variant_binding_projection_v1.json"),
        ]
    return {
        "status": "REVIEW_REQUIRED",
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED",
        "current_invocation_artifacts": artifacts,
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": False,
            "current_c4_producers_reused": True,
        },
        "intelligence_chains": [],
        "hard_block_hits": [],
        "review_hits": [],
    }


def _write_payloads(tmp_path: Path) -> None:
    delta = {
        "status": "REVIEW_REQUIRED",
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "gsvfd_1",
                "source_process_variant_family_ref": "family_1",
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["1"],
                "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "resolved_variant_count": 10,
                "success_resolved_variant_count": 7,
                "failure_resolved_variant_count": 3,
                "first_supported_context_difference_layer_candidate": 0,
                "first_supported_consequence_difference_layer_candidate": 1,
                "context_coverage_incomplete_variant_count": 2,
                "right_censored_variant_count": 0,
                "dependency_independence_proven": False,
                "context_feature_difference_candidates": [
                    {
                        "feature_token": "LAYER[1]::actor_identity_candidate_ids:actor_1",
                        "success_visible_numerator": 0,
                        "success_eligible_denominator": 7,
                        "failure_visible_numerator": 2,
                        "failure_eligible_denominator": 3,
                        "descriptive_rate_delta_success_minus_failure": -0.666667,
                    },
                    {
                        "feature_token": "LAYER[1]::provider_direction_candidates:FORWARD",
                        "success_visible_numerator": 6,
                        "success_eligible_denominator": 7,
                        "failure_visible_numerator": 0,
                        "failure_eligible_denominator": 3,
                        "descriptive_rate_delta_success_minus_failure": 0.857143,
                    },
                    {
                        "feature_token": "LAYER[1]::process_family_candidate:POSITIONAL_ATTACK_CANDIDATE",
                        "feature_surface_detail": "PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT",
                        "feature_scope": "PARTIAL_ORDER_LAYER",
                        "partial_order_layer_index": 1,
                        "eligible_denominator_basis": "VARIANTS_WITH_MATCHED_PROVIDER_REVIEWED_PROCESS_ANNOTATION",
                        "success_visible_numerator": 5,
                        "success_eligible_denominator": 7,
                        "failure_visible_numerator": 1,
                        "failure_eligible_denominator": 3,
                        "descriptive_rate_delta_success_minus_failure": 0.380952,
                        "dependency_independence_proven": False,
                        "statistical_independence_proven": False,
                        "claim_ceiling": "MATCH_LOCAL_PROVIDER_PROCESS_CONTEXT_DIFFERENCE_CANDIDATE_ONLY",
                    },
                ],
                "consequence_feature_difference_candidates": [
                    {
                        "feature_token": "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE",
                        "success_visible_numerator": 6,
                        "success_eligible_denominator": 7,
                        "failure_visible_numerator": 1,
                        "failure_eligible_denominator": 3,
                    },
                    {
                        "feature_token": "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE",
                        "success_visible_numerator": 0,
                        "success_eligible_denominator": 7,
                        "failure_visible_numerator": 2,
                        "failure_eligible_denominator": 3,
                    },
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    identity = {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "team_1",
                "team_normalized_key": "team_alpha",
            }
        ],
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_1",
                "actor_normalized_key": "player_alpha",
            },
            {
                "actor_identity_candidate_id": "actor_2",
                "actor_normalized_key": "player_beta",
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    occurrence = {
        "status": "REVIEW_REQUIRED",
        "occurrence_consequence_projection_count": 12,
        "occurrence_with_visible_consequence_support_count": 9,
        "complete_to_declared_horizon_no_admitted_followup_count": 2,
        "right_censored_occurrence_count": 1,
        "right_censoring_unresolved_occurrence_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    sequence = {
        "status": "REVIEW_REQUIRED",
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "variant_failure",
                "sequence_ref": "sequence_failure",
            },
            {
                "partial_order_occurrence_variant_id": "variant_success",
                "sequence_ref": "sequence_success",
            },
        ],
        "first_supported_branch_divergence_candidates": [
            {
                "team_identity_candidate_id": "team_1",
                "period_candidate": 1,
                "shared_anchor_time_candidate": 120.0,
                "branch_profiles": [
                    {
                        "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 122.0,
                        "supporting_visible_sequence_candidate_ids": ["sequence_failure"],
                        "semantic_profiles": [
                            {
                                "actor_identity_candidate_id": "actor_1",
                                "primary_family_candidate": "PASS",
                            }
                        ],
                    },
                    {
                        "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "neighbor_time_candidate": 124.0,
                        "supporting_visible_sequence_candidate_ids": ["sequence_success"],
                        "semantic_profiles": [
                            {
                                "actor_identity_candidate_id": "actor_2",
                                "primary_family_candidate": "PASS",
                            }
                        ],
                    },
                ],
            }
        ],
    }
    process_variants = {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_variant_refs": ["variant_failure", "variant_success"],
            }
        ],
    }
    (tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json").write_text(
        json.dumps(delta), encoding="utf-8"
    )
    (tmp_path / "match_local_identity_candidates_lite_v1.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )
    (tmp_path / "occurrence_consequence_projection_v1.json").write_text(
        json.dumps(occurrence), encoding="utf-8"
    )
    (tmp_path / "visible_action_sequence_candidates_lite_v1.json").write_text(
        json.dumps(sequence), encoding="utf-8"
    )
    (tmp_path / "observable_process_variant_binding_projection_v1.json").write_text(
        json.dumps(process_variants), encoding="utf-8"
    )


def test_current_mechanism_surface_separates_context_locator_and_outcome_adjacent_cues(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    lines = build_mechanism_review_lines(tmp_path, _full_spine(tmp_path))
    text = "\n".join(lines)
    assert "Team Alpha" in text
    assert "grammar=PASS -> PASS" in text
    assert "resolved=10 (SUCCESS=7, FAILURE=3)" in text
    assert "primary_occurrence_spine: occurrence_candidates=12" in text
    assert "visible_consequence_support=9" in text
    assert "fully_observed_no_followup=2" in text
    assert "right_censored=1 unresolved_censoring=0" in text
    assert "outcome_adjacent_consequence_contrast:" in text
    assert "same_team_continuation success=6/7 failure=1/3" in text
    assert "opponent_handover success=0/7 failure=2/3" in text
    assert (
        "mechanism_context_review_focus: process_context_candidate=Positional Attack Candidate "
        "success=5/7 failure=1/3" in text
    )
    assert "mechanism_context_source: source_role=PROVIDER_REVIEWED_ANNOTATION" in text
    assert "surface=PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT" in text
    assert "scope=PARTIAL_ORDER_LAYER" in text
    assert "denominator_basis=VARIANTS_WITH_MATCHED_PROVIDER_REVIEWED_PROCESS_ANNOTATION" in text
    assert "claim_ceiling=MATCH_LOCAL_PROVIDER_PROCESS_CONTEXT_DIFFERENCE_CANDIDATE_ONLY" in text
    assert "dependency_independence_proven=false" in text
    assert "statistical_independence_proven=false" in text
    assert "actor_locator_only: actor=Player Alpha success=0/7 failure=2/3" in text
    assert "role=VIDEO_REVIEW_LOCATOR_ONLY" in text
    assert "provider_direction_candidates" not in text
    assert "context_missing=2/10" in text
    assert "actor identity yalniz locator" in text
    assert "source_provenance_guard=" in text
    assert "locator_semantics=FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR_NOT_PROVEN_FIRST_DIVERGENCE" in text
    assert "video_review_locator: shared_anchor=02:00 -> 02:02 Player Alpha FAILURE PASS; 02:04 Player Beta SUCCESS PASS" in text
    assert "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY" in text
    assert "professional_emit_allowed=false" in text


def test_actor_only_difference_does_not_become_mechanism_context_focus(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    payload_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    rows = payload["grammar_stable_variant_feature_delta_records"][0]["context_feature_difference_candidates"]
    payload["grammar_stable_variant_feature_delta_records"][0]["context_feature_difference_candidates"] = [
        row for row in rows if "process_family_candidate:" not in row["feature_token"]
    ]
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    text = "\n".join(build_mechanism_review_lines(tmp_path, _full_spine(tmp_path)))
    assert "mechanism_context_review_focus: NO_NON_ACTOR_CONTEXT_DIAGNOSTIC_EXPOSED" in text
    assert "mechanism_context_source: source_role=NO_CURRENT_CONTEXT_SOURCE_EXPOSED" in text
    assert "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED" not in text
    assert "actor_locator_only: actor=Player Alpha" in text
    assert "video_review_locator: shared_anchor=02:00" in text


def test_unknown_context_provenance_fails_closed(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    payload_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    rows = payload["grammar_stable_variant_feature_delta_records"][0]["context_feature_difference_candidates"]
    process_row = next(row for row in rows if "process_family_candidate:" in row["feature_token"])
    process_row["feature_surface_detail"] = "UNDECLARED_SURFACE"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    text = "\n".join(build_mechanism_review_lines(tmp_path, _full_spine(tmp_path)))
    assert "mechanism_context_review_focus: process_context_candidate=Positional Attack Candidate" in text
    assert "mechanism_context_source: source_role=SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED" in text
    assert "surface=UNDECLARED_SURFACE" in text
    assert "source_role=DIRECT" not in text
    assert "source_role=TRACKING" not in text


def test_stale_mechanism_artifact_is_not_consumed(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    lines = build_mechanism_review_lines(tmp_path, _full_spine(tmp_path, declared=False))
    text = "\n".join(lines)
    assert "eski artifact kullanilmadi" in text
    assert "Team Alpha" not in text
    assert "occurrence_candidates=12" not in text
    assert "video_review_locator" not in text


def test_standard_report_contains_role_separated_review_without_promoting_emit(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    spine = _full_spine(tmp_path)
    spine["engineering_evidence"]["current_context_episode_feature_lane_completed"] = True
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True
    spine["rich_multiformat_analysis_lattice"] = {"status": "REVIEW_REQUIRED"}
    text = build_analyst_report(tmp_path, spine)
    assert "ANALYST REVIEW — GORUNUR SUREC MEKANIZMASI ADAYLARI" in text
    assert "primary_occurrence_spine: occurrence_candidates=12" in text
    assert "mechanism_context_review_focus: process_context_candidate=Positional Attack Candidate" in text
    assert "mechanism_context_source: source_role=PROVIDER_REVIEWED_ANNOTATION" in text
    assert "surface=PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT" in text
    assert "denominator_basis=VARIANTS_WITH_MATCHED_PROVIDER_REVIEWED_PROCESS_ANNOTATION" in text
    assert "claim_ceiling=MATCH_LOCAL_PROVIDER_PROCESS_CONTEXT_DIFFERENCE_CANDIDATE_ONLY" in text
    assert "actor_locator_only: actor=Player Alpha" in text
    assert "video_review_locator: shared_anchor=02:00" in text
    assert "professional_emit_allowed=false" in text
    assert "ZFGV observation ailesindeki occurrence/episode aday yuzeylerini" in text
    assert "event-only" not in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_bound_aware_story_review_is_runtime_visible_without_probability_promotion(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    delta_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    delta["grammar_stable_variant_feature_delta_records"][0]["right_censored_variant_count"] = 2
    delta_path.write_text(json.dumps(delta), encoding="utf-8")

    analyst_output = {
        "status": "REVIEW_REQUIRED",
        "analyst_output_contracts": [
            {
                "analyst_output_contract_id": "aoc_sfh_1",
                "rate_bound_binding_state": "SOURCE_BOUND_NUMERIC",
                "rate_bound_state": "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE",
                "rate_bound_estimand_id": "MATCH_LOCAL_VISIBLE_PROCESS_OUTCOME_RATE",
                "rate_bound_denominator_basis": "UNIQUE_OBSERVABLE_PROCESS_VARIANT_FAMILY_MEMBER_SEQUENCE_REFS",
                "rate_bound_resolved_success_n": 4,
                "rate_bound_resolved_failure_n": 1,
                "rate_bound_unresolved_eligible_n": 2,
                "rate_bound_eligible_total_n": 7,
                "rate_bound_lower": 4 / 7,
                "rate_bound_upper": 6 / 7,
                "rate_bound_width": 2 / 7,
                "rate_bound_assumption_set_id": "BINARY_VISIBLE_OUTCOME_KNOWN_ELIGIBLE_DENOMINATOR_WORST_CASE_UNRESOLVED_V1",
                "rate_bound_matched_process_variant_family_refs": ["family_1"],
                "rate_bound_can_authorize_emit": False,
                "rate_bound_can_strengthen_claim_ceiling": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    claim_path = tmp_path / "analyst_output_claim_contract_projection_v1.json"
    claim_path.write_text(json.dumps(analyst_output), encoding="utf-8")

    spine = _full_spine(tmp_path)
    spine["variant_feature_challenge_runtime_binding"] = {
        "post_sequence_admission_finalized": True,
        "post_sequence_current_invocation_artifacts": [str(claim_path)],
    }
    text = "\n".join(build_mechanism_review_lines(tmp_path, spine))

    assert "story_shortlist_status=PASS" in text
    assert "story_shortlist_count=1" in text
    assert "story_bounded_review_only_count=1" in text
    assert "family=family_1 eligibility=BOUND_AWARE_REVIEW_ONLY" in text
    assert "visible_outcome_rate_bound=0.571429-0.857143" in text
    assert "confidence_interval=false probability=false emit=false" in text
    assert "story_selection_is_truth_ranking=false" in text
    assert "story_selection_is_confidence_score=false" in text
    assert "story_selection_can_authorize_emit=false" in text
    assert "story_detail_render_count=1 source_candidate_count=1" in text
    assert "story_detail_render_scope=SHORTLIST_ONLY_ATTENTION_COMPRESSION_NOT_EVIDENCE_REMOVAL" in text


def test_same_grammar_contexts_are_compared_without_tactical_promotion(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    delta_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    first = delta["grammar_stable_variant_feature_delta_records"][0]
    first["visible_episode_spread_count"] = 3
    first["occurrence_disjoint_support_cluster_count"] = 4
    first["success_failure_supported_branch_divergence_count"] = 1
    second = json.loads(json.dumps(first))
    second["grammar_stable_variant_feature_delta_id"] = "gsvfd_2"
    second["source_process_variant_family_ref"] = "family_2"
    second["team_identity_candidate_ids"] = ["team_2"]
    second["period_candidates"] = ["2"]
    second["resolved_variant_count"] = 8
    second["success_resolved_variant_count"] = 6
    second["failure_resolved_variant_count"] = 2
    second["visible_episode_spread_count"] = 2
    second["occurrence_disjoint_support_cluster_count"] = 2
    second["success_failure_supported_branch_divergence_count"] = 2
    delta["grammar_stable_variant_feature_delta_records"].append(second)
    delta_path.write_text(json.dumps(delta), encoding="utf-8")

    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity["team_identity_candidates"].append(
        {"team_identity_candidate_id": "team_2", "team_normalized_key": "team_beta"}
    )
    identity_path.write_text(json.dumps(identity), encoding="utf-8")

    text = "\n".join(build_mechanism_review_lines(tmp_path, _full_spine(tmp_path)))
    assert "same_grammar_context_comparison: grammar=PASS -> PASS shortlisted_contexts=2" in text
    assert "scope=SHORTLIST_ONLY_ATTENTION_COMPRESSION_NOT_ALL_MATCH_CONTEXTS" in text
    assert "semantics=MATCH_LOCAL_VISIBLE_CONTEXT_COMPARISON_ONLY" in text
    assert "tactical_change=false team_quality=false causality=false significance=false" in text
    assert "same_grammar_context: team=Team Alpha period=1 resolved=10 success_visible=7 failure_visible=3" in text
    assert "same_grammar_context: team=Team Beta period=2 resolved=8 success_visible=6 failure_visible=2" in text
    assert "independent_support=false recurrence_truth=false" in text
