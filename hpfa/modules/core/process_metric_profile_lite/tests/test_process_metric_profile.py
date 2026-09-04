from pathlib import Path

from hpfa.modules.core.process_metric_profile_lite.src.process_metric_profile import (
    build_process_metric_profile,
    write_outputs,
)


def _inputs(*, incomplete=False):
    robustness = {
        "module_id": "process_robustness_lens_lite_v1",
        "status": "PASS",
        "process_robustness_rows": [{
            "process_variant_profile_candidate_id": "pv1",
            "process_family_signature_candidate": {"anchor_action_families": ["PASS"], "response_action_families": ["PASS"]},
            "visible_repeat_count_candidate": 4,
            "incomplete_episode_binding_count": 1 if incomplete else 0,
            "episode_scope_dispersion_ratio_candidate": 0.75,
            "segment_concentration_share_candidate": 0.5,
            "max_anchor_actor_chain_presence_share_candidate": 0.5,
            "trace_membership_uniqueness_ratio_candidate": 0.8,
            "visible_outcome_normalized_entropy_candidate": 0.9,
            "recurrence_surface_robustness_composite_candidate": 0.683333,
        }],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    activity = {
        "module_id": "team_episode_activity_lens_lite_v1",
        "status": "PASS",
        "team_episode_activity_rows": [
            {
                "team_identity_candidate_id": "ta",
                "team_normalized_key_candidate": "alpha",
                "known_team_eligible_action_candidate_count": 10,
                "action_family_candidate_counts": {"PASS": 6, "SHOT": 2, "RESTART": 1, "CARRY_DRIBBLE": 1},
                "zone_candidate_counts": {"FINAL_THIRD": 5, "MIDDLE_THIRD": 5},
            },
            {
                "team_identity_candidate_id": "ta",
                "team_normalized_key_candidate": "alpha",
                "known_team_eligible_action_candidate_count": 10,
                "action_family_candidate_counts": {"PASS": 4, "SHOT": 1, "DUEL_PRESSURE": 3, "RESTART": 2},
                "zone_candidate_counts": {"FINAL_THIRD": 3, "MIDDLE_THIRD": 7},
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    reciprocal = {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "eligible_reciprocal_population_count": 20,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return robustness, activity, reciprocal


def test_process_metrics_preserve_match_local_units():
    result = build_process_metric_profile(*_inputs())
    assert result["status"] == "PASS"
    row = result["process_metric_rows"][0]
    assert row["M_PROCESS_REPEAT_POPULATION_SHARE_CANDIDATE"] == 0.2
    assert row["M_PROCESS_EPISODE_DISPERSION_CANDIDATE"] == 0.75
    assert row["M_PROCESS_RECURRENCE_SURFACE_ROBUSTNESS_COMPOSITE_CANDIDATE"] == 0.683333
    assert row["composite_is_calibrated"] is False
    assert row["statistical_significance_tested"] is False


def test_team_visible_funnel_ratios_use_same_known_team_surface():
    result = build_process_metric_profile(*_inputs())
    row = result["team_visible_activity_metric_rows"][0]
    assert row["known_team_eligible_action_candidate_count"] == 20
    assert row["visible_pass_family_candidate_count"] == 10
    assert row["visible_shot_family_candidate_count"] == 3
    assert row["visible_final_third_zone_candidate_count"] == 8
    assert row["M_TEAM_VISIBLE_FINAL_THIRD_ACTION_SHARE_CANDIDATE"] == 0.4
    assert row["M_TEAM_VISIBLE_SHOT_ACTION_SHARE_CANDIDATE"] == 0.15
    assert row["M_TEAM_VISIBLE_SHOT_PER_FINAL_THIRD_ACTION_CANDIDATE"] == 0.375
    assert row["M_TEAM_VISIBLE_TERMINAL_TO_PASS_RATIO_CANDIDATE"] == 0.3
    assert row["terminal_ratio_is_finishing_quality_or_conversion_probability"] is False


def test_incomplete_episode_binding_marks_process_metric_review_eligibility():
    result = build_process_metric_profile(*_inputs(incomplete=True))
    assert result["process_metric_rows"][0]["metric_eligibility_state"] == "REVIEW_REQUIRED_INCOMPLETE_EPISODE_BINDING"


def test_review_required_is_inherited():
    robustness, activity, reciprocal = _inputs()
    activity["status"] = "REVIEW_REQUIRED"
    result = build_process_metric_profile(robustness, activity, reciprocal)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "activity_upstream_review_required" in result["review_hits"]


def test_output_locks(tmp_path: Path):
    result = build_process_metric_profile(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "composite_metrics_are_calibrated=false" in text
    assert "statistical_significance_tested=false" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
