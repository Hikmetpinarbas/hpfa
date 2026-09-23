from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
SCOPED = {
    "c1-foundation-final-snapshot-v1.yml",
    "c2-evidence-spine-final-snapshot-v1.yml",
    "c3-reconstruction-final-snapshot-v1.yml",
    "c4-intelligence-final-snapshot-v1.yml",
    "active-match-full-spine-v1.yml",
}


def _text(name: str) -> str:
    return (WF / name).read_text(encoding="utf-8")


def test_global_health_gate_remains_global() -> None:
    text = _text("full-repo-health-audit-v1.yml")
    trigger = text.split("permissions:", 1)[0]
    assert "pull_request:" in trigger
    assert "paths:" not in trigger
    assert "paths-ignore:" not in trigger


def test_layer_snapshots_and_runtime_gate_are_path_scoped() -> None:
    for name in SCOPED:
        text = _text(name)
        trigger = text.split("permissions:", 1)[0]
        assert "pull_request:" in trigger
        assert "paths:" in trigger
        assert f".github/workflows/{name}" in trigger
        assert "pyproject.toml" in trigger
        assert "requirements.txt" in trigger


def test_snapshot_scopes_own_their_layers() -> None:
    assert "provider_metric_dictionary_lite/**" in _text("c1-foundation-final-snapshot-v1.yml")
    assert "action_occurrence_admission_lite/**" in _text("c2-evidence-spine-final-snapshot-v1.yml")
    assert "visible_action_sequence_candidates_lite/**" in _text("c3-reconstruction-final-snapshot-v1.yml")
    assert "final_report_assembly_gate_lite/**" in _text("c4-intelligence-final-snapshot-v1.yml")
    active = _text("active-match-full-spine-v1.yml")
    assert "active_match_spine_runner/**" in active
    assert "provider_metric_dictionary_lite/**" in active
