import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "capability_closure_guard_lite" / "src"
sys.path.insert(0, str(SRC))

import capability_closure_guard as guard  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _governance(root: Path, matrix_rows: str) -> None:
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


def _ids(report: dict) -> set[str]:
    return {row["capability_id"] for row in report["capabilities"]}


def _skipped(report: dict) -> dict[str, str]:
    return {
        row["capability_id"]: row["reason"]
        for row in report.get("skipped_seed_only_candidates", [])
    }


def test_historical_looking_matrix_row_cannot_invent_current_capability(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "historical_only_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\tSPEC_ONLY\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "1" * 40)

    report = guard.build_report(tmp_path)

    assert "historical_only_lite" not in _ids(report)
    assert _skipped(report)["historical_only_lite"] == "seed_only_without_contract_or_implementation"


def test_current_looking_matrix_row_also_cannot_invent_current_capability(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "current_seed_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\tACTIVE_MATCH_EVIDENCE_PASS\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "2" * 40)

    report = guard.build_report(tmp_path)

    assert "current_seed_lite" not in _ids(report)
    assert _skipped(report)["current_seed_lite"] == "seed_only_without_contract_or_implementation"


def test_historical_supersession_hint_requires_current_successor_implementation(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "old_surface_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SUPERSEDED_BY_NEW_SURFACE_LITE\n",
    )
    _write(
        tmp_path / "docs/contracts/old_surface_lite_v1.md",
        "## Product Node\nold_surface_lite\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "3" * 40)

    without_successor = guard.build_report(tmp_path)
    without_records = {row["capability_id"]: row for row in without_successor["capabilities"]}
    assert without_records["old_surface_lite"]["superseded_by"] is None
    assert without_records["old_surface_lite"]["governance_status_used_as_truth"] is False
    assert without_records["old_surface_lite"]["decision"] == "ORPHAN_CONTRACT"

    _write(
        tmp_path / "hpfa/modules/core/new_surface_lite/src/new_surface.py",
        "def run():\n    return 'new'\n",
    )
    with_successor = guard.build_report(tmp_path)
    with_records = {row["capability_id"]: row for row in with_successor["capabilities"]}
    assert with_records["old_surface_lite"]["superseded_by"] == "new_surface_lite"
    assert with_records["old_surface_lite"]["decision"] == "SUPERSEDED_CONTRACT"
