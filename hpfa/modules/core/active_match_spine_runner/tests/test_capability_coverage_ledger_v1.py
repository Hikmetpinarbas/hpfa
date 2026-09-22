from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src.capability_coverage_ledger import (
    build_active_match_capability_coverage,
    write_active_match_capability_coverage,
)


def _module(root: Path, group: str, name: str, module_id: str | None) -> None:
    src = root / "hpfa" / "modules" / group / name / "src"
    src.mkdir(parents=True, exist_ok=True)
    text = "VALUE = 1\n" if module_id is None else f'MODULE_ID = "{module_id}"\n'
    (src / f"{name}.py").write_text(text, encoding="utf-8")


def _governance(root: Path) -> None:
    path = root / "docs" / "governance" / "runtime_pack_v1" / "module_governance_matrix.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "module_id\tsource_role\truntime_dependency\tclaim_boundary\tprimary_outputs\trelease_evidence_required\tcurrent_status\n"
        "superseded_demo\tGITHUB_PRODUCT_REPO\tNone\tNone\tNone\tNone\tSUPERSEDED_CONTRACT\n",
        encoding="utf-8",
    )


def test_coverage_separates_execution_control_support_and_unwired(tmp_path: Path) -> None:
    _module(tmp_path, "core", "demo_feature", "demo_feature_v1")
    _module(tmp_path, "core", "active_match_spine_runner", "active_match_full_spine_runner_v1")
    _module(tmp_path, "core", "unwired_feature", "unwired_feature_v1")
    _module(tmp_path, "core", "superseded_demo", "superseded_demo_v1")
    _module(tmp_path, "support", "support_demo", "support_demo_v1")
    _module(tmp_path, "reporting", "no_runtime_id", None)
    _governance(tmp_path)

    output = tmp_path / "out"
    output.mkdir()
    current = output / "current.json"
    current.write_text(
        json.dumps({
            "module_id": "demo_feature_v1",
            "nested": {"module_id": "active_match_full_spine_runner_v1"},
        }),
        encoding="utf-8",
    )
    report = {
        "module_id": "active_match_full_spine_runner_v1",
        "current_invocation_artifacts": [str(current)],
    }

    coverage = build_active_match_capability_coverage(
        product_root=tmp_path,
        output_root=output,
        full_spine_result=report,
    )
    by_name = {row["capability_family"]: row for row in coverage["capabilities"]}

    assert coverage["module_family_count"] == 6
    assert by_name["demo_feature"]["coverage_state"] == "EXECUTED_CONTRIBUTED"
    assert by_name["active_match_spine_runner"]["coverage_state"] == "EXECUTED_CONTROL_ONLY"
    assert by_name["unwired_feature"]["coverage_state"] == "UNWIRED_CURRENT_CAPABILITY"
    assert by_name["superseded_demo"]["coverage_state"] == "SUPERSEDED_NOT_CURRENT"
    assert by_name["support_demo"]["coverage_state"] == "SUPPORT_ONLY_NOT_EVENT_TRUTH"
    assert by_name["no_runtime_id"]["coverage_state"] == "NOT_EVIDENCED_REQUIRES_REVIEW"
    assert coverage["status"] == "REVIEW_REQUIRED"
    assert coverage["canonical_event_count"] == "UNKNOWN"
    assert coverage["true_action_count"] == "UNKNOWN"
    assert coverage["production_release"] is False


def test_coverage_outputs_are_flat_and_current_run_scoped(tmp_path: Path) -> None:
    _module(tmp_path, "core", "demo_feature", "demo_feature_v1")
    _governance(tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    current = output / "demo.json"
    current.write_text(json.dumps({"module_id": "demo_feature_v1"}), encoding="utf-8")

    result = write_active_match_capability_coverage(
        product_root=tmp_path,
        output_root=output,
        full_spine_result={"current_invocation_artifacts": [str(current)]},
    )

    for raw in result["current_invocation_artifacts"]:
        path = Path(raw)
        assert path.parent == output
        assert path.is_file()
    payload = json.loads((output / "HPFA_ACTIVE_MATCH_CAPABILITY_COVERAGE.json").read_text(encoding="utf-8"))
    assert payload["proven_execution_family_count"] == 1


def test_no_sample_match_identity_leak() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "capability_coverage_ledger.py"
    text = path.read_text(encoding="utf-8").casefold()
    for forbidden in ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor"):
        assert forbidden not in text
