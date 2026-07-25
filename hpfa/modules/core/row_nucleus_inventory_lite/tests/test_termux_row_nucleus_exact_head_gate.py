from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_row_nucleus_inventory_v1.sh"
RUNNER = ROOT / "tools" / "run_active_match_row_nucleus_inventory_v1.sh"


def test_bootstrap_exports_exact_remote_head() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'BRANCH="agent/row-nucleus-inventory-lite-v1"' in text
    assert 'git -C "$REPO" fetch origin "$BRANCH"' in text
    assert 'REMOTE_HEAD="$(git -C "$REPO" rev-parse "refs/remotes/origin/$BRANCH"' in text
    assert 'HPFA_EXPECTED_HEAD="${REQUESTED_EXPECTED_HEAD:-$REMOTE_HEAD}"' in text
    assert "export HPFA_REPO HPFA_ACTIVE_MATCH HPFA_EXPECTED_ACTIVE_MATCH HPFA_PHONE_OUTPUT HPFA_EXPECTED_HEAD" in text
    assert "reset --hard" not in text


def test_runner_requires_exact_branch_head_and_runtime_authority() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_BRANCH="agent/row-nucleus-inventory-lite-v1"' in text
    assert 'expected_head_missing_or_invalid' in text
    assert 'unexpected_head:$ACTUAL_HEAD expected:$EXPECTED_HEAD' in text
    assert 'active_match_runtime_authority_mismatch' in text
    assert '/sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA' in text
    assert 'nested_phone_output_directory_rejected' in text


def test_runner_refreshes_full_upstream_spine() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    for command in (
        "multiformat_file_inventory.py",
        "csv_surface_reader_lite.py",
        "xlsx_surface_reader_lite.py",
        "xml_surface_reader_lite.py",
        "provider_alias_field_semantics_lite.py",
        "provider_label_value_semantics_lite.py",
        "cross_format_reconciliation_lite.py",
        "aggregate_definition_alignment_lite.py",
        "row_nucleus_inventory_lite.py",
    ):
        assert command in text
    assert "provider_metric_dictionary_lite_v1.json" in text


def test_runner_keeps_release_and_claim_boundaries_closed() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text
    assert 'payload["release_status"] = "NOT_PRODUCTION"' in text
