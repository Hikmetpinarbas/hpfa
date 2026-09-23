from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
MANIFEST = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "registry" / "information_reservoir_manifest_v1.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_has_unique_current_artifact_bindings() -> None:
    payload = load_manifest()
    bindings = [(row["owner_id"], row["artifact_name"]) for row in payload["artifacts"]]
    assert len(bindings) == len(set(bindings))


def test_manifest_stage_classes_are_declared() -> None:
    payload = load_manifest()
    declared = set(payload["stage_classes"])
    for row in payload["artifacts"]:
        for stage in str(row["stage_id"]).split("/"):
            base = stage if stage in declared else stage[:1]
            assert base in declared or stage.startswith(("M", "F", "T"))


def test_final_tanks_do_not_claim_production_release() -> None:
    payload = load_manifest()
    assert payload["production_release"] is False
    for row in payload["artifacts"]:
        if str(row["stage_id"]).startswith("T"):
            assert row.get("production_report_allowed") is not True
            assert "production" not in str(row["claim_ceiling"]).lower()


def test_taxonomy_does_not_claim_dedicated_runtime_engines() -> None:
    payload = load_manifest()
    note = payload["taxonomy_only"]["note"].lower()
    assert "does not assert a dedicated runtime engine" in note


def test_key_current_chain_claim_ceilings_are_preserved() -> None:
    payload = load_manifest()
    by_owner = {row["owner_id"]: row for row in payload["artifacts"]}
    assert by_owner["analyst_episode_locator_lite_v1"]["claim_ceiling"] == "ANALYST_EPISODE_NAVIGATION_CANDIDATE_ONLY"
    assert by_owner["episode_feature_vector_lite_v1"]["claim_ceiling"] == "EPISODE_VISIBLE_FEATURE_CANDIDATES_ONLY"
    assert by_owner["temporal_episode_signature_lite_v1"]["claim_ceiling"] == "TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY"
    assert by_owner["analyst_report_block_composer_lite_v1"]["claim_ceiling"] == "analyst_report_block_candidate_only"
    assert by_owner["report_output_contract_lite_v1"]["claim_ceiling"] == "report_output_contract_candidate_only"
    assert by_owner["final_report_assembly_gate_lite_v1"]["claim_ceiling"] == "final_report_assembly_candidate_only"
