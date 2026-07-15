from hpfa.modules.core.active_match_pipeline_manifest_lite.src.active_match_pipeline_manifest import (
    REQUIRED_STAGES,
    RUNTIME_AUTHORITY,
    _canonical_sha256,
    build_pipeline_manifest,
)


def _fresh_chain(source):
    previous = _canonical_sha256(source)
    stages = []
    for module_id in REQUIRED_STAGES:
        payload = {"module_id": module_id, "input_sha256": previous, "decision_state": "TEST"}
        stages.append(payload)
        previous = _canonical_sha256(payload)
    return stages


def test_exact_runtime_authority_and_fresh_stage_chain_passes():
    source = {"match_binding_id": "opaque-test-binding", "rows": [1, 2]}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_chain(source))
    assert result["decision_state"] == "PASS_FRESH_ACTIVE_MATCH_PIPELINE_CHAIN"
    assert result["pipeline_chain_complete"] is True
    assert all(row["stage_status"] == "PASS_FRESH_CHAIN_LINK" for row in result["stage_chain"])
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_old_intermediate_payload_is_blocked():
    source = {"match_binding_id": "current", "rows": [1]}
    stages = _fresh_chain(source)
    stages[2]["input_sha256"] = "0" * 64
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, stages)
    assert result["decision_state"] == "BLOCKED_STALE_OR_INCOMPLETE_PIPELINE_CHAIN"
    assert any("STALE_OR_FOREIGN_STAGE_INPUT" in reason for reason in result["chain_failure_reasons"])


def test_missing_stage_is_blocked():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_chain(source)[:-1])
    assert result["pipeline_chain_complete"] is False
    assert any("MISSING_REQUIRED_STAGE" in reason for reason in result["chain_failure_reasons"])


def test_wrong_runtime_path_is_blocked_even_with_fresh_payloads():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest("/sdcard/Download/HPFA", source, _fresh_chain(source))
    assert "INVALID_RUNTIME_AUTHORITY" in result["chain_failure_reasons"]
    assert result["production_release"] is False


def test_reordered_stage_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_chain(source)
    stages[0]["module_id"], stages[1]["module_id"] = stages[1]["module_id"], stages[0]["module_id"]
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, stages)
    assert any("STAGE_ORDER_OR_MODULE_MISMATCH" in reason for reason in result["chain_failure_reasons"])
    assert "REQUIRED_STAGE_SEQUENCE_NOT_PROVEN" in result["chain_failure_reasons"]
