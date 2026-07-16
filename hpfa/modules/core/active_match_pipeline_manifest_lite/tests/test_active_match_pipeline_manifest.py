from hpfa.modules.core.active_match_pipeline_manifest_lite.src.active_match_pipeline_manifest import (
    ENVELOPE_MODULE_ID,
    REQUIRED_STAGES,
    RUNTIME_AUTHORITY,
    _canonical_sha256,
    build_pipeline_manifest,
)

CODE_HEAD_SHA = "5972606cc333162322ca7c6fc31ee584a36784e3"
OTHER_HEAD_SHA = "be772f3bf55f90443e3279b0e41581cf3731ef09"


def _fresh_chain(source):
    previous = _canonical_sha256(source)
    stages = []
    for module_id in REQUIRED_STAGES:
        payload = {"module_id": module_id, "input_sha256": previous, "decision_state": "TEST"}
        stages.append(payload)
        previous = _canonical_sha256(payload)
    return stages


def _fresh_envelope_chain(source, code_head_sha=CODE_HEAD_SHA):
    previous = _canonical_sha256(source)
    envelopes = []
    for module_id in REQUIRED_STAGES:
        stage_payload = {
            "module_id": module_id,
            "decision_state": "TEST_STAGE",
            "runtime_code_head_sha": code_head_sha,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }
        stage_sha256 = _canonical_sha256(stage_payload)
        envelopes.append({
            "module_id": ENVELOPE_MODULE_ID,
            "stage_module_id": module_id,
            "expected_stage_module_id": module_id,
            "runtime_code_head_sha": code_head_sha,
            "stage_runtime_code_head_sha": code_head_sha,
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


def _manifest(source, stages, **kwargs):
    return build_pipeline_manifest(
        RUNTIME_AUTHORITY,
        source,
        stages,
        expected_runtime_code_head_sha=CODE_HEAD_SHA,
        **kwargs,
    )


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


def test_raw_stage_chain_is_blocked_by_default_for_active_match():
    source = {"match_binding_id": "opaque-test-binding", "rows": [1, 2]}
    result = _manifest(source, _fresh_chain(source))
    assert result["pipeline_chain_complete"] is False
    assert all("RAW_STAGE_PAYLOAD_NOT_ADMISSIBLE" in row["stage_failures"] for row in result["stage_chain"])


def test_exact_provenance_envelope_chain_passes_on_one_code_head():
    source = {"match_binding_id": "opaque-envelope-binding", "rows": [1, 2, 3]}
    result = _manifest(source, _fresh_envelope_chain(source))
    assert result["decision_state"] == "PASS_FRESH_ACTIVE_MATCH_PIPELINE_CHAIN"
    assert result["pipeline_chain_complete"] is True
    assert result["expected_runtime_code_head_sha"] == CODE_HEAD_SHA
    assert all(row["runtime_code_head_sha"] == CODE_HEAD_SHA for row in result["stage_chain"])


def test_missing_expected_runtime_code_head_is_blocked():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest(RUNTIME_AUTHORITY, source, _fresh_envelope_chain(source))
    assert "MISSING_EXPECTED_RUNTIME_CODE_HEAD_SHA" in result["chain_failure_reasons"]
    assert result["pipeline_chain_complete"] is False


def test_mixed_or_stale_code_head_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stages[2]["runtime_code_head_sha"] = OTHER_HEAD_SHA
    result = _manifest(source, stages)
    assert any("RUNTIME_CODE_HEAD_SHA_MISMATCH" in reason for reason in result["chain_failure_reasons"])
    assert result["stage_chain"][2]["stage_status"] == "BLOCKED_CHAIN_LINK"


def test_relabeled_stage_payload_code_head_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stage_payload = stages[1]["stage_payload"]
    stage_payload["runtime_code_head_sha"] = OTHER_HEAD_SHA
    stages[1]["stage_payload_sha256"] = _canonical_sha256(stage_payload)
    stages[1]["stage_runtime_code_head_sha"] = OTHER_HEAD_SHA
    result = _manifest(source, stages)
    assert any("RELABELLED_STAGE_RUNTIME_CODE_HEAD_SHA" in reason for reason in result["chain_failure_reasons"])
    assert result["stage_chain"][1]["stage_status"] == "BLOCKED_CHAIN_LINK"


def test_missing_embedded_stage_code_head_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    del stages[0]["stage_payload"]["runtime_code_head_sha"]
    stages[0]["stage_payload_sha256"] = _canonical_sha256(stages[0]["stage_payload"])
    stages[0]["stage_runtime_code_head_sha"] = "MISSING"
    result = _manifest(source, stages)
    assert any("EMBEDDED_STAGE_RUNTIME_CODE_HEAD_SHA_MISSING" in reason for reason in result["chain_failure_reasons"])


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
    assert any("STALE_OR_FOREIGN_STAGE_INPUT" in reason for reason in result["chain_failure_reasons"])


def test_tampered_embedded_stage_payload_is_blocked():
    source = {"match_binding_id": "current", "rows": [1]}
    stages = _fresh_envelope_chain(source)
    stages[1]["stage_payload"]["decision_state"] = "TAMPERED"
    result = _manifest(source, stages)
    assert any("ENVELOPE_STAGE_PAYLOAD_SHA256_MISMATCH" in reason for reason in result["chain_failure_reasons"])


def test_non_passing_envelope_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stages[0]["decision_state"] = "BLOCKED_STAGE_PROVENANCE_ENVELOPE"
    stages[0]["provenance_blocker_count"] = 1
    result = _manifest(source, stages)
    assert any("ENVELOPE_NOT_PASSING" in reason for reason in result["chain_failure_reasons"])
    assert any("ENVELOPE_HAS_PROVENANCE_BLOCKERS" in reason for reason in result["chain_failure_reasons"])


def test_missing_stage_is_blocked():
    source = {"match_binding_id": "current"}
    result = _manifest(source, _fresh_envelope_chain(source)[:-1])
    assert any("MISSING_REQUIRED_STAGE" in reason for reason in result["chain_failure_reasons"])


def test_wrong_runtime_path_is_blocked_even_with_fresh_payloads():
    source = {"match_binding_id": "current"}
    result = build_pipeline_manifest(
        "/sdcard/Download/HPFA",
        source,
        _fresh_envelope_chain(source),
        expected_runtime_code_head_sha=CODE_HEAD_SHA,
    )
    assert "INVALID_RUNTIME_AUTHORITY" in result["chain_failure_reasons"]


def test_reordered_stage_is_blocked():
    source = {"match_binding_id": "current"}
    stages = _fresh_envelope_chain(source)
    stages[0]["stage_module_id"], stages[1]["stage_module_id"] = stages[1]["stage_module_id"], stages[0]["stage_module_id"]
    stages[0]["expected_stage_module_id"], stages[1]["expected_stage_module_id"] = stages[1]["expected_stage_module_id"], stages[0]["expected_stage_module_id"]
    stages[0]["stage_payload"]["module_id"], stages[1]["stage_payload"]["module_id"] = stages[1]["stage_payload"]["module_id"], stages[0]["stage_payload"]["module_id"]
    stages[0]["stage_payload_sha256"] = _canonical_sha256(stages[0]["stage_payload"])
    stages[1]["stage_payload_sha256"] = _canonical_sha256(stages[1]["stage_payload"])
    result = _manifest(source, stages)
    assert any("STAGE_ORDER_OR_MODULE_MISMATCH" in reason for reason in result["chain_failure_reasons"])
    assert "REQUIRED_STAGE_SEQUENCE_NOT_PROVEN" in result["chain_failure_reasons"]