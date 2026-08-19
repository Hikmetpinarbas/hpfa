from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_aggregate_definition_alignment_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_aggregate_definition_alignment_v1.sh"


def test_phone_runner_is_one_zip_no_pytest_single_pass():
    text = RUNNER.read_text(encoding="utf-8")
    assert "HPFA_181_ACTIVE_MATCH_" in text
    assert "HPFA_181_ZIP_CONTENT_MANIFEST.json" in text
    assert "python -m pytest" not in text
    assert text.count("python multiformat_file_inventory.py") == 1
    assert "nested_phone_output_directory_rejected" in text
    assert 'phone_handoff_mode\":\"ONE_ZIP_ONLY\"' in text


def test_runner_removes_stale_181_bundles_before_current_publish():
    text = RUNNER.read_text(encoding="utf-8")
    cleanup = 'rm -f "$OUT"/HPFA_181_ACTIVE_MATCH_*.zip "$OUT"/.HPFA_181_ACTIVE_MATCH_*.zip.partial'
    assert cleanup in text
    assert text.index(cleanup) < text.index('ZIP="$OUT/HPFA_181_ACTIVE_MATCH_')


def test_runner_enforces_exact_branch_and_head():
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"' in text
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in text
    assert "execution_identity_mismatch" in text


def test_runner_preserves_source_role_and_claim_boundaries():
    text = RUNNER.read_text(encoding="utf-8")
    assert '"xlsx_row_is_event_identity":False' in text
    assert '"csv_xml_candidate_linkage_is_physical_event_identity":False' in text
    assert '"measurement_invariance_truth":False' in text
    assert '"comparison_allowed":False' in text
    assert '"canonical_event_count":"UNKNOWN"' in text


def test_runner_persists_runtime_state_into_main_alignment_json():
    text = RUNNER.read_text(encoding="utf-8")
    assert "align.update({" in text
    assert '"active_match_evidence_pass":execution_completed' in text
    assert '"definition_alignment_cleared":definition_cleared' in text
    assert '"downstream_gate_open":downstream_gate_open' in text
    assert '(root/"aggregate_definition_alignment_lite_v1.json").write_text' in text


def test_bootstrap_uses_clean_current_181_work_branch_without_checkout_mutation():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'BRANCH="work/reconstruct-181-research-hardened-v1"' in text
    assert "clone --no-tags --no-recurse-submodules --single-branch --branch" in text
    assert "merge --ff-only" not in text
    assert "reset --hard" not in text
    assert "git -C \"$REPO\" fetch" not in text
    assert "git -C \"$REPO\" switch" not in text


def test_bootstrap_isolates_git_and_python_environment_before_evidence_run():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "env -i" in text
    assert 'SYSTEM_PATH="/data/data/com.termux/files/usr/bin:/system/bin"' in text
    assert 'PATH="$SYSTEM_PATH"' in text
    assert '${PATH:-' not in text
    assert text.count("GIT_CONFIG_GLOBAL=/dev/null") >= 2
    assert text.count("GIT_CONFIG_SYSTEM=/dev/null") >= 2
    assert text.count("GIT_CONFIG_NOSYSTEM=1") >= 2
    assert "GIT_TERMINAL_PROMPT=0" in text
    assert "core.hooksPath=/dev/null" in text
    assert "http.sslVerify=true" in text
    assert "protocol.ext.allow=never" in text
    assert "PYTHONNOUSERSITE=1" in text
    assert "--ignored=matching" in text
    assert "product_repo_origin_transport_or_identity_rejected" in text
    assert "remote_head_mismatch" in text


def test_bootstrap_rejects_ssh_transport_and_user_ssh_config_surface():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "https://github.com/hikmetpinarbas/hpfa" in text.casefold()
    assert "git@github.com:hikmetpinarbas/hpfa" not in text.casefold()
    assert "ssh://git@github.com/hikmetpinarbas/hpfa" not in text.casefold()
    assert "GIT_SSH_COMMAND" not in text
    assert "core.sshCommand" not in text


def test_no_sample_match_identity_leak_in_operator_scripts():
    text = (RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")).casefold()
    for forbidden in ("sturm graz", "heart of midlothian", "australia 2-0 turkey", "13.06.2026"):
        assert forbidden not in text
