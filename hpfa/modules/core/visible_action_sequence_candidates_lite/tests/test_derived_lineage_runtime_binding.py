from hpfa.modules.core.visible_action_sequence_candidates_lite.src.derived_lineage_runtime_binding import (
    bind_derived_lineage,
)


def _sequence_payload():
    divergence_id = "fsbd_root_1"
    handoff_id = "sfh_1"
    return {
        "first_supported_branch_divergence_candidates": [
            {
                "first_supported_branch_divergence_id": divergence_id,
                "branch_profiles": [
                    {
                        "neighbor_supporting_action_occurrence_candidate_ids": ["occ_1"]
                    }
                ],
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        ],
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": handoff_id,
                "source_first_supported_branch_divergence_ref": divergence_id,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _puzzle_payload():
    return {
        "puzzle_findings": [
            {
                "puzzle_finding_id": "pf_sfh_1",
                "source_safe_finding_handoff_ref": "sfh_1",
            },
            {
                "puzzle_finding_id": "pf_progression_access_sfh_1",
                "source_safe_finding_handoff_ref": "sfh_1",
                "family_projection": {"state": "ADMITTED_SOURCE_LINEAGE_FAMILY_VIEW"},
            },
            {
                "puzzle_finding_id": "pf_retention_loss_sfh_1",
                "source_safe_finding_handoff_ref": "sfh_1",
                "family_projection": {"state": "ADMITTED_SOURCE_LINEAGE_FAMILY_VIEW"},
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _claim_payload():
    return {
        "analyst_output_contracts": [
            {
                "analyst_output_contract_id": "aoc_sfh_1",
                "source_safe_finding_handoff_ref": "sfh_1",
                "professional_emit_allowed": False,
                "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_family_views_and_claim_share_one_bounded_occurrence_ancestor_group():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())

    assert result["status"] == "PASS"
    summary = result["summary"]
    assert summary["bounded_lineage_group_count"] == 1
    assert summary["bounded_occurrence_ancestor_count"] == 1
    assert summary["lineage_group_count_is_admitted_independent_support_count"] is False
    assert summary["bounded_ancestry_distinctness_is_independence_proof"] is False
    assert summary["lineage_can_increase_existing_independent_support"] is False
    assert summary["lineage_can_authorize_emit"] is False
    assert summary["current_topology"] == (
        "BOUNDED_OCCURRENCE_ANCESTOR_TO_DIVERGENCE_TO_SAFE_FINDING_THEN_PUZZLE_AND_CLAIM_SIBLINGS"
    )

    findings = result["puzzle_payload"]["puzzle_findings"]
    assert len({row["derived_lineage"]["lineage_group_id"] for row in findings}) == 1
    assert all(row["derived_lineage"]["root_refs"] == ["occ_1"] for row in findings)
    assert findings[1]["family_view_shares_source_lineage_root"] is True
    assert findings[2]["family_view_shares_source_lineage_root"] is True
    assert all(row["shared_ancestor_can_add_independent_support"] is False for row in findings)

    claim = result["claim_payload"]["analyst_output_contracts"][0]
    assert claim["derived_lineage"]["root_refs"] == ["occ_1"]
    assert claim["puzzle_sibling_is_claim_parent"] is False
    assert sorted(claim["puzzle_sibling_refs"]) == sorted(row["puzzle_finding_id"] for row in findings)
    assert claim["professional_emit_allowed"] is False


def test_shared_occurrence_ancestor_is_exposed_without_support_inflation():
    sequence = _sequence_payload()
    sequence["first_supported_branch_divergence_candidates"].append(
        {
            "first_supported_branch_divergence_id": "fsbd_root_2",
            "branch_profiles": [
                {
                    "neighbor_supporting_action_occurrence_candidate_ids": ["occ_1", "occ_2"]
                }
            ],
        }
    )

    result = bind_derived_lineage(sequence, {}, {})

    assert result["status"] == "PASS"
    summary = result["summary"]
    assert summary["resolved_divergence_count"] == 2
    assert summary["shared_occurrence_ancestor_count"] == 1
    assert summary["divergence_occurrence_ancestry_edge_count"] == 3
    assert summary["reused_occurrence_ancestry_edge_count"] == 1
    assert summary["reused_occurrence_ancestry_edge_denominator"] == 3
    assert summary["provenance_multiplicity_state"] == "ANCESTRY_REUSE_PRESENT"
    assert summary["structural_multiplicity_equals_provenance_multiplicity"] is False
    assert summary["structural_multiplicity_is_independent_support"] is False
    assert summary["divergence_with_shared_ancestor_count"] == 2
    assert summary["shared_ancestor_can_add_independent_support"] is False
    rows = result["sequence_payload"]["first_supported_branch_divergence_candidates"]
    by_id = {row["first_supported_branch_divergence_id"]: row for row in rows}
    assert by_id["fsbd_root_1"]["shared_ancestor_overlap_state"] == "SHARED_ANCESTOR_OVERLAP"
    assert by_id["fsbd_root_1"]["shared_ancestor_refs"] == ["occ_1"]
    assert by_id["fsbd_root_1"]["bounded_occurrence_ancestor_ref_count"] == 1
    assert by_id["fsbd_root_1"]["shared_ancestor_ref_count"] == 1
    assert by_id["fsbd_root_2"]["shared_ancestor_refs"] == ["occ_1"]
    assert by_id["fsbd_root_2"]["bounded_occurrence_ancestor_ref_count"] == 2
    assert by_id["fsbd_root_2"]["shared_ancestor_ref_count"] == 1
    assert by_id["fsbd_root_2"]["bounded_ancestry_distinctness_is_independence_proof"] is False


def test_distinct_occurrence_ancestry_is_not_independence_proof():
    sequence = _sequence_payload()
    sequence["first_supported_branch_divergence_candidates"].append(
        {
            "first_supported_branch_divergence_id": "fsbd_root_2",
            "branch_profiles": [
                {"neighbor_supporting_action_occurrence_candidate_ids": ["occ_2"]}
            ],
        }
    )

    result = bind_derived_lineage(sequence, {}, {})

    assert result["status"] == "PASS"
    summary = result["summary"]
    assert summary["shared_occurrence_ancestor_count"] == 0
    assert summary["divergence_occurrence_ancestry_edge_count"] == 2
    assert summary["reused_occurrence_ancestry_edge_count"] == 0
    assert summary["reused_occurrence_ancestry_edge_denominator"] == 2
    assert summary["provenance_multiplicity_state"] == "NO_ANCESTRY_REUSE_WITHIN_TRACKED_SCOPE"
    assert summary["divergence_without_shared_ancestor_within_tracked_scope_count"] == 2
    assert summary["bounded_ancestry_distinctness_is_independence_proof"] is False
    for row in result["sequence_payload"]["first_supported_branch_divergence_candidates"]:
        assert row["shared_ancestor_overlap_state"] == "NO_SHARED_ANCESTOR_WITHIN_TRACKED_SCOPE"
        assert row["bounded_ancestry_distinctness_is_independence_proof"] is False


def test_missing_occurrence_ancestry_remains_review_required_and_cannot_promote_claim():
    sequence = _sequence_payload()
    sequence["first_supported_branch_divergence_candidates"][0]["branch_profiles"] = []

    result = bind_derived_lineage(sequence, _puzzle_payload(), _claim_payload())

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["summary"]["unresolved_divergence_ancestry_count"] == 1
    assert result["summary"]["divergence_occurrence_ancestry_edge_count"] == 0
    assert result["summary"]["reused_occurrence_ancestry_edge_count"] == 0
    assert result["summary"]["provenance_multiplicity_state"] == "NO_RESOLVED_ANCESTRY"
    row = result["claim_payload"]["analyst_output_contracts"][0]
    assert row["derived_lineage"]["status"] == "REVIEW_REQUIRED"
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == "NO_CLAIM_OUTPUT"


def test_missing_handoff_parent_for_claim_fails_closed_to_no_claim_output():
    claim = _claim_payload()
    claim["analyst_output_contracts"][0]["source_safe_finding_handoff_ref"] = "missing_handoff"

    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), claim)

    assert result["status"] == "REVIEW_REQUIRED"
    row = result["claim_payload"]["analyst_output_contracts"][0]
    assert row["derived_lineage"]["status"] == "REVIEW_REQUIRED"
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == "NO_CLAIM_OUTPUT"
    assert row["lineage_can_authorize_emit"] is False


def test_root_scope_is_explicitly_bounded_occurrence_not_absolute_evidence_root():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())
    summary = result["summary"]
    assert summary["root_is_absolute_observation_or_evidence_root"] is False
    assert summary["root_is_bounded_admitted_occurrence_ancestor"] is True
    for row in result["sequence_payload"]["first_supported_branch_divergence_candidates"]:
        envelope = row["derived_lineage"]
        assert envelope["root_is_absolute_observation_or_evidence_root"] is False
        assert envelope["root_is_current_tracked_derived_chain_root"] is False
        assert envelope["root_is_bounded_admitted_occurrence_ancestor"] is True
        assert envelope["occurrence_ancestor_is_event_truth"] is False


def test_binding_preserves_truth_locks_and_never_creates_evidence():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["summary"]["lineage_creates_new_evidence"] is False
    assert result["summary"]["lineage_can_strengthen_claim_ceiling"] is False
    assert result["summary"]["shared_ancestor_can_add_independent_support"] is False
