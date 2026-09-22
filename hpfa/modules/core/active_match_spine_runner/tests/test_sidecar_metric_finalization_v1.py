import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import orphan_capability_sidecars as sidecars


def _base_report():
    return {
        "module_id": sidecars.MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "hard_block_hits": [],
        "review_hits": [
            "spatial_transition_candidate_review_required",
            "metric_governance_bridge_not_evaluated_deferred_until_rich_lane",
        ],
        "current_invocation_artifacts": [],
        "construct_path_blocked": False,
        "construct_path_block_reason": None,
    }


def test_metric_finalization_replaces_deferred_review_with_current_metric_review(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sidecars,
        "_run_metric_governance_sidecar",
        lambda *_a, **_k: {
            "status": "REVIEW_REQUIRED",
            "hard_block_hits": [],
            "review_hits": ["provider_metric_dictionary_review_required"],
            "current_invocation_artifacts": [],
        },
    )
    report = sidecars.finalize_metric_governance_sidecar(_base_report(), tmp_path, tmp_path)
    assert report["status"] == "REVIEW_REQUIRED"
    assert "spatial_transition_candidate_review_required" in report["review_hits"]
    assert "metric_governance_bridge_review_required" in report["review_hits"]
    assert "metric_governance_bridge_not_evaluated_deferred_until_rich_lane" not in report["review_hits"]


def test_metric_finalization_fails_closed_on_metric_hard_block(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sidecars,
        "_run_metric_governance_sidecar",
        lambda *_a, **_k: {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["synthetic_metric_contract_failure"],
            "review_hits": [],
            "current_invocation_artifacts": [],
        },
    )
    report = sidecars.finalize_metric_governance_sidecar(_base_report(), tmp_path, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["construct_path_blocked"] is True
    assert report["construct_path_block_reason"] == "synthetic_metric_contract_failure"
    assert "metric_governance_construct_path_blocked:synthetic_metric_contract_failure" in report["hard_block_hits"]


def test_metric_finalization_smoke_pass_when_no_other_debt(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sidecars,
        "_run_metric_governance_sidecar",
        lambda *_a, **_k: {
            "status": "SMOKE_PASS",
            "hard_block_hits": [],
            "review_hits": [],
            "current_invocation_artifacts": [],
        },
    )
    base = _base_report()
    base["review_hits"] = ["metric_governance_bridge_not_evaluated_deferred_until_rich_lane"]
    report = sidecars.finalize_metric_governance_sidecar(base, tmp_path, tmp_path)
    assert report["status"] == "SMOKE_PASS"
    assert report["review_hits"] == []
