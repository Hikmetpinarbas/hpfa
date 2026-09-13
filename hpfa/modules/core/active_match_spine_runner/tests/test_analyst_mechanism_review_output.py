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
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["1"],
                "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "resolved_variant_count": 10,
                "success_resolved_variant_count": 7,
                "failure_resolved_variant_count": 3,
                "first_supported_context_difference_layer_candidate": 0,
                "first_supported_consequence_difference_layer_candidate": 1,
                "process_context_coverage_incomplete_variant_count": 2,
                "right_censored_variant_count": 0,
                "dependency_independence_proven": False,
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
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    (tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json").write_text(
        json.dumps(delta), encoding="utf-8"
    )
    (tmp_path / "match_local_identity_candidates_lite_v1.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )


def test_current_mechanism_surface_is_rendered_as_review_only(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    lines = build_mechanism_review_lines(tmp_path, _full_spine(tmp_path))
    text = "\n".join(lines)
    assert "Team Alpha" in text
    assert "grammar=PASS -> PASS" in text
    assert "resolved=10 (SUCCESS=7, FAILURE=3)" in text
    assert "same_team_continuation success=6/7 failure=1/3" in text
    assert "opponent_handover success=0/7 failure=2/3" in text
    assert "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY" in text
    assert "professional_emit_allowed=false" in text
    assert "causality" not in text.casefold() or "degildir" in text.casefold()


def test_stale_mechanism_artifact_is_not_consumed(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    lines = build_mechanism_review_lines(tmp_path, _full_spine(tmp_path, declared=False))
    text = "\n".join(lines)
    assert "eski artifact kullanilmadi" in text
    assert "Team Alpha" not in text


def test_standard_report_contains_review_section_without_promoting_emit(tmp_path: Path) -> None:
    _write_payloads(tmp_path)
    text = build_analyst_report(tmp_path, _full_spine(tmp_path))
    assert "ANALYST REVIEW — GORUNUR SUREC MEKANIZMASI ADAYLARI" in text
    assert "same_team_continuation success=6/7 failure=1/3" in text
    assert "professional_emit_allowed=false" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text
