from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hpfa_commercial_pilot_readiness_v1",
    ROOT / "tools" / "hpfa_commercial_pilot_readiness_v1.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _evidence(tmp_path: Path, head: str = "abc123") -> Path:
    evidence = tmp_path / "evidence"
    _write(evidence / "physical_acceptance.json", {
        "exact_head_sha": head,
        "execution_exit_code": 0,
        "runtime_status": "REVIEW_REQUIRED",
        "hard_block_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    })
    _write(evidence / "portability_acceptance.json", {
        "exact_head_sha": head,
        "required_profile_count": 3,
        "passed_profile_count": 3,
        "all_exit_zero": True,
        "production_release": False,
    })
    _write(evidence / "bundle_integrity.json", {
        "exact_head_sha": head,
        "bundle_status": "PASS",
        "deterministic_bundle": True,
        "forbidden_entry_count": 0,
        "raw_match_data_bundled": False,
        "raw_donor_bundled": False,
    })
    _write(evidence / "installation_smoke.json", {
        "exact_head_sha": head,
        "smoke_status": "PASS",
        "isolated_environment": True,
        "base_runtime_dependency_count": 0,
    })
    _write(evidence / "human_report_review.json", {
        "exact_head_sha": head,
        "claim_boundary_visible": True,
        "evidence_completeness_visible": True,
        "zero_emit_not_promoted": True,
        "review_status": "PASS",
    })
    _write(evidence / "red_team_review.json", {
        "exact_head_sha": head,
        "critical_blocker_count": 0,
        "review_status": "PASS",
    })
    return evidence


def test_controlled_commercial_pilot_can_pass_without_production_release(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    report = MOD.audit(ROOT, evidence, expected_head="abc123")
    assert report["decision"] == "CONTROLLED_COMMERCIAL_PILOT_READY"
    assert report["production_release"] is False
    assert report["public_index_upload_authorized"] is False
    assert report["commercial_distribution_authorized"] is True
    assert report["raw_match_data_bundling_allowed"] is False
    assert report["raw_donor_bundling_allowed"] is False
    assert report["exact_head_consistent"] is True
    assert report["critical_blocker_count"] == 0
    assert report["bundle_integrity_verified"] is True
    assert report["isolated_installation_smoke_verified"] is True


def test_head_mismatch_fails_closed(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path, head="old")
    report = MOD.audit(ROOT, evidence, expected_head="new")
    assert report["decision"] == "REVIEW_REQUIRED"
    assert report["exact_head_consistent"] is False
    assert "exact_head_mismatch" in report["blockers"]


def test_physical_failure_blocks_pilot(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads((evidence / "physical_acceptance.json").read_text())
    payload["execution_exit_code"] = 1
    _write(evidence / "physical_acceptance.json", payload)
    report = MOD.audit(ROOT, evidence, expected_head="abc123")
    assert report["decision"] == "REVIEW_REQUIRED"
    assert "physical_acceptance_failed" in report["blockers"]


def test_zero_emit_must_remain_non_promoted(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    payload = json.loads((evidence / "human_report_review.json").read_text())
    payload["zero_emit_not_promoted"] = False
    _write(evidence / "human_report_review.json", payload)
    report = MOD.audit(ROOT, evidence, expected_head="abc123")
    assert report["decision"] == "REVIEW_REQUIRED"
    assert "human_report_claim_boundary_failed" in report["blockers"]


def test_non_deterministic_or_unisolated_delivery_blocks_pilot(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    bundle = json.loads((evidence / "bundle_integrity.json").read_text())
    bundle["deterministic_bundle"] = False
    _write(evidence / "bundle_integrity.json", bundle)
    install = json.loads((evidence / "installation_smoke.json").read_text())
    install["isolated_environment"] = False
    _write(evidence / "installation_smoke.json", install)
    report = MOD.audit(ROOT, evidence, expected_head="abc123")
    assert report["decision"] == "REVIEW_REQUIRED"
    assert "bundle_integrity_failed" in report["blockers"]
    assert "installation_smoke_failed" in report["blockers"]
