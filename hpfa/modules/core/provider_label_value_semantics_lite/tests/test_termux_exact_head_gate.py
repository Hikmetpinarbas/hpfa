from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_provider_label_value_semantics_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_label_value_semantics_v1.sh"


def test_runner_requires_explicit_integration_identity() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:-}"' in source
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "expected_branch_required:set_HPFA_EXPECTED_BRANCH" in source
    assert "expected_head_required:set_HPFA_EXPECTED_HEAD" in source
    assert "execution_identity_mismatch" in source


def test_bootstrap_is_non_destructive_and_ff_only() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'BRANCH="integration/foundation-tranche-a-v1"' in source
    assert 'git -C "$REPO" merge --ff-only "origin/$BRANCH"' in source
    assert 'reset --hard' not in source
    assert 'HPFA_EXPECTED_BRANCH="$BRANCH"' in source
    assert 'HPFA_EXPECTED_HEAD="$EXPECTED_HEAD"' in source


def test_phone_runtime_is_single_pass_and_zip_only() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "python -m pytest" not in source
    assert "run_active_match_csv_surface_reader_v1.sh" not in source
    assert "run_active_match_xlsx_surface_reader_v1.sh" not in source
    assert "run_active_match_xml_surface_reader_v1.sh" not in source
    assert "HPFA_175_ACTIVE_MATCH_" in source
    assert "TERMUX_TMP" in (ROOT / "docs" / "governance" / "HPFA_DEVELOPMENT_CHECKPOINT_CURRENT.json").read_text(encoding="utf-8")


def test_no_sample_match_identity_leak_in_head_gate_scripts() -> None:
    content = RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "Sturm Graz", "Heart of Midlothian", "6935", "77798"]
    assert not any(token in content for token in forbidden)


def test_run_step_uses_subshell_so_step_exit_cannot_terminate_parent_runner() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    start = source.index("run_step(){")
    end = source.index("\n}\n", start) + 3
    block = source[start:end]
    assert '  (\n' in block
    assert '  ) >>"$LOG" 2>&1' in block
    assert '  {\n' not in block
    assert '    exit "$rc"' in block
