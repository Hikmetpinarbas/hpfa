from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_occurrence_consequence_burden_adapter import (
    _handoff_visible_outcome_identification_bound,
)


def test_outcome_contrast_selected_family_does_not_create_neutral_estimand_universe():
    handoff = {
        "support": {"visible_success_sequence_refs": ["s1"]},
        "counterevidence": {"visible_failure_sequence_refs": ["s2"]},
    }
    process = {
        "observable_process_variant_families": [{
            "observable_process_variant_family_id": "family_1",
            "member_records": [
                {"sequence_ref": "s1", "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE"},
                {"sequence_ref": "s2", "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE"},
                {"sequence_ref": "s3", "visible_outcome_state": None},
            ],
        }]
    }
    bound = _handoff_visible_outcome_identification_bound(handoff, process)
    assert bound["bound_state"] == "BOUND_UNRESOLVED"
    assert bound["eligible_total_n"] is None
    assert "OUTCOME_CONDITIONED_ESTIMAND_UNIVERSE_UNRESOLVED" in bound["bound_review_reasons"]
    assert bound["estimand_universe_selected_without_outcome"] is False
