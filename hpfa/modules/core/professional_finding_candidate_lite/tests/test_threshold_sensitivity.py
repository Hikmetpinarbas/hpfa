from hpfa.modules.core.professional_finding_candidate_lite.src.threshold_sensitivity import (
    attach_threshold_sensitivity,
)


def _payload(repeat_count: int) -> dict:
    return {
        "module_id": "professional_finding_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "professional_finding_candidates": [
            {
                "professional_finding_candidate_id": "pfc_test",
                "support": {"visible_repeat_count_candidate": repeat_count},
                "finding_challenge_packet": {
                    "evaluated_falsifier_families": [],
                    "pending_falsifier_families": ["THRESHOLD_SENSITIVITY", "FAILED_TRACE_SUPPORT"],
                },
                "alternative_explanations": [
                    {"type": "THRESHOLD_SENSITIVITY", "state": "NOT_EVALUATED_V1"}
                ],
                "uncertainty": {},
            }
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_output_allowed_count": 0,
        "professional_finding_emitted_count": 0,
    }


def test_repeat_two_is_sensitive_to_stricter_thresholds() -> None:
    out = attach_threshold_sensitivity(_payload(2))
    row = out["professional_finding_candidates"][0]
    sensitivity = row["finding_challenge_packet"]["threshold_sensitivity"]
    assert sensitivity["state_candidate"] == "SENSITIVE_TO_STRICTER_REPEAT_THRESHOLD"
    assert sensitivity["thresholds_are_calibrated"] is False
    assert "THRESHOLD_SENSITIVITY" not in row["finding_challenge_packet"]["pending_falsifier_families"]
    assert out["claim_output_allowed_count"] == 0
    assert out["production_release"] is False


def test_repeat_four_survives_tested_repeat_gate_grid_without_becoming_truth() -> None:
    out = attach_threshold_sensitivity(_payload(4))
    row = out["professional_finding_candidates"][0]
    sensitivity = row["finding_challenge_packet"]["threshold_sensitivity"]
    assert sensitivity["state_candidate"] == "SURVIVES_ALL_TESTED_REPEAT_THRESHOLDS"
    assert sensitivity["survival_proves_stable_pattern"] is False
    assert row["claim_output_allowed"] is False
    assert row["professional_finding_emitted"] is False


def test_upstream_fail_closed_remains_fail_closed() -> None:
    payload = _payload(4)
    payload["status"] = "FAIL_CLOSED"
    payload["hard_block_hits"] = ["upstream_failure"]
    out = attach_threshold_sensitivity(payload)
    assert out["status"] == "FAIL_CLOSED"
    assert out["threshold_sensitivity_status"] == "FAIL_CLOSED"
    assert out["claim_output_allowed_count"] == 0
    assert out["production_release"] is False
