import visible_action_sequence_candidates_current_v1 as current


def _base_payload():
    return {
        "status": "PASS",
        "module_status": "PASS",
        "review_hits": [],
        "visible_action_sequence_candidates": [
            {
                "visible_action_sequence_candidate_id": "SEQ_GENERIC",
                "trackable_action_trace_candidate_ids": ["TRACE_A", "TRACE_B"],
                "canonical_event_count": "UNKNOWN",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence(trace_id, *, team=None, goalkeeper=None, reflection=None):
    return {
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "occurrence_object_context_state": "OCCURRENCE_OBJECT_CONTEXT_ONLY",
        "occurrence_team_context_refs": team or [],
        "occurrence_goalkeeper_context_refs": goalkeeper or [],
        "occurrence_goalkeeper_context_bundle_refs": [],
        "occurrence_reflection_context_refs": reflection or [],
        "occurrence_relation_type_candidates": ["OBJECT_CONTEXT_ONLY"],
        "occurrence_context_is_independent_support": False,
        "goalkeeper_context_is_occurrence_participant_truth": False,
        "reflection_context_is_event_equivalence_truth": False,
        "occurrence_context_creates_event": False,
        "canonical_event_count": "UNKNOWN",
    }


def test_sequence_projection_preserves_refs_without_claim_upgrade():
    payload = _base_payload()
    consequence_payload = {
        "trackable_action_consequence_candidates": [
            _consequence("TRACE_A", team=["TEAM_CTX"], goalkeeper=["GK_CTX"]),
            _consequence("TRACE_B", reflection=["REFLECT_CTX"]),
        ]
    }
    out = current._project_sequence_occurrence_context(payload, consequence_payload)
    row = out["visible_action_sequence_candidates"][0]
    assert row["sequence_occurrence_object_context_state"] == "SEQUENCE_OCCURRENCE_OBJECT_CONTEXT_ONLY"
    assert row["sequence_occurrence_team_context_refs"] == ["TEAM_CTX"]
    assert row["sequence_occurrence_goalkeeper_context_refs"] == ["GK_CTX"]
    assert row["sequence_occurrence_reflection_context_refs"] == ["REFLECT_CTX"]
    assert row["sequence_occurrence_context_is_independent_support"] is False
    assert row["goalkeeper_context_is_sequence_participant_truth"] is False
    assert row["reflection_context_is_sequence_equivalence_truth"] is False
    assert row["sequence_occurrence_context_creates_event"] is False
    assert row["sequence_occurrence_context_ref_count_is_action_count"] is False
    assert row["canonical_event_count"] == "UNKNOWN"


def test_sequence_projection_fails_to_review_on_claim_upgrade():
    payload = _base_payload()
    bad = _consequence("TRACE_A", team=["TEAM_CTX"])
    bad["occurrence_context_is_independent_support"] = True
    out = current._project_sequence_occurrence_context(
        payload,
        {"trackable_action_consequence_candidates": [bad, _consequence("TRACE_B")]},
    )
    row = out["visible_action_sequence_candidates"][0]
    assert out["status"] == "REVIEW_REQUIRED"
    assert row["sequence_occurrence_object_context_state"] == "REVIEW_REQUIRED"
    assert row["sequence_occurrence_team_context_refs"] == []
    assert row["sequence_occurrence_context_projection_review_hits"]
    assert out["canonical_event_count"] == "UNKNOWN"
    assert out["production_release"] is False
