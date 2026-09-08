from trackable_action_consequence_candidates_current_v1 import _occurrence_context_projection


def _binding(**overrides):
    value = {
        "action_occurrence_candidate_id": "occ_a",
        "team_refs": ["team_a", "team_b"],
        "goalkeeper_refs": ["gk_a"],
        "goalkeeper_context_bundle_refs": ["gk_bundle_a"],
        "reflection_context_refs": ["team_bundle_a"],
        "relation_types": ["OCCURRENCE_HAS_TEAM", "OCCURRENCE_HAS_GOALKEEPER"],
        "binding_is_event_truth": False,
        "goalkeeper_context_is_occurrence_participant_truth": False,
        "object_view_count_is_independent_support_count": False,
        "object_view_creates_event": False,
        "canonical_event_count": "UNKNOWN",
    }
    value.update(overrides)
    return value


def test_context_projection_preserves_team_goalkeeper_and_reflection_refs_without_claim_upgrade():
    payload = {"occurrence_trace_binding_records": [_binding()]}

    result = _occurrence_context_projection(payload, {"occ_a"})

    assert result["occurrence_object_context_state"] == "OCCURRENCE_OBJECT_CONTEXT_ONLY"
    assert result["occurrence_team_context_refs"] == ["team_a", "team_b"]
    assert result["occurrence_goalkeeper_context_refs"] == ["gk_a"]
    assert result["occurrence_goalkeeper_context_bundle_refs"] == ["gk_bundle_a"]
    assert result["occurrence_reflection_context_refs"] == ["team_bundle_a"]
    assert result["occurrence_relation_type_candidates"] == ["OCCURRENCE_HAS_GOALKEEPER", "OCCURRENCE_HAS_TEAM"]
    assert result["occurrence_context_is_independent_support"] is False
    assert result["goalkeeper_context_is_occurrence_participant_truth"] is False
    assert result["reflection_context_is_event_equivalence_truth"] is False
    assert result["occurrence_context_creates_event"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_claim_upgraded_occurrence_binding_fails_to_review_without_context_refs():
    payload = {
        "occurrence_trace_binding_records": [
            _binding(binding_is_event_truth=True),
        ]
    }

    result = _occurrence_context_projection(payload, {"occ_a"})

    assert result["occurrence_object_context_state"] == "REVIEW_REQUIRED"
    assert result["occurrence_team_context_refs"] == []
    assert result["occurrence_goalkeeper_context_refs"] == []
    assert result["occurrence_goalkeeper_context_bundle_refs"] == []
    assert result["occurrence_reflection_context_refs"] == []
    assert result["occurrence_context_projection_review_hits"] == [
        "occurrence_context_claim_boundary_mismatch:occ_a"
    ]


def test_unrequested_occurrence_cannot_leak_context():
    payload = {"occurrence_trace_binding_records": [_binding()]}

    result = _occurrence_context_projection(payload, {"occ_b"})

    assert result["occurrence_object_context_state"] == "NO_CONTEXT_VISIBLE"
    assert result["occurrence_team_context_refs"] == []
    assert result["occurrence_goalkeeper_context_refs"] == []
    assert result["occurrence_reflection_context_refs"] == []
