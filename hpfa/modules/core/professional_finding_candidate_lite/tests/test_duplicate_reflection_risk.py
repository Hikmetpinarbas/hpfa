from hpfa.modules.core.professional_finding_candidate_lite.src.duplicate_reflection_risk import (
    attach_duplicate_reflection_risk,
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
                "pending_falsifier_families": ["DUPLICATE_REFLECTION_RISK"],
            },
            "uncertainty": {},
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _reciprocal():
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "REVIEW_REQUIRED",
        "reciprocal_process_chain_candidates": [
            {"reciprocal_process_chain_candidate_id": "c1", "supporting_trackable_action_trace_candidate_ids": ["t1"]},
            {"reciprocal_process_chain_candidate_id": "c2", "supporting_trackable_action_trace_candidate_ids": ["t2"]},
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _trace():
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "status": "REVIEW_REQUIRED",
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "t1",
                "supporting_evidence_atom_ids": ["ea1"],
                "reflection_evidence_atom_ids": ["ea2"],
            },
            {
                "trackable_action_trace_candidate_id": "t2",
                "supporting_evidence_atom_ids": ["ea1", "ea3"],
                "reflection_evidence_atom_ids": [],
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _evidence():
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "evidence_atoms": [
            {
                "evidence_atom_id": "ea1",
                "row_nucleus_candidate_id": "rn1",
                "source_sha256_lineage": ["sha_csv", "sha_xml"],
                "reflection_dependency_state": "DEPENDENT_SERIALIZATION_REFLECTION",
            },
            {
                "evidence_atom_id": "ea2",
                "row_nucleus_candidate_id": "rn2",
                "source_sha256_lineage": ["sha_csv", "sha_xml"],
                "reflection_dependency_state": "DEPENDENT_SERIALIZATION_REFLECTION",
            },
            {
                "evidence_atom_id": "ea3",
                "row_nucleus_candidate_id": "rn3",
                "source_sha256_lineage": ["sha_other"],
                "reflection_dependency_state": "INDEPENDENCE_UNKNOWN_REVIEW_REQUIRED",
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_dependent_reflections_and_reused_atom_membership_are_not_independent_votes():
    result = attach_duplicate_reflection_risk(_finding(), _reciprocal(), _trace(), _evidence())
    row = result["professional_finding_candidates"][0]
    audit = row["finding_challenge_packet"]["duplicate_reflection_risk"]
    assert audit["state_candidate"] == "DEPENDENT_OR_REUSED_REFLECTION_SUPPORT_PRESENT"
    assert audit["nominal_evidence_atom_membership_count"] == 4
    assert audit["unique_evidence_atom_candidate_count"] == 3
    assert audit["reused_evidence_atom_ids_across_support_memberships"] == ["ea1"]
    assert set(audit["dependent_serialization_reflection_atom_ids"]) == {"ea1", "ea2"}
    assert audit["raw_atom_count_is_independent_evidence_count"] is False
    assert audit["csv_xml_reflections_are_independent_votes"] is False
    assert audit["dependent_reflection_adds_support_vote"] is False


def test_current_explicit_lineage_scope_removes_only_duplicate_reflection_pending_family():
    result = attach_duplicate_reflection_risk(_finding(), _reciprocal(), _trace(), _evidence())
    challenge = result["professional_finding_candidates"][0]["finding_challenge_packet"]
    assert "DUPLICATE_REFLECTION_RISK" not in challenge["pending_falsifier_families"]
    assert challenge["duplicate_reflection_search_complete_for_current_explicit_lineage_scope"] is True
    assert challenge["duplicate_reflection_search_complete_for_final_finding"] is False


def test_missing_atom_lineage_keeps_review_state_without_inventing_independence():
    trace = _trace()
    trace["trackable_action_trace_candidates"][1]["supporting_evidence_atom_ids"].append("missing")
    result = attach_duplicate_reflection_risk(_finding(), _reciprocal(), trace, _evidence())
    audit = result["professional_finding_candidates"][0]["finding_challenge_packet"]["duplicate_reflection_risk"]
    assert audit["state_candidate"] == "PARTIAL_REFLECTION_LINEAGE_COVERAGE_REVIEW_REQUIRED"
    assert audit["missing_evidence_atom_ids"] == ["missing"]
    assert audit["absence_of_duplicate_membership_proves_independence"] is False


def test_claim_locks_remain_closed_after_reflection_audit():
    result = attach_duplicate_reflection_risk(_finding(), _reciprocal(), _trace(), _evidence())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["claim_output_allowed_count"] == 0
    assert result["professional_finding_emitted_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
