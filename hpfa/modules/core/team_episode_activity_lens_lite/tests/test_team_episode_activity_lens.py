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
            {"context_id": "c3", "team_label": "Beta (2)", "action_family": "DUEL", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
            {"context_id": "c4", "team_label": "none", "action_family": "PASS", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
            {"context_id": "c5", "team_label": "Alpha (1)", "action_family": "SHOT", "zone_candidate": "DEFENSIVE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
            {"context_id": "c6", "team_label": "Alpha (1)", "action_family": "CARRY", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
            {"context_id": "c7", "team_label": "Alpha (1)", "action_family": "DRIBBLE", "zone_candidate": "FINAL_THIRD", "channel_candidate": "RIGHT_CHANNEL"},
            {"context_id": "c8", "team_label": "Beta (2)", "action_family": "TACKLE", "zone_candidate": "MIDDLE_THIRD", "channel_candidate": "CENTRAL_CHANNEL"},
        ],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    reviewed = {
        "c1": ("Alpha (1)", "PASS", "MIDDLE_THIRD", "CENTRAL_CHANNEL"),
        "c2": ("Alpha (1)", "SHOT", "FINAL_THIRD", "LEFT_CHANNEL"),
        "c3": ("Beta (2)", "DUEL", "DEFENSIVE_THIRD", "RIGHT_CHANNEL"),
        "c4": ("none", "PASS", "MIDDLE_THIRD", "CENTRAL_CHANNEL"),
        "c5": ("Alpha (1)", "RESTART", "DEFENSIVE_THIRD", "CENTRAL_CHANNEL"),
        "c6": ("Alpha (1)", "CARRY", "MIDDLE_THIRD", "RIGHT_CHANNEL"),
        "c7": ("Alpha (1)", "DRIBBLE", "FINAL_THIRD", "RIGHT_CHANNEL"),
        "c8": ("Beta (2)", "TACKLE", "MIDDLE_THIRD", "CENTRAL_CHANNEL"),
    }
    semantic = {
        "module_id": "context_action_semantics_rebind_lite_v1",
        "status": "PASS",
        "context_action_semantic_records": [
            {
                "context_id": context_id,
                "action_occurrence_eligible": True,
                "context_team_candidate": team,
                "provider_action_family_candidate": family,
                "context_zone_candidate": zone,
                "context_channel_candidate": channel,
            }
            for context_id, (team, family, zone, channel) in reviewed.items()
        ],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    episode = {
        "module_id": "analyst_episode_locator_lite_v1",
        "status": "PASS",
        "episode_candidates": [{
            "episode_candidate_id": "ep1", "period_candidate": "1",
            "start_second_candidate": 10.0, "end_second_candidate": 20.0,
            "action_occurrence_eligible_context_refs": list(reviewed),
        }],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "team_identity_candidates": [
            {"team_identity_candidate_id": "ta", "team_normalized_key": "alpha", "team_aliases_raw": ["Alpha (1)"]},
            {"team_identity_candidate_id": "tb", "team_normalized_key": "beta", "team_aliases_raw": ["Beta (2)"]},
        ],
        "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "production_release": False, "hard_block_hits": [],
    }
    return context, semantic, episode, identity


def test_activity_lens_uses_reviewed_semantics_and_real_family_composites():
    result = build_team_episode_activity_lens(*_inputs())
    assert result["status"] == "PASS"
    assert result["known_team_eligible_action_candidate_count"] == 7
    assert result["unknown_team_eligible_action_candidate_count"] == 1
    alpha = next(row for row in result["team_episode_activity_rows"] if row["team_identity_candidate_id"] == "ta")
    beta = next(row for row in result["team_episode_activity_rows"] if row["team_identity_candidate_id"] == "tb")
    assert alpha["visible_activity_signal_counts"]["CIRCULATION_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["CARRY_DRIBBLE_ACTIVITY_CANDIDATE"] == 2
    assert alpha["visible_activity_signal_counts"]["ADVANCED_ACCESS_ACTIVITY_CANDIDATE"] == 2
    assert alpha["visible_activity_signal_counts"]["TERMINAL_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["RESTART_RESET_ACTIVITY_CANDIDATE"] == 1
    assert beta["visible_activity_signal_counts"]["DUEL_TACKLE_ACTIVITY_CANDIDATE"] == 2
    assert alpha["action_family_candidate_counts"]["SHOT"] == 1
    assert alpha["action_family_candidate_counts"]["RESTART"] == 1
    assert alpha["action_family_source"] == "REVIEWED_PROVIDER_SEMANTICS"


def test_reviewed_restart_overrides_preliminary_shot_label():
    result = build_team_episode_activity_lens(*_inputs())
    alpha = next(row for row in result["team_episode_activity_rows"] if row["team_identity_candidate_id"] == "ta")
    assert alpha["visible_activity_signal_counts"]["TERMINAL_ACTIVITY_CANDIDATE"] == 1
    assert alpha["visible_activity_signal_counts"]["RESTART_RESET_ACTIVITY_CANDIDATE"] == 1


def test_unknown_team_rows_are_not_silently_assigned():
    result = build_team_episode_activity_lens(*_inputs())
    assert result["known_team_attribution_coverage_candidate"] == 0.875


def test_review_required_is_inherited():
    context, semantic, episode, identity = _inputs()
    semantic["status"] = "REVIEW_REQUIRED"
    result = build_team_episode_activity_lens(context, semantic, episode, identity)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "semantic_upstream_review_required" in result["review_hits"]


def test_missing_reviewed_semantics_does_not_fall_back_to_raw_family():
    context, semantic, episode, identity = _inputs()
    semantic["context_action_semantic_records"] = [row for row in semantic["context_action_semantic_records"] if row["context_id"] != "c5"]
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
