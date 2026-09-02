from hpfa.modules.core.action_occurrence_admission_lite.src.calibrated_source_semantics import (
    admit_spatial_semantics,
    admit_time_semantics,
    calibrated_claim_locks,
    map_team_pass_length_candidate,
)


def test_short_action_midpoint_requires_family_admission():
    blocked = admit_time_semantics(
        semantic_family="PASS", start=100.0, end=112.0, family_admitted=False
    )
    assert blocked.midpoint_anchor_candidate is None

    admitted = admit_time_semantics(
        semantic_family="PASS", start=100.0, end=112.0, family_admitted=True
    )
    assert admitted.midpoint_anchor_candidate == 106.0
    assert admitted.interval_role == "SHORT_ACTION_ANNOTATION_WINDOW_CANDIDATE"
    assert admitted.physical_action_duration is False


def test_long_interval_never_promotes_midpoint():
    result = admit_time_semantics(
        semantic_family="POSITIONAL_ATTACK", start=100.0, end=145.0, family_admitted=True
    )
    assert result.midpoint_anchor_candidate is None
    assert result.interval_role == "EPISODE_ANNOTATION_INTERVAL_CANDIDATE"


def test_non_twelve_second_action_window_stays_review_required():
    result = admit_time_semantics(
        semantic_family="SHOT", start=100.0, end=109.0, family_admitted=True
    )
    assert result.midpoint_anchor_candidate is None
    assert result.interval_role == "ANNOTATION_INTERVAL_REVIEW_REQUIRED"


def test_same_timestamp_never_creates_total_order():
    result = admit_time_semantics(
        semantic_family="DRIBBLE",
        start=100.0,
        end=112.0,
        family_admitted=True,
        same_timestamp_peer=True,
    )
    assert result.chronology_relation == "SAME_TIME_UNORDERED"


def test_spatial_anchor_is_never_tracking_or_endpoint_geometry():
    result = admit_spatial_semantics(semantic_family="SHOT", pos_x="96.42", pos_y="29.76")
    assert result["spatial_role"] == "SHOT_LOCATION_ANCHOR_CANDIDATE"
    assert result["coordinate_frame_status"] == "STRONGLY_SUPPORTED_CANDIDATE"
    assert result["physical_player_coordinate"] is False
    assert result["endpoint_geometry"] is False
    assert result["player_trajectory"] is False
    assert result["physical_speed"] is False


def test_episode_membership_uses_inherited_anchor_role():
    result = admit_spatial_semantics(
        semantic_family="INVOLVEMENT_IN_POSITIONAL_ATTACK", pos_x=52.5, pos_y=34.0
    )
    assert result["spatial_role"] == "INHERITED_EPISODE_ANCHOR_CANDIDATE"


def test_team_pass_length_mapping_preserves_raw_label():
    raw = "Goal kicks medium (15-40 m)"
    result = map_team_pass_length_candidate(
        raw_label=raw, surface_role="TEAM", action_family="PASS"
    )
    assert result["raw_provider_label"] == raw
    assert result["semantic_candidate"] == "PASS_LENGTH_MEDIUM_CANDIDATE"
    assert result["literal_goal_kick"] is False


def test_goalkeeper_goal_kick_is_not_remapped_as_pass_length():
    result = map_team_pass_length_candidate(
        raw_label="Goal kicks long (40+ m)",
        surface_role="GOALKEEPER",
        action_family="RESTART",
    )
    assert result["semantic_candidate"] is None
    assert result["mapping_status"] == "NOT_APPLIED"
    assert result["goalkeeper_surface_remapped"] is False


def test_claim_locks_remain_closed():
    locks = calibrated_claim_locks()
    assert locks["canonical_event_count"] == "UNKNOWN"
    assert locks["true_action_count"] == "UNKNOWN"
    assert locks["production_release"] is False
    assert locks["possession_truth"] is False
    assert locks["sequence_truth"] is False
    assert locks["tactical_truth"] is False
    assert locks["causal_truth"] is False


def test_no_sample_match_identity_leak():
    import inspect
    from hpfa.modules.core.action_occurrence_admission_lite.src import calibrated_source_semantics

    source = inspect.getsource(calibrated_source_semantics)
    forbidden = ["Genclerbirligi", "Fenerbahce", "15.08.2026", "27041", "29575"]
    assert all(token not in source for token in forbidden)
