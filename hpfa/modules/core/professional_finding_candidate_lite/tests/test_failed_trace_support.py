from hpfa.modules.core.professional_finding_candidate_lite.src.failed_trace_support import (
    attach_failed_trace_support,
)


def _finding():
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [{
            "professional_finding_candidate_id": "p1",
            "support": {"supporting_reciprocal_process_chain_candidate_ids": ["c1", "c2"]},
            "finding_challenge_packet": {
                "evaluated_falsifier_families": [],
                "pending_falsifier_families": ["FAILED_TRACE_SUPPORT", "ALTERNATIVE_EXPLANATION"],
            },
            "uncertainty": {},
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _reciprocal(second_has_trace=True):
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": [
            {
                "reciprocal_process_chain_candidate_id": "c1",
                "supporting_trackable_action_trace_candidate_ids": ["t1"],
            },
            {
                "reciprocal_process_chain_candidate_id": "c2",
                "supporting_trackable_action_trace_candidate_ids": ["t2"] if second_has_trace else [],
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _trace(partial=False):
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "REVIEW_REQUIRED" if partial else "PASS",
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "t1",
                "supporting_action_occurrence_candidate_ids": ["o1"],
            },
            {
                "trackable_action_trace_candidate_id": "t2",
                "supporting_action_occurrence_candidate_ids": ["o2"],
            },
        ],
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "o1",
                "binding_state": "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE",
            },
            {
                "action_occurrence_candidate_id": "o2",
                "binding_state": (
                    "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED"
                    if partial else "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE"
                ),
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_chain_linkage_scope_is_available_without_trace_payload_but_does_not_close_full_debt():
    result = attach_failed_trace_support(_finding(), _reciprocal(), None)
    row = result["professional_finding_candidates"][0]
    audit = row["finding_challenge_packet"]["failed_trace_support"]
    assert audit["state_candidate"] == "CHAIN_TRACE_LINKAGE_VISIBLE_CURRENT_SCOPE"
    assert audit["full_occurrence_binding_scope_evaluated"] is False
    assert "FAILED_TRACE_SUPPORT" in row["finding_challenge_packet"]["pending_falsifier_families"]
    assert row["claim_output_allowed"] is False


def test_missing_chain_trace_linkage_is_evidence_debt_not_failed_action_truth():
    result = attach_failed_trace_support(_finding(), _reciprocal(second_has_trace=False), None)
    audit = result["professional_finding_candidates"][0]["finding_challenge_packet"]["failed_trace_support"]
    assert audit["state_candidate"] == "INCOMPLETE_CHAIN_TRACE_LINKAGE_REVIEW_REQUIRED"
    assert audit["missing_trace_is_failed_football_action"] is False
    assert audit["missing_trace_is_counterevidence"] is False


def test_full_occurrence_scope_can_close_failed_trace_support_family_when_complete():
    result = attach_failed_trace_support(_finding(), _reciprocal(), _trace())
    row = result["professional_finding_candidates"][0]
    audit = row["finding_challenge_packet"]["failed_trace_support"]
    assert audit["state_candidate"] == "COMPLETE_VISIBLE_PARTICIPANT_TRACE_SUPPORT_CURRENT_SCOPE"
    assert audit["full_occurrence_binding_scope_evaluated"] is True
    assert "FAILED_TRACE_SUPPORT" not in row["finding_challenge_packet"]["pending_falsifier_families"]
    assert result["claim_output_allowed_count"] == 0


def test_partial_occurrence_trace_binding_keeps_review_required_and_claim_closed():
    result = attach_failed_trace_support(_finding(), _reciprocal(), _trace(partial=True))
    audit = result["professional_finding_candidates"][0]["finding_challenge_packet"]["failed_trace_support"]
    assert audit["state_candidate"] == "INCOMPLETE_OCCURRENCE_TRACE_EVIDENCE_REVIEW_REQUIRED"
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["claim_output_allowed_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
