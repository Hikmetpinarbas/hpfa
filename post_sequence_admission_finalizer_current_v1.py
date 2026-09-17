from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import analyst_output_claim_admission_current_v1 as claim_runner
import safe_finding_admission_current_v1 as safe_finding_runner

SEQUENCE_JSON = "visible_action_sequence_candidates_lite_v1.json"
SAFE_FINDING_ADMISSION_JSON = "safe_finding_admission_projection_v1.json"
ANALYST_OUTPUT_CLAIM_JSON = "analyst_output_claim_contract_projection_v1.json"


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def finalize_post_sequence_admission(out_dir: str | Path) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve()
    sequence_path = output / SEQUENCE_JSON
    if not sequence_path.is_file():
        return {
            "status": "FAIL_CLOSED",
            "reason": "sequence_artifact_missing",
            "safe_finding_admission": {},
            "analyst_output_claim": {},
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    sequence = _load(sequence_path)
    expected_count = int(sequence.get("safe_finding_handoff_candidate_count") or 0)
    if not sequence:
        return {
            "status": "FAIL_CLOSED",
            "reason": "sequence_artifact_invalid",
            "safe_finding_admission": {},
            "analyst_output_claim": {},
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    admission = safe_finding_runner.runtime_write_outputs(sequence_path, output)
    if admission.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "reason": "safe_finding_admission_fail_closed",
            "safe_finding_admission": admission,
            "analyst_output_claim": {},
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    admission_path = output / SAFE_FINDING_ADMISSION_JSON
    claim = claim_runner.runtime_write_outputs(sequence_path, admission_path, output)
    if claim.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "reason": "analyst_output_claim_fail_closed",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    admission_count = int(admission.get("safe_finding_admission_decision_count") or 0)
    claim_count = int(claim.get("analyst_output_contract_count") or 0)
    consumed = claim.get("safe_finding_admission_consumed") is True
    if admission_count != expected_count or claim_count != expected_count or not consumed:
        return {
            "status": "FAIL_CLOSED",
            "reason": "post_sequence_admission_count_or_consumption_mismatch",
            "expected_handoff_count": expected_count,
            "admission_count": admission_count,
            "claim_count": claim_count,
            "safe_finding_admission_consumed": consumed,
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    return {
        "status": "PASS",
        "reason": None,
        "expected_handoff_count": expected_count,
        "admission_count": admission_count,
        "claim_count": claim_count,
        "safe_finding_admission_consumed": True,
        "safe_finding_admission": admission,
        "analyst_output_claim": claim,
        "current_invocation_artifacts": [str(admission_path), str(output / ANALYST_OUTPUT_CLAIM_JSON)],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
