from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
RUNNER = REPO_ROOT / "tools" / "run_active_match_coordinate_frame_precondition_v1.sh"


def runner_text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_runner_refreshes_current_head_upstream_spine() -> None:
    text = runner_text()
    assert "run_active_match_context_slicer_v1.sh" in text
    assert 'HPFA_EXPECTED_BRANCH="$EXPECTED_BRANCH"' in text
    assert 'HPFA_EXPECTED_HEAD="$EXPECTED_HEAD"' in text
    assert "selected_event_consequence_surface_lite.py" not in text
    assert "CONTEXT_SPINE_ACTIVE_MATCH_OUTPUT_PRESERVED" in text
    assert "selected_event_active_match_provenance_invalid" in text
    assert "provider_label_output_missing_after_upstream_refresh" in text


def test_runner_always_emits_flat_failure_diagnostic_bundle() -> None:
    text = runner_text()
    assert "coordinate_frame_precondition_failure_bundle_v1.zip" in text
    assert "coordinate_frame_precondition_operator_state_v1.txt" in text
    assert "coordinate_frame_precondition_failure_inventory_v1.txt" in text
    assert "failure_bundle=%s" in text
    assert "/sdcard/Download/HPFA" in text
    assert "nested_phone_output_directory_rejected" in text


def test_success_bundle_contains_current_run_upstream_lineage() -> None:
    text = runner_text()
    required = (
        "provider_label_value_semantics_lite_v1.json",
        "semantic_role_action_bundle_candidates_lite_v1.json",
        "selected_action_consequence_surface_lite_v1.json",
        "selected_event_consequence_surface_lite_v1.json",
        "coordinate_frame_precondition_lite_v1.json",
    )
    for name in required:
        assert name in text
    assert "bundle_required_output_not_current_run" in text
    assert "runtime_code_head_sha" in text
    assert "canonical_event_count" in text
    assert "production_release" in text


def test_runner_does_not_call_legacy_branch_locked_provider_runner() -> None:
    text = runner_text()
    assert "run_active_match_provider_label_value_semantics_v1.sh" not in text
    assert 'EXPECTED_BRANCH="provider-label-value-semantics-v1"' not in text


def test_runner_preserves_selected_event_active_match_provenance() -> None:
    text = runner_text()
    assert 'payload.get("runtime_authority") != expected_authority' in text
    assert 'payload.get("runtime_code_head_sha") != expected_head' in text
    assert 'payload.get("active_match_execution_completed") is not True' in text
    assert '"ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"' in text
    assert "coordinate_frame_precondition_selected_event_refresh_v1.txt" not in text
