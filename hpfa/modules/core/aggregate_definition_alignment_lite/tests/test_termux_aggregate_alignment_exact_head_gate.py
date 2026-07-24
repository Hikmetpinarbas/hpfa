from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_aggregate_definition_alignment_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_aggregate_definition_alignment_v1.sh"


def test_runner_requires_exact_head_runtime_authority_and_flat_output():
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "expected_head_missing_or_invalid" in source
    assert '[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]]' in source
    assert '[[ "$ACTIVE_RESOLVED" == "$EXPECTED_RESOLVED" ]]' in source
    assert "nested_phone_output_directory_rejected" in source
    assert "/sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA" in source


def test_bootstrap_uses_fast_forward_and_exports_exact_head():
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "reset --hard" not in source
    assert 'git -C "$REPO" merge --ff-only "origin/$BRANCH"' in source
    assert '[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]]' in source
    assert 'HPFA_EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"' in source
    assert "export HPFA_REPO HPFA_ACTIVE_MATCH HPFA_EXPECTED_ACTIVE_MATCH" in source


def test_runner_requires_upstream_outputs_and_never_claims_release():
    source = RUNNER.read_text(encoding="utf-8")
    assert "xlsx_surface_audit_lite_v1.json" in source
    assert "provider_label_value_semantics_lite_v1.json" in source
    assert "--metric-config-dir" in source
    assert "canonical_event_count=UNKNOWN" in source
    assert "production_release=false" in source


def test_runner_separates_execution_evidence_from_definition_clearance():
    source = RUNNER.read_text(encoding="utf-8")
    assert 'python - "$OUTPUT" "$ACTIVE_RESOLVED" "$EXPECTED_RESOLVED" "$RUN_RC"' in source
    assert 'payload["active_match_execution_completed"]' in source
    assert 'payload["definition_alignment_cleared"]' in source
    assert 'payload["downstream_gate_open"]' in source
    assert '"ACTIVE_MATCH_EXECUTION_COMPLETED"' in source
    assert '"DEFINITION_ALIGNMENT_REVIEW_REQUIRED"' in source


def test_no_sample_match_identity_leak_in_scripts():
    text = (
        RUNNER.read_text(encoding="utf-8")
        + BOOTSTRAP.read_text(encoding="utf-8")
    ).casefold()
    for forbidden in ("fenerbahce", "galatasaray", "gornik", "19721253"):
        assert forbidden not in text
