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
        "primary_outputs\trelease_evidence_required\tcurrent_status\tauthority_scope\n"
    )
    _write(root / guard.GOVERNANCE_MATRIX, header + matrix_rows)


def _ids(report: dict) -> set[str]:
    return {row["capability_id"] for row in report["capabilities"]}


def test_historical_matrix_row_does_not_expand_current_capability_universe(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "historical_only_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SPEC_ONLY\tHISTORICAL_SNAPSHOT\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "1" * 40)

    report = guard.build_report(tmp_path)

    assert "historical_only_lite" not in _ids(report)


def test_current_discovery_seed_can_expand_current_capability_universe(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "current_seed_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SPEC_ONLY\tCURRENT_DISCOVERY_SEED\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "2" * 40)

    report = guard.build_report(tmp_path)

    assert "current_seed_lite" in _ids(report)


def test_historical_row_can_still_supply_supersession_metadata_for_discovered_contract(tmp_path, monkeypatch):
    _governance(
        tmp_path,
        "old_surface_lite\tGITHUB_PRODUCT_REPO\tNone\tX\tX\tX\t"
        "SUPERSEDED_BY_NEW_SURFACE_LITE\tHISTORICAL_SNAPSHOT\n",
    )
    _write(
        tmp_path / "docs/contracts/old_surface_lite_v1.md",
        "## Product Node\nold_surface_lite\n",
    )
    _write(
        tmp_path / "hpfa/modules/core/new_surface_lite/src/new_surface.py",
        "def run():\n    return 'new'\n",
    )
    monkeypatch.setattr(guard, "current_product_tree_sha", lambda _root: "3" * 40)

    report = guard.build_report(tmp_path)
    records = {row["capability_id"]: row for row in report["capabilities"]}

    assert records["old_surface_lite"]["superseded_by"] == "new_surface_lite"
    assert records["old_surface_lite"]["decision"] == "SUPERSEDED_CONTRACT"
