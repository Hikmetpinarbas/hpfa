from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from pipeline_stage_provenance_envelope import build_stage_envelope, canonical_payload_sha256


def stage_payload(module_id="base_event_label_semantic_classifier_lite_v1"):
    return {
        "module_id": module_id,
        "decision_state": "REVIEW_REQUIRED_IDENTITY_GAPS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_exact_stage_module_and_claim_boundary_passes():
    source = {"evidence_atoms": [{"evidence_atom_id": "a1"}]}
    result = build_stage_envelope(
        source,
        stage_payload(),
        "base_event_label_semantic_classifier_lite_v1",
    )
    assert result["decision_state"] == "PASS_STAGE_PROVENANCE_ENVELOPE"
    assert result["input_sha256"] == canonical_payload_sha256(source)
    assert result["stage_payload_sha256"] == canonical_payload_sha256(stage_payload())
    assert result["provenance_blocker_count"] == 0


def test_input_payload_change_changes_hash():
    first = build_stage_envelope(
        {"evidence_atoms": [{"evidence_atom_id": "a1"}]},
        stage_payload(),
        "base_event_label_semantic_classifier_lite_v1",
    )
    second = build_stage_envelope(
        {"evidence_atoms": [{"evidence_atom_id": "a2"}]},
        stage_payload(),
        "base_event_label_semantic_classifier_lite_v1",
    )
    assert first["input_sha256"] != second["input_sha256"]


def test_stage_payload_change_changes_output_hash():
    first_stage = stage_payload()
    second_stage = stage_payload()
    second_stage["decision_state"] = "REVIEW_REQUIRED_SEMANTIC_CONFLICTS"
    first = build_stage_envelope({}, first_stage, first_stage["module_id"])
    second = build_stage_envelope({}, second_stage, second_stage["module_id"])
    assert first["stage_payload_sha256"] != second["stage_payload_sha256"]


def test_wrong_stage_module_is_blocked():
    result = build_stage_envelope(
        {},
        stage_payload("cross_role_reflection_resolver_lite_v1"),
        "base_event_label_semantic_classifier_lite_v1",
    )
    assert result["decision_state"] == "BLOCKED_STAGE_PROVENANCE_ENVELOPE"
    assert result["provenance_blockers"][0]["code"] == "STAGE_MODULE_ID_MISMATCH"


def test_claim_boundary_violation_is_blocked():
    payload = stage_payload()
    payload["canonical_event_count"] = 10
    payload["production_release"] = True
    result = build_stage_envelope({}, payload, payload["module_id"])
    codes = {blocker["code"] for blocker in result["provenance_blockers"]}
    assert "CANONICAL_EVENT_COUNT_CLAIM_VIOLATION" in codes
    assert "PRODUCTION_RELEASE_CLAIM_VIOLATION" in codes
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False
