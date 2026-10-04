from __future__ import annotations

import json
from pathlib import Path

import analyst_output_claim_admission_current_v1 as runner


def _sequence() -> dict:
    return {
        "first_supported_branch_divergence_candidates": [
            {
                "first_supported_branch_divergence_id": "fsbd_1",
                "branch_profiles": [
                    {"neighbor_supporting_action_occurrence_candidate_ids": ["occ_1"]}
                ],
            }
        ],
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "source_first_supported_branch_divergence_ref": "fsbd_1",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _puzzle() -> dict:
    return {
        "puzzle_findings": [
            {
                "puzzle_finding_id": "pf_1",
                "source_safe_finding_handoff_ref": "sfh_1",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _claim() -> dict:
    return {
        "status": "PASS",
        "analyst_output_contracts": [
            {
                "analyst_output_contract_id": "claim_1",
                "source_safe_finding_handoff_ref": "sfh_1",
                "professional_emit_allowed": False,
                "claim_scope": "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            }
        ],
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_current_claim_runtime_binds_occurrence_lineage_before_render(tmp_path: Path) -> None:
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    puzzle_path = tmp_path / runner.PUZZLE_FINDING_NAME
    sequence = _sequence()
    sequence_path.write_text(json.dumps(sequence), encoding="utf-8")
    puzzle_path.write_text(json.dumps(_puzzle()), encoding="utf-8")

    bound_sequence, bound_claim = runner._bind_current_lineage(
        sequence_path,
        sequence,
        puzzle_path,
        _claim(),
    )

    assert bound_claim["derived_lineage_runtime_binding_consumed"] is True
    assert bound_claim["derived_lineage_runtime_binding_status"] == "PASS"
    assert bound_claim["derived_lineage_binding_creates_new_evidence"] is False
    assert bound_claim["derived_lineage_binding_can_authorize_emit"] is False
    row = bound_claim["analyst_output_contracts"][0]
    assert row["derived_lineage"]["root_refs"] == ["occ_1"]
    assert row["professional_emit_allowed"] is False
    assert bound_sequence["derived_lineage_runtime_binding_consumed"] is True

    persisted_sequence = json.loads(sequence_path.read_text(encoding="utf-8"))
    persisted_puzzle = json.loads(puzzle_path.read_text(encoding="utf-8"))
    assert persisted_sequence["derived_lineage_runtime_binding"]["bounded_occurrence_ancestor_count"] == 1
    assert persisted_puzzle["puzzle_findings"][0]["derived_lineage"]["root_refs"] == ["occ_1"]


def test_unresolved_occurrence_ancestry_lowers_claim_before_render(tmp_path: Path) -> None:
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    puzzle_path = tmp_path / runner.PUZZLE_FINDING_NAME
    sequence = _sequence()
    sequence["first_supported_branch_divergence_candidates"][0]["branch_profiles"] = []
    sequence_path.write_text(json.dumps(sequence), encoding="utf-8")
    puzzle_path.write_text(json.dumps(_puzzle()), encoding="utf-8")

    _, bound_claim = runner._bind_current_lineage(
        sequence_path,
        sequence,
        puzzle_path,
        _claim(),
    )

    assert bound_claim["status"] == "REVIEW_REQUIRED"
    assert bound_claim["derived_lineage_runtime_binding_status"] == "REVIEW_REQUIRED"
    assert "derived_lineage_runtime_binding_review_required" in bound_claim["review_hits"]
    row = bound_claim["analyst_output_contracts"][0]
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == "NO_CLAIM_OUTPUT"
    assert row["derived_lineage"]["status"] == "REVIEW_REQUIRED"
