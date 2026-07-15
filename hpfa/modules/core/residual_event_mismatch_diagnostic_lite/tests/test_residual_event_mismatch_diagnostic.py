from hpfa.modules.core.residual_event_mismatch_diagnostic_lite.src.residual_event_mismatch_diagnostic import diagnose_residual_event_mismatch


def _payload():
    return {
        "base_event_family_counts": {"SHOT": 2, "PASS": 1},
        "event_label_candidates": [
            {"event_label_candidate_id": "l1", "normalized_label": "shots_on_target"},
            {"event_label_candidate_id": "l2", "normalized_label": "shots_saved"},
            {"event_label_candidate_id": "l3", "normalized_label": "passes_accurate"},
        ],
        "base_event_surface_candidates": [
            {"base_event_family": "SHOT", "source_semantic_route": "PLAYER_PRIMARY_ACTION_SURFACE", "event_label_candidate_ids": ["l1"]},
            {"base_event_family": "SHOT", "source_semantic_route": "PLAYER_PRIMARY_ACTION_SURFACE", "event_label_candidate_ids": ["l2"]},
            {"base_event_family": "PASS", "source_semantic_route": "PLAYER_PRIMARY_ACTION_SURFACE", "event_label_candidate_ids": ["l3"]},
        ],
        "cross_role_reflection_relations": [
            {"source_semantic_route": "TEAM_ACTION_REFLECTION_SURFACE"},
            {"source_semantic_route": "GOALKEEPER_OPPONENT_ACTION_REFLECTION"},
        ],
    }


def test_residual_mismatch_is_blocked_and_localized():
    result = diagnose_residual_event_mismatch(_payload(), {"aggregate_family_counts": {"SHOT": 1, "PASS": 1}})
    assert result["decision_state"] == "BLOCKED_RESIDUAL_EVENT_MISMATCH"
    assert result["blocked_families"] == ["SHOT"]
    shot = next(row for row in result["family_diagnostics"] if row["event_family"] == "SHOT")
    assert shot["signed_delta"] == 1
    assert shot["candidate_source_route_counts"] == {"PLAYER_PRIMARY_ACTION_SURFACE": 2}
    assert shot["top_candidate_labels"][0]["candidate_attachment_count"] == 1
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_exact_parity_does_not_create_canonical_events():
    result = diagnose_residual_event_mismatch(_payload(), {"aggregate_family_counts": {"SHOT": 2, "PASS": 1}})
    assert result["decision_state"] == "PASS_NO_RESIDUAL_MISMATCH"
    assert result["blocked_families"] == []
    assert result["identity_bound_event_count"] == 0


def test_reflections_are_reported_but_not_added_to_family_counts():
    result = diagnose_residual_event_mismatch(_payload(), {"aggregate_family_counts": {"SHOT": 2, "PASS": 1}})
    assert result["cross_role_reflection_counts"] == {
        "GOALKEEPER_OPPONENT_ACTION_REFLECTION": 1,
        "TEAM_ACTION_REFLECTION_SURFACE": 1,
    }
    shot = next(row for row in result["family_diagnostics"] if row["event_family"] == "SHOT")
    assert shot["provisional_surface_count"] == 2
