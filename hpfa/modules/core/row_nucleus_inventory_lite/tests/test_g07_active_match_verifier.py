from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
VERIFIER = REPO_ROOT / "tools" / "verify_g07_coordinate_eligibility_active_match_v1.py"
HEAD = "a" * 40
AUTHORITY = "/runtime/active_single_match/current"


def payload(*, required_missing: bool = False) -> dict:
    admin = {
        "semantic_role_candidates": ["PERIOD_OR_META"],
        "downstream_eligibility_candidates": ["ADMIN_ONLY"],
        "pos_x_candidate": None,
        "pos_y_candidate": None,
    }
    nuclei = [admin]
    required_count = 0
    if required_missing:
        nuclei.append(
            {
                "semantic_role_candidates": ["ACTION_ANCHOR"],
                "downstream_eligibility_candidates": ["ACTION_BUNDLE_CANDIDATE"],
                "pos_x_candidate": None,
                "pos_y_candidate": "34",
            }
        )
        required_count = 1
    total = 1 + required_count
    g07_status = "REVIEW_REQUIRED" if required_count else "PASS"
    return {
        "runtime_code_head_sha": HEAD,
        "runtime_authority": AUTHORITY,
        "active_match_execution_completed": True,
        "runtime_evidence_status": "ACTIVE_MATCH_EXECUTION_COMPLETED_REVIEW_REQUIRED",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "row_nuclei": nuclei,
        "coordinate_missing_nucleus_count": total,
        "coordinate_missing_exempt_nucleus_count": 1,
        "coordinate_missing_required_nucleus_count": required_count,
        "g01_g18_rollup": {
            "status": "REVIEW_REQUIRED" if required_count else "PASS",
            "gates": [
                {
                    "gate_id": "G07",
                    "status": g07_status,
                    "evidence": {
                        "coordinate_missing_nucleus_count": total,
                        "coordinate_missing_exempt_nucleus_count": 1,
                        "coordinate_missing_required_nucleus_count": required_count,
                    },
                },
                {"gate_id": "G16", "status": "REVIEW_REQUIRED"},
            ],
        },
    }


def run(tmp_path: Path, data: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "row.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--row-nucleus",
            str(path),
            "--expected-head",
            HEAD,
            "--expected-authority",
            AUTHORITY,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_admin_only_coordinate_exemption(tmp_path: Path) -> None:
    completed = run(tmp_path, payload())
    assert completed.returncode == 0
    assert "ACTIVE_MATCH_G07_ELIGIBILITY_EVIDENCE_VERIFIED" in completed.stdout
    assert "coordinate_missing_exempt_nucleus_count=1" in completed.stdout
    assert "coordinate_missing_required_nucleus_count=0" in completed.stdout


def test_accepts_real_required_missing_coordinate_when_g07_reviews(tmp_path: Path) -> None:
    completed = run(tmp_path, payload(required_missing=True))
    assert completed.returncode == 0
    assert "coordinate_missing_required_nucleus_count=1" in completed.stdout
    assert "g07_status=REVIEW_REQUIRED" in completed.stdout


def test_rejects_false_g07_pass_for_required_missing_coordinate(tmp_path: Path) -> None:
    data = payload(required_missing=True)
    data["g01_g18_rollup"]["gates"][0]["status"] = "PASS"
    completed = run(tmp_path, data)
    assert completed.returncode == 1
    assert "g07_status_not_eligibility_consistent" in completed.stdout


def test_rejects_wrong_runtime_head(tmp_path: Path) -> None:
    data = payload()
    data["runtime_code_head_sha"] = "b" * 40
    completed = run(tmp_path, data)
    assert completed.returncode == 1
    assert "runtime_code_head_sha_mismatch" in completed.stdout


def test_no_sample_match_identity_leak() -> None:
    text = VERIFIER.read_text(encoding="utf-8")
    forbidden = (
        "Galatasaray",
        "Fenerbahce",
        "Fenerbahçe",
        "Besiktas",
        "Beşiktaş",
        "match001",
    )
    assert not any(token in text for token in forbidden)
