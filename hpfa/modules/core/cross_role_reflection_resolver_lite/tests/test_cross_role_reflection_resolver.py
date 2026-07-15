from hpfa.modules.core.cross_role_reflection_resolver_lite.src.cross_role_reflection_resolver import resolve_cross_role_reflections


def _primary(candidate_id: str, family: str, *, start: float = 12.0, x: float = 50.0) -> dict:
    return {
        "base_event_candidate_id": candidate_id,
        "base_event_family": family,
        "source_semantic_route": "PLAYER_PRIMARY_ACTION_SURFACE",
        "action_group_key": [
            "active_single_match_current",
            "players",
            "PLAYER_PRIMARY_ACTION_SURFACE",
            "Player A",
            "Team A",
            "1",
            start,
            start + 1,
            x,
            30.0,
        ],
    }


def _reflection(relation_id: str, route: str, label_id: str, label: str, *, start: float = 12.0, x: float = 50.0) -> tuple[dict, dict]:
    relation = {
        "reflection_relation_id": relation_id,
        "source_semantic_route": route,
        "event_label_candidate_ids": [label_id],
        "action_group_key": [
            "active_single_match_current",
            "teams" if route.startswith("TEAM") else "goalkeepers",
            route,
            "Team A" if route.startswith("TEAM") else "Goalkeeper A",
            "Team A",
            "1",
            start,
            start + 1,
            x,
            30.0,
        ],
        "relation_status": "UNRESOLVED_CROSS_ROLE_LINK",
    }
    label_entry = {
        "event_label_candidate_id": label_id,
        "normalized_label": label,
    }
    return relation, label_entry


def test_team_reflection_links_to_exact_player_primary_candidate() -> None:
    relation, label = _reflection("rr_team", "TEAM_ACTION_REFLECTION_SURFACE", "el_pass", "passes_accurate")
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [_primary("be_pass", "PASS")],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["resolved_reflection_link_count"] == 1
    assert result["resolved_reflection_links"][0]["linked_primary_event_candidate_id"] == "be_pass"
    assert result["canonical_event_count"] == "UNKNOWN"


def test_goalkeeper_shot_reflection_links_to_player_shot_candidate() -> None:
    relation, label = _reflection(
        "rr_gk_shot",
        "GOALKEEPER_OPPONENT_ACTION_REFLECTION",
        "el_shot",
        "shots_on_target",
    )
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [_primary("be_shot", "SHOT")],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["resolved_reflection_link_count"] == 1
    assert result["resolved_reflection_links"][0]["reflected_family_hints"] == ["SHOT"]


def test_nearby_but_non_exact_time_does_not_link() -> None:
    relation, label = _reflection("rr_team", "TEAM_ACTION_REFLECTION_SURFACE", "el_pass", "passes", start=12.1)
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [_primary("be_pass", "PASS", start=12.0)],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["resolved_reflection_link_count"] == 0
    assert result["unresolved_reflection_link_count"] == 1
    assert result["decision_state"] == "REVIEW_REQUIRED_UNRESOLVED_REFLECTION_LINKS"


def test_multiple_exact_primary_candidates_remain_ambiguous() -> None:
    relation, label = _reflection("rr_team", "TEAM_ACTION_REFLECTION_SURFACE", "el_pass", "passes")
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [
            _primary("be_pass_1", "PASS"),
            _primary("be_pass_2", "PASS"),
        ],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["ambiguous_reflection_link_count"] == 1
    assert result["resolved_reflection_link_count"] == 0
    assert result["decision_state"] == "REVIEW_REQUIRED_AMBIGUOUS_REFLECTION_LINKS"


def test_participation_label_does_not_infer_reflected_shot_family() -> None:
    relation, label = _reflection(
        "rr_participation",
        "TEAM_ACTION_REFLECTION_SURFACE",
        "el_participation",
        "involvement_in_attack_with_shot",
    )
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [_primary("be_shot", "SHOT")],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["resolved_reflection_link_count"] == 0
    assert result["unresolved_reflection_links"][0]["reflected_family_hints"] == []


def test_goal_kick_reflection_prefers_restart_over_shot() -> None:
    relation, label = _reflection(
        "rr_goal_kick",
        "TEAM_ACTION_REFLECTION_SURFACE",
        "el_goal_kick",
        "goal_kicks_long_40_m",
    )
    result = resolve_cross_role_reflections({
        "base_event_surface_candidates": [
            _primary("be_restart", "RESTART"),
            _primary("be_shot", "SHOT"),
        ],
        "event_label_candidates": [label],
        "cross_role_reflection_relations": [relation],
    })
    assert result["resolved_reflection_link_count"] == 1
    assert result["resolved_reflection_links"][0]["linked_primary_event_candidate_id"] == "be_restart"
    assert result["resolved_reflection_links"][0]["reflected_family_hints"] == ["RESTART"]
