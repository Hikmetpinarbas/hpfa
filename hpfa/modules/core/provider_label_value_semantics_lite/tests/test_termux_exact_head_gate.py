from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
RUNNER = ROOT / "tools" / "run_active_match_provider_label_value_semantics_v1.sh"
BOOTSTRAP = ROOT / "tools" / "bootstrap_termux_provider_label_value_semantics_v1.sh"


def test_runner_requires_explicit_exact_head() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert 'EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:-}"' in source
    assert "expected_head_missing_or_invalid" in source
    assert '[[ "$ACTUAL_HEAD" == "$EXPECTED_HEAD" ]]' in source
    assert 'echo "expected_head_sha=$EXPECTED_HEAD"' in source


def test_bootstrap_binds_runner_to_fetched_head() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'git -C "$REPO" reset --hard "origin/$BRANCH"' in source
    assert 'ACTUAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"' in source
    assert 'HPFA_EXPECTED_HEAD="$ACTUAL_HEAD"' in source
    assert 'echo "expected_head_sha=$ACTUAL_HEAD"' in source


def test_no_sample_match_identity_leak_in_head_gate_scripts() -> None:
    content = RUNNER.read_text(encoding="utf-8") + BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in content for token in forbidden)
