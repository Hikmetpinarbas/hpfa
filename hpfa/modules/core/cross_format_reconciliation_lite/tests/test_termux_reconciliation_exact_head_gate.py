from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_cross_format_reconciliation_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_cross_format_reconciliation_v1.sh"


def test_runner_requires_explicit_exact_head_and_runtime_authority() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "expected_head_missing_or_invalid" in source
    assert '[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]]' in source
    assert '[[ "$ACTIVE_RESOLVED" == "$EXPECTED_RESOLVED" ]]' in source
    assert "--expected-runtime-authority" in source
    assert 'echo "expected_head_sha=$EXPECTED_HEAD"' in source


def test_bootstrap_binds_runner_to_fetched_head() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'git -C "$REPO" reset --hard "origin/$BRANCH"' in source
    assert 'ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"' in source
    assert 'HPFA_EXPECTED_HEAD="$ACTUAL_HEAD"' in source
    assert 'export HPFA_REPO HPFA_ACTIVE_MATCH HPFA_PHONE_OUTPUT HPFA_EXPECTED_HEAD' in source
    assert '[[ "$HPFA_EXPECTED_HEAD" == "$ACTUAL_HEAD" ]]' in source
    assert 'bash "$REPO/tools/run_active_match_cross_format_reconciliation_v1.sh"' in source


def test_runner_integrates_field_and_label_semantics() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "provider_alias_field_semantics_lite.py" in source
    assert "provider_label_value_semantics_lite.py" in source
    assert "--field-semantics" in source
    assert "--label-semantics" in source
    assert "--xml-group-registry" in source


def test_no_sample_match_identity_leak_in_reconciliation_scripts() -> None:
    content = RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798", "Galatasaray"]
    assert not any(token in content for token in forbidden)
