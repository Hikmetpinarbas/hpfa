import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "capability_closure_guard_lite" / "src"
sys.path.insert(0, str(SRC))

import capability_closure_guard as guard  # noqa: E402


GOLDEN_EXPECTED = {
    "active_match_spine_runner": "ACTIVE_CONTRACT",
    "content_source_role_resolver_lite": "ACTIVE_CONTRACT",
    "canonical_ingest_surface_manifest": "ACTIVE_CONTRACT",
    "core_pipeline_orchestrator_lite": "TEST_ONLY_SURFACE",
    "support_report_concept_surface_gate_lite": "SUPERSEDED_CONTRACT",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _active_evidence(path: Path, tree_sha: str) -> Path:
    payload = {
        "evidence_kind": "ACTIVE_MATCH_RUNTIME_EVIDENCE",
        "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
        "product_tree_sha": tree_sha,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "active_match_spine_check": {
            "status": "PASS",
            "active_match_authority_validated": True,
            "runtime_surface_policy": {
                "executed_runtime_surfaces": [
                    "hpfa/modules/core/content_source_role_resolver_lite",
                    "hpfa/modules/core/canonical_ingest_surface_manifest",
                ]
            },
            "source_role_resolution": {"status": "PASS"},
            "surface_manifest": {"status": "PASS"},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _decision_map(report):
    return {
        record["capability_id"]: record["decision"]
        for record in report["capabilities"]
    }


def _minimal_governance(root: Path, matrix_rows: str = "") -> None:
    _write(
        root / guard.SOURCE_ROLE_REGISTRY,
        json.dumps(
            {
                "source_roles": [
                    {"role": "ACTIVE_MATCH_RUNTIME_AUTHORITY"},
                    {"role": "GITHUB_PRODUCT_REPO"},
                ]
            }
        ),
    )
    _write(
        root / guard.RELEASE_STATUS_NORMALIZER,
        json.dumps(
            {
                "statuses": [
                    {"status": "SMOKE_PASS"},
                    {"status": "ACTIVE_MATCH_EVIDENCE_PASS"},
                    {"status": "PRODUCTION_RELEASE"},
                    {"status": "RELEASE_CANDIDATE_NOT_PRODUCTION_BOUND"},
                ]
            }
        ),
    )
    header = (
        "module_id\tsource_role\truntime_dependency\tclaim_boundary\t"
        "primary_outputs\trelease_evidence_required\tcurrent_status\n"
    )
    _write(root / guard.GOVERNANCE_MATRIX, header + matrix_rows)


def test_current_repo_five_golden_cases_with_admitted_evidence_fixture(tmp_path):
    tree_sha = guard.current_product_tree_sha(ROOT)
    evidence_path = _active_evidence(tmp_path / "active_match_evidence.json", tree_sha)

    report = guard.build_report(
        ROOT,
        active_match_evidence_path=evidence_path,
    )
    decisions = _decision_map(report)

    assert {key: decisions[key] for key in GOLDEN_EXPECTED} == GOLDEN_EXPECTED
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_active_contract_is_impossible_without_active_match_evidence():
    report = guard.build_report(ROOT)
    decisions = _decision_map(report)

    for capability_id in (
        "active_match_spine_runner",
        "content_source_role_resolver_lite",
        "canonical_ingest_surface_manifest",
    ):
        assert decisions[capability_id] == "UNBOUND_IMPLEMENTATION"
        record = next(
            row for row in report["capabilities"]
            if row["capability_id"] == capability_id
        )
        assert record["evidence"]["active_match_evidence"] is False


def test_tests_ci_and_docs_do_not_become_non_test_consumers(tmp_path, monkeypatch):
    _minimal_governance(tmp_path)
    _write(
        tmp_path / "docs/contracts/sample_lite_v1.md",
        "## Product Node\nsample_lite\n",
    )
    _write(
        tmp_path / "hpfa/modules/core/sample_lite/src/sample_impl.py",
        "def run():\n    return 'ok'\n",
    )
    _write(
        tmp_path / "hpfa/modules/core/sample_lite/tests/test_sample.py",
        "import sample_impl\n",
    )
    _write(
        tmp_path / ".github/workflows/sample.yml",
        "run: python -c 'import sample_impl'\n",
    )
    _write(
        tmp_path / "docs/sample_consumer_claim.md",
        "import sample_impl\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "a" * 40)

    report = guard.build_report(tmp_path)
    record = next(row for row in report["capabilities"] if row["capability_id"] == "sample_lite")

    assert record["evidence"]["test"] is True
    assert record["evidence"]["non_test_consumer"] is False
    assert record["evidence"]["runtime_binding"] is False
    assert record["decision"] == "TEST_ONLY_SURFACE"


def test_static_superseded_hint_needs_current_successor_implementation(tmp_path, monkeypatch):
    _minimal_governance(
        tmp_path,
        "old_surface_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SUPERSEDED_BY_NEW_SURFACE_LITE\n",
    )
    _write(
        tmp_path / "docs/contracts/old_surface_lite_v1.md",
        "## Product Node\nold_surface_lite\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "b" * 40)

    report = guard.build_report(tmp_path)
    record = next(row for row in report["capabilities"] if row["capability_id"] == "old_surface_lite")

    assert record["superseded_by"] is None
    assert record["governance_status_used_as_truth"] is False
    assert record["decision"] == "ORPHAN_CONTRACT"


def test_current_successor_implementation_corrobates_superseded_contract(tmp_path, monkeypatch):
    _minimal_governance(
        tmp_path,
        "old_surface_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SUPERSEDED_BY_NEW_SURFACE_LITE\n",
    )
    _write(
        tmp_path / "docs/contracts/old_surface_lite_v1.md",
        "## Product Node\nold_surface_lite\n",
    )
    _write(
        tmp_path / "hpfa/modules/core/new_surface_lite/src/new_surface.py",
        "def run():\n    return 'new'\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "c" * 40)

    report = guard.build_report(tmp_path)
    record = next(row for row in report["capabilities"] if row["capability_id"] == "old_surface_lite")

    assert record["superseded_by"] == "new_surface_lite"
    assert record["decision"] == "SUPERSEDED_CONTRACT"


@pytest.mark.parametrize(
    "field,bad_value,error",
    [
        ("canonical_event_count", 8, "active_match_evidence_canonical_event_count_promoted"),
        ("true_action_count", 8, "active_match_evidence_true_action_count_promoted"),
        ("production_release", True, "active_match_evidence_production_release_promoted"),
    ],
)
def test_active_match_evidence_claim_promotions_fail_closed(
    tmp_path,
    monkeypatch,
    field,
    bad_value,
    error,
):
    _minimal_governance(tmp_path)
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "d" * 40)
    payload = {
        "evidence_kind": "ACTIVE_MATCH_RUNTIME_EVIDENCE",
        "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
        "product_tree_sha": "d" * 40,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "capabilities": {},
    }
    payload[field] = bad_value
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(guard.ClosureGuardError, match=error):
        guard.build_report(tmp_path, active_match_evidence_path=evidence)


def test_stale_active_match_evidence_tree_fails_closed(tmp_path, monkeypatch):
    _minimal_governance(tmp_path)
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "e" * 40)
    payload = {
        "evidence_kind": "ACTIVE_MATCH_RUNTIME_EVIDENCE",
        "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
        "product_tree_sha": "f" * 40,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "capabilities": {},
    }
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        guard.ClosureGuardError,
        match="active_match_evidence_product_tree_mismatch",
    ):
        guard.build_report(tmp_path, active_match_evidence_path=evidence)


def test_same_sha_reflection_is_collapsed_inside_one_capability(tmp_path, monkeypatch):
    _minimal_governance(tmp_path)
    _write(
        tmp_path / "docs/contracts/reflection_lite_v1.md",
        "## Product Node\nreflection_lite\n",
    )
    same = "VALUE = 1\n"
    _write(tmp_path / "hpfa/modules/core/reflection_lite/src/a.py", same)
    _write(tmp_path / "hpfa/modules/core/reflection_lite/src/b.py", same)
    _write(
        tmp_path / "hpfa/modules/core/reflection_lite/tests/test_reflection.py",
        "import a\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "1" * 40)

    report = guard.build_report(tmp_path)
    record = next(row for row in report["capabilities"] if row["capability_id"] == "reflection_lite")

    assert len(record["evidence_paths"]["implementation"]) == 1
    assert record["reflection_groups"] == [[
        "hpfa/modules/core/reflection_lite/src/a.py",
        "hpfa/modules/core/reflection_lite/src/b.py",
    ]]


def test_json_and_txt_outputs_are_deterministic(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    _minimal_governance(repo)
    _write(
        repo / "docs/contracts/sample_lite_v1.md",
        "## Product Node\nsample_lite\n",
    )
    _write(
        repo / "hpfa/modules/core/sample_lite/src/sample.py",
        "VALUE = 1\n",
    )
    _write(
        repo / "hpfa/modules/core/sample_lite/tests/test_sample.py",
        "import sample\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "2" * 40)
    out = tmp_path / "out"

    first = guard.write_report(repo, out)
    json_first = (out / "capability_closure_guard_lite_v1.json").read_text()
    txt_first = (out / "capability_closure_guard_lite_v1.txt").read_text()
    second = guard.write_report(repo, out)

    assert first == second
    assert json_first == (out / "capability_closure_guard_lite_v1.json").read_text()
    assert txt_first == (out / "capability_closure_guard_lite_v1.txt").read_text()
    assert second["canonical_event_count"] == "UNKNOWN"
    assert second["true_action_count"] == "UNKNOWN"
    assert second["production_release"] is False
