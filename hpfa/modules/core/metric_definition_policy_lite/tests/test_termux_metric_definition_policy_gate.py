from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_metric_definition_policy_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_metric_definition_policy_v1.sh"


def test_runner_requires_exact_execution_identity_and_runtime_authority():
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"' in source
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "execution_identity_mismatch" in source
    assert "*/runtime/active_single_match/current" in source
    assert "active_match_runtime_authority_mismatch" in source


def test_runner_uses_current_inventory_producer_and_no_nested_runner_or_pytest():
    source = RUNNER.read_text(encoding="utf-8")
    assert "multiformat_file_inventory.py" in source
    assert "--active-match-execution" in source
    assert "run_active_match_cross_format_reconciliation_v1.sh" not in source
    assert "python -m pytest" not in source
    assert "INVENTORY_AUTHORITY_PLUS_POLICY_ADMISSION" in source


def test_runner_is_one_zip_atomic_phone_handoff():
    source = RUNNER.read_text(encoding="utf-8")
    assert "HPFA_178_ACTIVE_MATCH_" in source
    assert "HPFA_178_ZIP_CONTENT_MANIFEST.json" in source
    assert '.zip.partial"' in source
    assert 'mv -f "$ZIP_TMP" "$ZIP"' in source
    assert 'trap \'rm -rf "$TMP_ROOT"; rm -f "$ZIP_TMP"\' EXIT' in source
    assert 'echo "ZIP=NOT_CREATED"' in source
    assert 'phone_handoff_mode":"ONE_ZIP_ONLY"' in source
    assert 'phone_runtime_pytest":False' in source


def test_runner_preserves_metric_claim_boundaries():
    source = RUNNER.read_text(encoding="utf-8")
    for token in [
        '"validated_metric_truth":False',
        '"construct_validity_truth":False',
        '"aggregate_equivalence_truth":False',
        '"exposure_authority_truth":False',
        '"metric_value_output_allowed":False',
        '"claim_output_allowed":False',
        '"canonical_event_count":"UNKNOWN"',
        '"production_release":False',
    ]:
        assert token in source


def test_bootstrap_tracks_only_current_178_work_branch_and_remote_head():
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'BRANCH="work/reconstruct-178-research-hardened-v1"' in source
    assert 'git -C "$REPO" fetch origin "$BRANCH"' in source
    assert 'git -C "$REPO" merge --ff-only "origin/$BRANCH"' in source
    assert '[[ "$ACTUAL_HEAD" == "$REMOTE_HEAD" ]]' in source
    assert 'HPFA_EXPECTED_BRANCH="$BRANCH"' in source
    assert 'run_active_match_metric_definition_policy_v1.sh' in source
    assert "reset --hard" not in source


def test_no_sample_match_identity_leak_in_178_operator_scripts():
    content = RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "Galatasaray", "2062", "6935", "77798"]
    assert not any(token in content for token in forbidden)
