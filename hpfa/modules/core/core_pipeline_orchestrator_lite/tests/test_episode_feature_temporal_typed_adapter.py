from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from episode_feature_temporal_typed_adapter import validate_episode_feature_temporal_chain


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_payload(module_id: str, claim_ceiling: str, *, status: str = "PASS") -> dict:
    return {
        "module_id": module_id,
        "status": status,
        "decision": "READY",
        "claim_ceiling": claim_ceiling,
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
    }


def fixture_dir(tmp_path: Path) -> Path:
    write_json(
        tmp_path / "context_action_semantics_rebind_lite_v1.json",
        base_payload(
            "context_action_semantics_rebind_lite_v1",
            "REVIEWED_PROVIDER_ACTION_SEMANTICS_CANDIDATE_ONLY",
        ),
    )
    write_json(
        tmp_path / "analyst_episode_locator_lite_v1.json",
        base_payload(
            "analyst_episode_locator_lite_v1",
            "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY",
        ),
    )
    write_json(
        tmp_path / "episode_feature_vector_lite_v1.json",
        base_payload(
            "episode_feature_vector_lite_v1",
            "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY",
        ),
    )
    write_json(
        tmp_path / "temporal_episode_signature_lite_v1.json",
        base_payload(
            "temporal_episode_signature_lite_v1",
            "TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY",
        ),
    )
    return tmp_path


def test_real_artifact_adapter_builds_two_stage_typed_ledger(tmp_path: Path) -> None:
    root = fixture_dir(tmp_path)
    result = validate_episode_feature_temporal_chain(root, run_id="pilot")
    assert result["status"] == "SMOKE_PASS"
    assert result["stage_count_executed"] == 2
    assert [row["owner_id"] for row in result["stage_ledger"]] == [
        "episode_feature_vector_lite_v1",
        "temporal_episode_signature_lite_v1",
    ]
    assert result["stage_ledger"][0]["context_input_artifact_ids"]["semantics"]


def test_review_state_is_preserved_without_hiding_later_contract_validation(tmp_path: Path) -> None:
    root = fixture_dir(tmp_path)
    episode = json.loads((root / "analyst_episode_locator_lite_v1.json").read_text(encoding="utf-8"))
    episode["status"] = "REVIEW_REQUIRED"
    episode["review_hits"] = ["episode_review"]
    write_json(root / "analyst_episode_locator_lite_v1.json", episode)
    result = validate_episode_feature_temporal_chain(root, run_id="pilot_review")
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["stage_count_executed"] == 2


def test_wrong_producer_claim_ceiling_is_rejected_before_orchestration(tmp_path: Path) -> None:
    root = fixture_dir(tmp_path)
    feature = json.loads((root / "episode_feature_vector_lite_v1.json").read_text(encoding="utf-8"))
    feature["claim_ceiling"] = "TOO_WIDE"
    write_json(root / "episode_feature_vector_lite_v1.json", feature)
    try:
        validate_episode_feature_temporal_chain(root, run_id="pilot_bad_claim")
    except ValueError as exc:
        assert "claim_ceiling_mismatch:episode_feature_vector_lite_v1.json" in str(exc)
    else:
        raise AssertionError("claim ceiling drift was not rejected")
