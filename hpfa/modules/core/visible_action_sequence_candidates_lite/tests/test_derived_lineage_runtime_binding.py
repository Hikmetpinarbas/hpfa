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


def test_family_views_and_claim_share_one_bounded_root_group():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())

    assert result["status"] == "PASS"
    summary = result["summary"]
    assert summary["bounded_lineage_group_count"] == 1
    assert summary["lineage_group_count_is_admitted_independent_support_count"] is False
    assert summary["lineage_can_increase_existing_independent_support"] is False
    assert summary["lineage_can_authorize_emit"] is False
    assert summary["current_topology"] == (
        "DIVERGENCE_TO_SAFE_FINDING_THEN_PUZZLE_AND_CLAIM_SIBLING_PROJECTIONS"
    )

    findings = result["puzzle_payload"]["puzzle_findings"]
    assert len({row["derived_lineage"]["lineage_group_id"] for row in findings}) == 1
    assert all(row["derived_lineage"]["root_refs"] == ["fsbd_root_1"] for row in findings)
    assert findings[1]["family_view_shares_source_lineage_root"] is True
    assert findings[2]["family_view_shares_source_lineage_root"] is True

    claim = result["claim_payload"]["analyst_output_contracts"][0]
    assert claim["derived_lineage"]["root_refs"] == ["fsbd_root_1"]
    assert claim["puzzle_sibling_is_claim_parent"] is False
    assert sorted(claim["puzzle_sibling_refs"]) == sorted(row["puzzle_finding_id"] for row in findings)
    assert claim["professional_emit_allowed"] is False


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


def test_root_scope_is_explicitly_not_absolute_evidence_root():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())
    summary = result["summary"]
    assert summary["root_is_absolute_observation_or_evidence_root"] is False
    for row in result["sequence_payload"]["first_supported_branch_divergence_candidates"]:
        assert row["derived_lineage"]["root_is_absolute_observation_or_evidence_root"] is False
        assert row["derived_lineage"]["root_is_current_tracked_derived_chain_root"] is True


def test_binding_preserves_truth_locks_and_never_creates_evidence():
    result = bind_derived_lineage(_sequence_payload(), _puzzle_payload(), _claim_payload())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["summary"]["lineage_creates_new_evidence"] is False
    assert result["summary"]["lineage_can_strengthen_claim_ceiling"] is False
