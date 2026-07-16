from hpfa.modules.core.active_match_pipeline_manifest_lite.src.active_match_pipeline_manifest import (
    ENVELOPE_MODULE_ID,
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


def _fresh_envelope_chain(source):
    previous = _canonical_sha256(source)
    envelopes = []
    for module_id in REQUIRED_STAGES:
        stage_payload = {
            "module_id": module_id,
            "decision_state": "TEST_STAGE",
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }
        stage_sha256 = _canonical_sha256(stage_payload)
        envelopes.append({
            "module_id": ENVELOPE_MODULE_ID,
            "stage_module_id": module_id,
            "expected_stage_module_id": module_id,
            "input_sha256": previous,
            "stage_payload_sha256": stage_sha256,
            "stage_payload": stage_payload,
            "decision_state": "PASS_STAGE_PROVENANCE_ENVELOPE",
            "provenance_blockers": [],
            "provenance_blocker_count": 0,
            "identity_bound_event_count": 0,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        })
        previous = stage_sha256
    return envelopes


def test_explicit_legacy_mode_allows_fresh_raw_stage_chain():
    source = {"match_binding_id": "opaque-test-binding", "rows": [1, 2]}
    result = build_pipeline_manifest(
        RUNTIME_AUTHORITY,
        source,
        _fresh_chain(source),
        require_provenance_envelopes=False,
    )
    assert result["decision_state"] == "PASS_FRESH_ACTIVE_MATCH_PIPELINE_CHAIN"
    assert result["pipeline_chain_complete"] is True
    assert result["provenance_envelopes_required"] is False
    assert all(row["stage_status"] == "PASS_FRESH_CHAIN_LINK" for row in result["stage_chain"])
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_raw_stage_chain_is_blocked_by_default_for_active_match():
    source = {"match_binding_id": "opaque-test-binding", "rows": [1, 2]}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_chain(source))
    assert result["decision_state"] == "BLOCKED_STALE_OR_INCOMPLETE_PIPELINE_CHAIN"
    assert result["pipeline_chain_complete"] is False
    assert result["provenance_envelopes_required"] is True
    assert all(row["payload_mode"] == "RAW_STAGE_PAYLOAD" for row in result["stage_chain"])
    assert all("RAW_STAGE_PAYLOAD_NOT_ADMISSIBLE" in row["stage_failures"] for row in result["stage_chain"])


def test_exact_provenance_envelope_chain_passes_on_embedded_stage_hashes():
    source = {"match_binding_id": "opaque-envelope-binding", "rows": [1, 2, 3]}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_envelope_chain(source))
    assert result["decision_state"] == "PASS_FRESH_ACTIVE_MATCH_PIPELINE_CHAIN"
    assert result["pipeline_chain_complete"] is True
    assert result["provenance_envelopes_required"] is True
    assert all(row["payload_mode"] == "PROVENANCE_ENVELOPE" for row in result["stage_chain"])
    assert all(row["stage_status"] == "PASS_FRESH_CHAIN_LINK" for row in result["stage_chain"])


def test_old_intermediate_payload_is_blocked():
    source = {"match_binding_id": "current", "rows": [1]}
    stages = _fresh_chain(source)
    stages[2]["input_sha256"] = "0" * 64
    result = build_pipeline_manifest(
        RUNTIME_AUTHORITY,
        source,
        stages,
        require_provenance_envelopes=False,
    )
    assert result["decision_state"] == "BLOCKED_STALE_OR_INCOMPLETE_PIPELINE_CHAIN"
    assert any("STALE_OR_FOREIGN_STAGE_INPUT" in reason for reason in result["chain_failure_reasons"])


def test_tampered_embedded_stage_payload_is_blocked():
    source = {"match_binding_id": "current", "rows": [1]}
    stages = _fresh_envelope_chain(source)
    stages[1]["stage_payload"]["decision_state"] = "TAMPERED"
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, stages)
    assert result["pipeline_chain_complete"] is False
    assert any("ENVELOPE_STAGE_PAYLOAD_SHA256_MISMATCH" in reason for reason in result["chain_failure_reasons"])


def test_non_passing_envelope_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stages[0]["decision_state"] = "BLOCKED_STAGE_PROVENANCE_ENVELOPE"
    stages[0]["provenance_blocker_count"] = 1
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, stages)
    assert any("ENVELOPE_NOT_PASSING" in reason for reason in result["chain_failure_reasons"])
    assert any("ENVELOPE_HAS_PROVENANCE_BLOCKERS" in reason for reason in result["chain_failure_reasons"])


def test_missing_stage_is_blocked():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_envelope_chain(source)[:-1])
    assert result["pipeline_chain_complete"] is False
    assert any("MISSING_REQUIRED_STAGE" in reason for reason in result["chain_failure_reasons"])


def test_wrong_runtime_path_is_blocked_even_with_fresh_payloads():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest("/sdcard/Download/HPFA", source, _fresh_envelope_chain(source))
    assert "INVALID_RUNTIME_AUTHORITY" in result["chain_failure_reasons"]
    assert result["production_release"] is False


def test_reordered_stage_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stages[0]["stage_module_id"], stages[1]["stage_module_id"] = (
        stages[1]["stage_module_id"],
        stages[0]["stage_module_id"],
    )
    stages[0]["expected_stage_module_id"], stages[1]["expected_stage_module_id"] = (
        stages[1]["expected_stage_module_id"],
        stages[0]["expected_stage_module_id"],
    )
    stages[0]["stage_payload"]["module_id"], stages[1]["stage_payload"]["module_id"] = (
        stages[1]["stage_payload"]["module_id"],
        stages[0]["stage_payload"]["module_id"],
    )
    stages[0]["stage_payload_sha256"] = _canonical_sha256(stages[0]["stage_payload"])
    stages[1]["stage_payload_sha256"] = _canonical_sha256(stages[1]["stage_payload"])
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, stages)
    assert any("STAGE_ORDER_OR_MODULE_MISMATCH" in reason for reason in result["chain_failure_reasons"])
    assert "REQUIRED_STAGE_SEQUENCE_NOT_PROVEN" in result["chain_failure_reasons"]
