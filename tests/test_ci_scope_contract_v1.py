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


def test_global_health_keeps_fail_local_isolation_with_bounded_parallelism() -> None:
    text = _text("full-repo-health-audit-v1.yml")
    assert "python repo_fail_local_product_test_audit_v1.py" in text
    assert "--max-workers 2" in text


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

EVENT_AWARE_CONCURRENCY = {
    "analyst-episode-locator-semantic-v1.yml",
    "content-source-role-resolver-lite-v1.yml",
    "context-row-nucleus-rebinding-v1.yml",
    "episode-feature-vector-v1.yml",
    "event-window-partial-order-hardening-v1.yml",
    "metric-definition-policy-lite-v1.yml",
    "provider-metric-dictionary-lite-v1.yml",
    "provider-time-semantic-admission-v1.yml",
    "reconstruction-intelligence-packet-adapter-v1.yml",
    "row-nucleus-inventory-lite-v1.yml",
    "temporal-episode-signature-v1.yml",
    "triangulated-event-reflection-resolver-lite-v1.yml",
    "triplex-source-alignment-adapter-lite-v1.yml",
}


def test_all_pr_workflows_define_concurrency() -> None:
    workflows = sorted(WF.glob("*.yml"))
    assert workflows
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        trigger_and_policy = text.split("jobs:", 1)[0]
        assert "pull_request:" in trigger_and_policy, path.name
        assert "concurrency:" in trigger_and_policy, path.name
        assert "cancel-in-progress:" in trigger_and_policy, path.name


def test_new_concurrency_rehabilitation_only_auto_cancels_pr_runs() -> None:
    expected_group = (
        "group: hpfa-${{ github.workflow_ref }}-${{ github.event_name }}-"
        "${{ github.event_name == 'pull_request' && github.event.pull_request.number || github.run_id }}"
    )
    expected_cancel = "cancel-in-progress: ${{ github.event_name == 'pull_request' }}"
    for name in EVENT_AWARE_CONCURRENCY:
        text = _text(name)
        trigger_and_policy = text.split("jobs:", 1)[0]
        lines = [line.strip() for line in trigger_and_policy.splitlines()]
        assert lines.count("concurrency:") == 1, name
        assert lines.count(expected_group) == 1, name
        assert lines.count(expected_cancel) == 1, name
