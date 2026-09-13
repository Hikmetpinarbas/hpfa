import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import active_match_exact_head_run_v1 as runtime


def test_post_context_current_sequence_count_is_authoritative(tmp_path: Path) -> None:
    stale_sequence = {
        "safe_finding_handoff_candidate_count": 10,
        "safe_finding_handoff_candidates": [
            {"safe_finding_handoff_candidate_id": f"sfh_{i}", "safe_meaning": "VISIBLE_ONLY"}
            for i in range(10)
        ],
    }
    current_sequence = {
        "safe_finding_handoff_candidate_count": 9,
        "safe_finding_handoff_candidates": [
            {"safe_finding_handoff_candidate_id": f"sfh_{i}", "safe_meaning": "VISIBLE_ONLY"}
            for i in range(9)
        ],
    }
    (tmp_path / runtime.SEQUENCE_JSON).write_text(json.dumps(current_sequence), encoding="utf-8")
    (tmp_path / runtime.SAFE_FINDING_ADMISSION_JSON).write_text("{}", encoding="utf-8")
    (tmp_path / runtime.ANALYST_OUTPUT_CLAIM_JSON).write_text("{}", encoding="utf-8")

    post_sequence = {
        "status": "PASS",
        "safe_finding_admission": {
            "status": "REVIEW_REQUIRED",
            "safe_finding_admission_decision_count": 9,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
        "analyst_output_claim": {
            "status": "REVIEW_REQUIRED",
            "analyst_output_contract_count": 9,
            "safe_finding_admission_consumed": True,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
    }

    assert runtime._post_sequence_admission_ready(
        out_dir=tmp_path,
        sequence=stale_sequence,
        post_sequence=post_sequence,
    ) is True


def test_user_output_gate_uses_current_post_context_handoffs(tmp_path: Path) -> None:
    stale_sequence = {
        "safe_finding_handoff_candidates": [
            {"safe_finding_handoff_candidate_id": "withdrawn", "safe_meaning": "STALE"},
            {"safe_finding_handoff_candidate_id": "kept", "safe_meaning": "CURRENT"},
        ],
    }
    current_sequence = {
        "safe_finding_handoff_candidates": [
            {"safe_finding_handoff_candidate_id": "kept", "safe_meaning": "CURRENT"},
        ],
    }
    (tmp_path / runtime.SEQUENCE_JSON).write_text(json.dumps(current_sequence), encoding="utf-8")
    post_sequence = {
        "status": "PASS",
        "safe_finding_admission": {
            "safe_finding_admission_decisions": [
                {
                    "decision": "EMIT",
                    "claim_output_allowed": True,
                    "source_safe_finding_handoff_ref": "kept",
                }
            ],
            "professional_finding_emitted_count": 1,
        },
        "analyst_output_claim": {
            "analyst_output_contracts": [
                {
                    "professional_emit_allowed": True,
                    "safe_finding_admission_decision": "EMIT",
                    "source_safe_finding_handoff_ref": "kept",
                }
            ],
            "professional_emit_allowed_count": 1,
        },
    }
    full_spine = {
        "engineering_evidence": {"current_c4_producers_reused": True},
        "current_invocation_artifacts": [],
    }
    result = runtime._admission_gated_full_spine_for_user_outputs(
        out_dir=tmp_path,
        full_spine=full_spine,
        sequence=stale_sequence,
        post_sequence=post_sequence,
    )
    assert result["status"] == "PASS"
    assert result["admitted_professional_finding_refs"] == ["kept"]
    assert "withdrawn" not in json.dumps(result)
