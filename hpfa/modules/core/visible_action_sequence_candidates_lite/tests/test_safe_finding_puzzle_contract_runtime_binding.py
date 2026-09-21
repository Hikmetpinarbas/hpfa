from __future__ import annotations

import json
from pathlib import Path

import safe_finding_admission_current_v1 as runtime


def test_safe_finding_runtime_materializes_puzzle_contract_without_fusion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    sequence_path.write_text(
        json.dumps({
            "comparable_outcome_counterevidence_status": "PASS",
            "safe_finding_handoff_candidates": [
                {"safe_finding_handoff_candidate_id": "sfh_runtime"}
            ],
            "safe_finding_handoff_candidate_count": 1,
            "safe_finding_handoff_professional_emit_allowed": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )

    def fake_admission(payload):
        assert payload["safe_finding_handoff_candidate_count"] == 1
        return {
            "status": "PASS",
            "safe_finding_admission_decisions": [
                {
                    "source_safe_finding_handoff_ref": "sfh_runtime",
                    "decision": "DOWNGRADE",
                    "claim_output_allowed": False,
                    "claim_ceiling": "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY",
                }
            ],
            "safe_finding_admission_decision_count": 1,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": [],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    def fake_challenge_adapter(source, base, challenge, process_variant):
        assert source["canonical_event_count"] == "UNKNOWN"
        assert challenge is None
        assert process_variant is None
        return dict(base)

    def fake_puzzle_contract(source, admission):
        assert source["safe_finding_handoff_candidate_count"] == 1
        assert admission["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
        return {
            "module_id": "puzzle_finding_contract_adapter_v1",
            "status": "PASS",
            "puzzle_finding_contract_version": "PUZZLE_FINDING_V1",
            "puzzle_findings": [
                {
                    "puzzle_finding_id": "pf_sfh_runtime",
                    "puzzle_id": "P6_PROCESS_VARIANT_DIVERGENCE",
                    "finding_status": "DOWNGRADE",
                    "claim_output_allowed": False,
                    "canonical_event_count": "UNKNOWN",
                    "true_action_count": "UNKNOWN",
                    "production_release": False,
                }
            ],
            "puzzle_finding_count": 1,
            "puzzle_finding_status_counts": {"DOWNGRADE": 1},
            "bound_puzzle_ids": ["P6_PROCESS_VARIANT_DIVERGENCE"],
            "creates_new_evidence": False,
            "creates_new_finding": False,
            "cross_mechanism_fusion_performed": False,
            "mechanism_candidate_emitted": False,
            "hard_block_hits": [],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    monkeypatch.setattr(runtime, "build_safe_finding_admission", fake_admission)
    monkeypatch.setattr(runtime, "apply_variant_feature_challenge_to_admission", fake_challenge_adapter)
    monkeypatch.setattr(runtime, "build_puzzle_finding_contract", fake_puzzle_contract)

    result = runtime.runtime_write_outputs(sequence_path, tmp_path)
    puzzle_path = tmp_path / runtime.PUZZLE_FINDING_NAME
    safe_finding_path = tmp_path / runtime.OUTPUT_NAME

    assert puzzle_path.is_file()
    assert safe_finding_path.is_file()
    puzzle = json.loads(puzzle_path.read_text(encoding="utf-8"))
    safe_finding = json.loads(safe_finding_path.read_text(encoding="utf-8"))

    assert puzzle["status"] == "PASS"
    assert puzzle["puzzle_finding_count"] == 1
    assert puzzle["bound_puzzle_ids"] == ["P6_PROCESS_VARIANT_DIVERGENCE"]
    assert result["puzzle_finding_contract_status"] == "PASS"
    assert result["puzzle_finding_count"] == 1
    assert result["puzzle_finding_bound_puzzle_ids"] == ["P6_PROCESS_VARIANT_DIVERGENCE"]
    assert result["puzzle_finding_contract_creates_new_evidence"] is False
    assert result["puzzle_finding_contract_creates_new_finding"] is False
    assert result["cross_mechanism_fusion_performed"] is False
    assert result["mechanism_candidate_emitted"] is False
    assert safe_finding["puzzle_finding_contract_status"] == "PASS"
    assert safe_finding["puzzle_finding_count"] == 1
    assert safe_finding["canonical_event_count"] == "UNKNOWN"
    assert safe_finding["true_action_count"] == "UNKNOWN"
    assert safe_finding["production_release"] is False


def test_context_decomposition_distinguishes_rich_context_from_branch_completeness():
    source = {
        "process_comparison_context_consumed": True,
        "process_comparison_context_state_counts": {
            "MATCHED_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT": 8,
            "UNKNOWN_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT_REVIEW_REQUIRED": 2,
        },
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_a",
                "evidence_sufficiency": {
                    "dimensions": {
                        "context_coverage": {
                            "state": "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY"
                        }
                    }
                },
            },
            {
                "safe_finding_handoff_candidate_id": "sfh_b",
                "evidence_sufficiency": {
                    "dimensions": {
                        "context_coverage": {
                            "state": "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY"
                        }
                    }
                },
            },
        ],
    }
    admission = {
        "safe_finding_admission_decisions": [
            {"source_safe_finding_handoff_ref": "sfh_a"},
            {"source_safe_finding_handoff_ref": "sfh_b"},
        ]
    }
    rich = {
        "game_state_context": {"status": "PASS"},
        "loss_next_opponent_process_context": {"status": "PASS"},
    }
    result = runtime._context_coverage_decomposition(source, admission, rich)
    assert result["rich_descriptive_context_available"] is True
    assert result["provider_reviewed_process_comparison_context_consumed"] is True
    assert result["branch_comparison_context_state_counts"] == {
        "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY": 2
    }
    assert result["rich_descriptive_context_resolves_branch_comparison_completeness"] is False
    assert result["context_blocker_scope"] == (
        "BRANCH_COMPARISON_CONTEXT_COMPLETENESS_NOT_GLOBAL_CONTEXT_ABSENCE"
    )
    assert result["can_change_safe_finding_decision"] is False
    assert result["can_authorize_emit"] is False
