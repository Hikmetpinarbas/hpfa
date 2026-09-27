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

MERGE_REF_TRUTH_WORKFLOWS = {
    "csv-surface-reader-lite-v1.yml",
    "multiformat-file-inventory-lite-v1.yml",
    "provider-alias-field-semantics-v1.yml",
    "row-nucleus-inventory-lite-v1.yml",
    "triangulated-event-reflection-resolver-lite-v1.yml",
    "triplex-source-alignment-adapter-lite-v1.yml",
    "xlsx-surface-reader-lite-v1.yml",
    "xml-surface-reader-lite-v1.yml",
}




def _top_level_mapping(text: str, key: str) -> dict[str, str]:
    lines = text.splitlines()
    marker = f"{key}:"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise AssertionError(f"missing_top_level_mapping:{key}") from exc
    result: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        if not line.startswith("  ") or ":" not in line.strip():
            continue
        child_key, value = line.strip().split(":", 1)
        result[child_key] = value.strip()
    return result


def _checkout_step(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "uses: actions/checkout@" not in line:
            continue
        start = index - 1 if index > 0 and lines[index - 1].lstrip().startswith("- name:") else index
        step_indent = len(lines[start]) - len(lines[start].lstrip())
        end = len(lines)
        for cursor in range(index + 1, len(lines)):
            stripped = lines[cursor].lstrip()
            indent = len(lines[cursor]) - len(stripped)
            if stripped.startswith("- ") and indent == step_indent:
                end = cursor
                break
        return "\n".join(lines[start:end])
    raise AssertionError("checkout_step_missing")


def _modeled_concurrency_group(
    workflow_ref: str, event_name: str, *, pr_number: int | None, run_id: int
) -> str:
    suffix = pr_number if event_name == "pull_request" else run_id
    if suffix is None:
        raise AssertionError("pull_request_requires_pr_number")
    return f"hpfa-{workflow_ref}-{event_name}-{suffix}"


def test_non_pr_trigger_workflows_do_not_cancel_push_or_manual_runs() -> None:
    expected_group = "hpfa-${{ github.workflow_ref }}-${{ github.event_name }}-${{ github.event_name == 'pull_request' && github.event.pull_request.number || github.run_id }}"
    expected_cancel = "${{ github.event_name == 'pull_request' }}"
    for path in sorted(WF.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        trigger_and_policy = text.split("jobs:", 1)[0]
        if "workflow_dispatch:" not in trigger_and_policy and "push:" not in trigger_and_policy:
            continue
        concurrency = _top_level_mapping(trigger_and_policy, "concurrency")
        assert concurrency == {
            "group": expected_group,
            "cancel-in-progress": expected_cancel,
        }, path.name


def test_merge_ref_workflows_make_ref_truth_explicit() -> None:
    observed = set()
    for path in sorted(WF.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        trigger = text.split("jobs:", 1)[0]
        if "pull_request:" not in trigger or "actions/checkout@" not in text:
            continue
        checkout = _checkout_step(text)
        if "ref:" not in checkout:
            observed.add(path.name)
    assert observed == MERGE_REF_TRUTH_WORKFLOWS
    for name in MERGE_REF_TRUTH_WORKFLOWS:
        text = _text(name)
        checkout = _checkout_step(text)
        assert "ref:" not in checkout, name
        assert "name: Verify checkout ref truth" in text
        assert "EXPECTED_EVENT_SHA: ${{ github.sha }}" in text
        assert 'source_ref_kind="PR_MERGE_REF"' in text
        assert 'source_ref_kind="EVENT_SHA"' in text
        assert 'actual_head="$(git rev-parse HEAD)"' in text
        assert 'test "$actual_head" = "$EXPECTED_EVENT_SHA"' in text


def test_full_repo_health_verifies_exact_pr_head_ref_truth() -> None:
    text = _text("full-repo-health-audit-v1.yml")
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert "name: Verify checkout ref truth" in text
    assert "EXPECTED_SOURCE_SHA: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert 'source_ref_kind="PR_HEAD"' in text
    assert 'source_ref_kind="EVENT_SHA"' in text
    assert 'actual_head="$(git rev-parse HEAD)"' in text
    assert 'test "$actual_head" = "$EXPECTED_SOURCE_SHA"' in text

def test_concurrency_group_semantics_keep_pr_stale_cancellation_without_non_pr_collision() -> None:
    workflow_a = "Hikmetpinarbas/hpfa/.github/workflows/a.yml@refs/heads/main"
    workflow_b = "Hikmetpinarbas/hpfa/.github/workflows/b.yml@refs/heads/main"
    pr_old = _modeled_concurrency_group(workflow_a, "pull_request", pr_number=364, run_id=1001)
    pr_new = _modeled_concurrency_group(workflow_a, "pull_request", pr_number=364, run_id=1002)
    assert pr_old == pr_new
    assert _modeled_concurrency_group(workflow_b, "pull_request", pr_number=364, run_id=1002) != pr_new
    manual_a = _modeled_concurrency_group(workflow_a, "workflow_dispatch", pr_number=None, run_id=2001)
    manual_b = _modeled_concurrency_group(workflow_a, "workflow_dispatch", pr_number=None, run_id=2002)
    push_a = _modeled_concurrency_group(workflow_a, "push", pr_number=None, run_id=3001)
    assert manual_a != manual_b
    assert push_a not in {manual_a, manual_b}
