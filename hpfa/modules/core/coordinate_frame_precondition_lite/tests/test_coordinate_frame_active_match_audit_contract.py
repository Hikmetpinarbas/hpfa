from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
AUDIT = REPO_ROOT / "tools" / "coordinate_frame_precondition_active_match_audit_v1.py"
RUNNER = REPO_ROOT / "tools" / "run_active_match_coordinate_frame_precondition_v1.sh"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def run_audit(
    tmp_path: Path,
    *,
    status: str,
    progression_allowed: bool,
    run_rc: int,
    actual_authority: str = "/runtime/active_single_match/current",
    expected_authority: str = "/runtime/active_single_match/current",
) -> tuple[dict, dict, subprocess.CompletedProcess[str]]:
    output = tmp_path / "coordinate.json"
    rollup = tmp_path / "rollup.json"
    aggregate = tmp_path / "aggregate.json"
    dependency = tmp_path / "dependency.json"

    write_json(
        output,
        {
            "status": status,
            "module_status": status,
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": "msb_fixture",
            "coordinate_frame_candidate": (
                "TEAM_PERIOD_DIRECTION_MAP_CANDIDATE"
                if progression_allowed
                else "FRAME_UNRESOLVED"
            ),
            "expected_team_period_group_count": 4,
            "multi_anchor_pass_group_count": 4 if progression_allowed else 2,
            "multi_anchor_conflict_group_count": 0,
            "progression_metric_recheck_allowed": progression_allowed,
            "hard_block_hits": [],
            "review_hits": [] if status == "PASS" else ["fixture_review"],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        },
    )
    write_json(
        rollup,
        {
            "gates": [
                {
                    "gate_id": "G07",
                    "status": "REVIEW_REQUIRED",
                    "message": "Coordinate surface checked.",
                    "evidence": {"coordinate_missing_nucleus_count": 12},
                },
                {
                    "gate_id": "G16",
                    "status": "REVIEW_REQUIRED",
                    "message": "Aggregate derivation dependency checked.",
                    "evidence": {},
                },
            ]
        },
    )
    write_json(
        aggregate,
        {
            "status": "REVIEW_REQUIRED",
            "review_hits": [
                {
                    "code": "provider_definition_evidence_unresolved",
                    "detail": "PROVIDER_DEFINITION_REQUIRED",
                    "severity": "REVIEW_REQUIRED",
                },
                {
                    "code": "derivation_dependency_unresolved",
                    "detail": ["DERIVATION_DEPENDENCY_UNRESOLVED"],
                    "severity": "REVIEW_REQUIRED",
                },
            ],
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(AUDIT),
            "--output",
            str(output),
            "--runtime-authority",
            actual_authority,
            "--expected-runtime-authority",
            expected_authority,
            "--runtime-head",
            "a" * 40,
            "--run-rc",
            str(run_rc),
            "--rollup",
            str(rollup),
            "--aggregate-alignment",
            str(aggregate),
            "--dependency-audit-out",
            str(dependency),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return (
        json.loads(output.read_text(encoding="utf-8")),
        json.loads(dependency.read_text(encoding="utf-8")),
        completed,
    )


def test_review_required_active_match_execution_is_self_describing(tmp_path: Path) -> None:
    output, _, _ = run_audit(
        tmp_path,
        status="REVIEW_REQUIRED",
        progression_allowed=False,
        run_rc=1,
    )
    assert output["active_match_execution_completed"] is True
    assert output["active_match_evidence_pass"] is False
    assert output["runtime_evidence_status"] == "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
    assert output["runtime_code_head_sha"] == "a" * 40
    assert output["canonical_event_count"] == "UNKNOWN"
    assert output["production_release"] is False


def test_pass_requires_progression_recheck_admission_for_active_match_pass(tmp_path: Path) -> None:
    passed, _, _ = run_audit(
        tmp_path,
        status="PASS",
        progression_allowed=True,
        run_rc=0,
    )
    assert passed["runtime_evidence_status"] == "ACTIVE_MATCH_EVIDENCE_PASS"
    assert passed["active_match_evidence_pass"] is True

    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir()
    blocked, _, _ = run_audit(
        blocked_dir,
        status="PASS",
        progression_allowed=False,
        run_rc=0,
    )
    assert blocked["runtime_evidence_status"] == "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED"
    assert blocked["active_match_evidence_pass"] is False


def test_authority_mismatch_never_completes_active_match_evidence(tmp_path: Path) -> None:
    output, _, _ = run_audit(
        tmp_path,
        status="PASS",
        progression_allowed=True,
        run_rc=0,
        actual_authority="/wrong/runtime",
    )
    assert output["active_match_execution_completed"] is False
    assert output["active_match_evidence_pass"] is False
    assert output["runtime_evidence_status"] == "ACTIVE_MATCH_EXECUTION_NOT_COMPLETED"


def test_dependency_audit_preserves_exact_run_gates_without_elevating_truth(tmp_path: Path) -> None:
    _, dependency, completed = run_audit(
        tmp_path,
        status="REVIEW_REQUIRED",
        progression_allowed=False,
        run_rc=1,
    )
    assert dependency["g07_coordinate_surface_gate"]["evidence"] == {
        "coordinate_missing_nucleus_count": 12
    }
    assert dependency["g16_aggregate_derivation_gate"]["status"] == "REVIEW_REQUIRED"
    codes = {
        item["code"] for item in dependency["aggregate_definition_alignment_review_hits"]
    }
    assert codes == {
        "provider_definition_evidence_unresolved",
        "derivation_dependency_unresolved",
    }
    assert dependency["canonical_event_count"] == "UNKNOWN"
    assert dependency["production_release"] is False
    assert "does not override coordinate-frame admission" in dependency["interpretation_rule"]
    assert "g07_coordinate_surface_gate=" in completed.stdout
    assert "g16_aggregate_derivation_gate=" in completed.stdout


def test_runner_bundles_active_match_runtime_and_dependency_artifacts() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    for name in (
        "coordinate_frame_precondition_active_match_v1.txt",
        "coordinate_frame_precondition_runtime_audit_v1.txt",
        "coordinate_frame_precondition_dependency_audit_v1.json",
    ):
        assert name in text
    assert "coordinate_frame_precondition_active_match_audit_v1.py" in text
    assert "coordinate_frame_active_match_provenance_invalid" in text
    assert "g01_g18_data_quality_rollup_v1.json" in text
    assert "aggregate_definition_alignment_lite_v1.json" in text
    assert '"version": "1.2.0"' in text


def test_no_sample_match_identity_leak() -> None:
    combined = AUDIT.read_text(encoding="utf-8") + RUNNER.read_text(encoding="utf-8")
    forbidden = (
        "Galatasaray",
        "Fenerbahce",
        "Fenerbahçe",
        "Besiktas",
        "Beşiktaş",
        "match001",
    )
    assert not any(token in combined for token in forbidden)
