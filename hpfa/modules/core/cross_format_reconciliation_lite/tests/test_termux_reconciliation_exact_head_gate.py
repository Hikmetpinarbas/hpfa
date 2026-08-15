from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_cross_format_reconciliation_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_cross_format_reconciliation_v1.sh"


def test_runner_requires_explicit_exact_execution_identity() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"' in source
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "expected_branch_required" in source
    assert "expected_head_required" in source
    assert "execution_identity_mismatch" in source
    assert "*/runtime/active_single_match/current" in source


def test_bootstrap_uses_current_integration_branch_and_exact_head() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'BRANCH="integration/foundation-tranche-a-v1"' in source
    assert "reset --hard" not in source
    assert 'git -C "$REPO" merge --ff-only "origin/$BRANCH"' in source
    assert 'ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"' in source
    assert '[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]]' in source
    assert '[[ "$ACTUAL_HEAD" == "$HPFA_EXPECTED_HEAD" ]]' in source
    assert 'HPFA_EXPECTED_BRANCH="$BRANCH"' in source
    assert 'bash "$REPO/tools/run_active_match_cross_format_reconciliation_v1.sh"' in source


def test_runner_is_one_zip_phone_handoff_without_pytest() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "python -m pytest" not in source
    assert "HPFA_177_ACTIVE_MATCH_" in source
    assert "HPFA_177_ZIP_CONTENT_MANIFEST.json" in source
    assert 'TMP_ROOT=' in source
    assert 'trap \'rm -rf "$TMP_ROOT"\' EXIT' in source
    assert "ONE_ZIP_ONLY" in source
    assert 'phone_runtime_pytest' in source
    assert 'single_pass_upstream_refresh' in source


def test_runner_step_exit_cannot_terminate_parent_runner() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    start = source.index("run_step(){")
    end = source.index("\n}\n", start) + 3
    block = source[start:end]
    assert '  (\n' in block
    assert '  ) >>"$LOG" 2>&1' in block
    assert '  {\n' not in block


def test_runner_propagates_postprocess_and_packaging_failures() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "record_post_step_failure(){" in source
    assert "POSTPROCESS_RC=$?" in source
    assert 'record_post_step_failure "$POSTPROCESS_RC" "evidence_postprocess"' in source
    assert "PACKAGING_RC=$?" in source
    assert 'record_post_step_failure "$PACKAGING_RC" "evidence_bundle_packaging"' in source
    assert 'rm -f "$ZIP"' in source
    assert 'echo "run_rc=$FINAL_RC"' in source
    assert 'echo "failed_step=$FAILED_STEP"' in source
    assert 'echo "ZIP=NOT_CREATED"' in source
    assert 'exit "$FINAL_RC"' in source


def test_runner_integrates_current_semantics_and_research_hardening() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "provider_alias_field_semantics_lite.py" in source
    assert "provider_label_value_semantics_lite.py" in source
    assert "cross_format_reconciliation_lite.py" in source
    assert "--field-semantics" in source
    assert "--label-semantics" in source
    assert "--xml-group-registry" in source
    assert "research_hardening_status" in source


def test_no_sample_match_identity_leak_in_reconciliation_scripts() -> None:
    content = RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "Galatasaray", "6935", "77798", "2062"]
    assert not any(token in content for token in forbidden)
