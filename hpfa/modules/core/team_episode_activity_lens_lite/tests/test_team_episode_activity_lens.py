from pathlib import Path

from hpfa.modules.core.team_episode_activity_lens_lite.src.team_episode_activity_lens import (
    build_team_episode_activity_lens,
    write_outputs,
)


def _inputs():
    context = {
        "module_id": "minimum_viable_context_lite_v1",
        "status": "PASS",
        "context_candidates": [
            {"context_id": "c1", "team_label": "Alpha (1)", "action_family": "PASS", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
            {"context_id": "c2", "team_label": "Alpha (1)", "action_family": "SHOT", "zone_candidate": "FINAL_THIRD", "channel_candidate": "LEFT_CHANNEL"},
            {"context_id": "c3", "team_label": "Beta (2)", "action_family": "DUEL_PRESSURE", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
            {"context_id": "c4", "team_label": "none", "action_family": "PASS", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
            # Preliminary normalizer is intentionally wrong here; reviewed semantics must win.
            {"context_id": "c5", "team_label": "Alpha (1)", "action_family": "SHOT", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    semantic = {
        "module_id": "context_action_semantics_rebind_lite_v1",
        "status": "PASS",
        "context_action_semantic_records": [
            {"context_id": "c1", "action_occurrence_eligible": True, "context_team_candidate": "Alpha (1)", "provider_action_family_candidate": "PASS", "context_zone_candidate": "MIDDLE_THIRD", "context_channel_candidate": "CENTRAL_CHANNEL"},
            {"context_id": "c2", "action_occurrence_eligible": True, "context_team_candidate": "Alpha (1)", "provider_action_family_candidate": "SHOT", "context_zone_candidate": "FINAL_THIRD", "context_channel_candidate": "LEFT_CHANNEL"},
            {"context_id": "c3", "action_occurrence_eligible": True, "context_team_candidate": "Beta (2)", "provider_action_family_candidate": "DUEL_PRESSURE", "context_zone_candidate": "DEFENSIVE_THIRD", "context_channel_candidate": "RIGHT_CHANNEL"},
            {"context_id": "c4", "action_occurrence_eligible": True, "context_team_candidate": "none", "provider_action_family_candidate": "PASS", "context_zone_candidate": "MIDDLE_THIRD", "context_channel_candidate": "CENTRAL_CHANNEL"},
            {"context_id": "c5", "action_occurrence_eligible": True, "context_team_candidate": "Alpha (1)", "provider_action_family_candidate": "RESTART", "context_zone_candidate": "DEFENSIVE_THIRD", "context_channel_candidate": "CENTRAL_CHANNEL"},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    episode = {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "episode_candidates": [
            {
                "episode_candidate_id": "ep1",
                "period_candidate": "1",
                "start_second_candidate": 10.0,
                "end_second_candidate": 20.0,
                "action_occurrence_eligible_context_refs": ["c1", "c2", "c3", "c4", "c5"],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "team_identity_candidates": [
            {"team_identity_candidate_id": "ta", "team_normalized_key": "alpha", "team_aliases_raw": ["Alpha (1)"]},
            {"team_identity_candidate_id": "tb", "team_normalized_key": "beta", "team_aliases_raw": ["Beta (2)"]},
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return context, semantic, episode, identity


def test_activity_lens_uses_reviewed_semantics_and_is_multi_label():
    result = build_team_episode_activity_lens(*_inputs())
    assert result["status"] == "PASS"
    assert result["team_episode_activity_row_count"] == 2
    assert result["known_team_eligible_action_candidate_count"] == 4
    assert result["unknown_team_eligible_action_candidate_count"] == 1
    alpha = next(row for row in result["team_episode_activity_rows"] if row["team_identity_candidate_id"] == "ta")
    assert alpha["visible_activity_signal_counts"]["CIRCULATION_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["ADVANCED_ACCESS_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["TERMINAL_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["RESTART_RESET_ACTIVITY_CANDIDATE"] == 1
    assert alpha["action_family_candidate_counts"]["SHOT"] == 1
    assert alpha["action_family_candidate_counts"]["RESTART"] == 1
    assert alpha["action_family_source"] == "REVIEWED_PROVIDER_SEMANTICS"
    assert alpha["activity_signals_are_mutually_exclusive_phases"] is False


def test_reviewed_restart_overrides_preliminary_shot_label():
    result = build_team_episode_activity_lens(*_inputs())
    alpha = next(row for row in result["team_episode_activity_rows"] if row["team_identity_candidate_id"] == "ta")
    assert alpha["visible_activity_signal_counts"]["TERMINAL_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["RESTART_RESET_ACTIVITY_CANDIDATE"] == 1


def test_unknown_team_rows_are_not_silently_assigned():
    result = build_team_episode_activity_lens(*_inputs())
    assert result["known_team_attribution_coverage_candidate"] == 0.8
    assert result["unknown_team_eligible_action_candidate_count"] == 1


def test_review_required_is_inherited():
    context, semantic, episode, identity = _inputs()
    semantic["status"] = "REVIEW_REQUIRED"
    result = build_team_episode_activity_lens(context, semantic, episode, identity)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "semantic_upstream_review_required" in result["review_hits"]


def test_missing_reviewed_semantics_does_not_fall_back_to_raw_family():
    context, semantic, episode, identity = _inputs()
    semantic["context_action_semantic_records"] = [
        row for row in semantic["context_action_semantic_records"] if row["context_id"] != "c5"
    ]
    result = build_team_episode_activity_lens(context, semantic, episode, identity)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["reviewed_semantics_missing_for_eligible_context_count"] == 1


def test_output_locks(tmp_path: Path):
    result = build_team_episode_activity_lens(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "action_family_source=REVIEWED_PROVIDER_SEMANTICS" in text
    assert "true_phase_truth=false" in text
    assert "possession_truth=false" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
