import json
from pathlib import Path

import active_match_spine_runner as runner


def _result() -> dict:
    return {
        "module_id": "active_match_full_spine_runner_v1",
        "status": "REVIEW_REQUIRED",
        "review_hits": [],
        "reciprocal_match_tomography_bridge": {
            "module_id": "reciprocal_full_spine_packet_bridge_v1",
            "status": "REVIEW_REQUIRED",
            "active_match_evidence_pass": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        },
        "reciprocal_match_tomography_bridge_status": "REVIEW_REQUIRED",
        "reciprocal_match_tomography_claim_output_allowed_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_post_bridge_augmentation_is_persisted_in_canonical_full_spine_artifacts(tmp_path: Path) -> None:
    json_path = tmp_path / runner.full_spine_module.OUTPUT_JSON
    txt_path = tmp_path / runner.full_spine_module.OUTPUT_TXT
    json_path.write_text(json.dumps({"status": "REVIEW_REQUIRED", "stale_pre_bridge": True}), encoding="utf-8")
    txt_path.write_text("HPFA ACTIVE_MATCH FULL SPINE V1\nstatus=REVIEW_REQUIRED\n", encoding="utf-8")

    report = runner._persist_augmented_full_spine_artifacts(_result(), tmp_path)

    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert "stale_pre_bridge" not in persisted
    assert persisted["reciprocal_match_tomography_bridge_status"] == "REVIEW_REQUIRED"
    assert persisted["reciprocal_match_tomography_claim_output_allowed_count"] == 0
    assert persisted["canonical_event_count"] == "UNKNOWN"
    assert persisted["true_action_count"] == "UNKNOWN"
    assert persisted["production_release"] is False
    assert report["reciprocal_match_tomography_artifact_persistence_status"] == "PERSISTED_IN_CANONICAL_FULL_SPINE_ARTIFACTS"

    text = txt_path.read_text(encoding="utf-8")
    assert "reciprocal_match_tomography_bridge_status=REVIEW_REQUIRED" in text
    assert "reciprocal_match_tomography_claim_output_allowed_count=0" in text
    assert "reciprocal_match_tomography_active_match_evidence_pass=false" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_missing_canonical_json_is_review_required_not_silently_persisted(tmp_path: Path) -> None:
    report = runner._persist_augmented_full_spine_artifacts(_result(), tmp_path)
    assert report["reciprocal_match_tomography_artifact_persistence_status"] == "REVIEW_REQUIRED_CANONICAL_JSON_MISSING"
    assert "canonical_full_spine_json_missing_after_bridge_augmentation" in report["review_hits"]
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
