import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "context_action_semantics_rebind_lite" / "src"
sys.path.insert(0, str(SRC))

import context_action_semantics_rebind as rebind_module
from context_action_semantics_rebind import build_rebind


def _payloads() -> tuple[dict, dict]:
    nuclei = [
        {
            "row_nucleus_candidate_id": "rn_0",
            "source_role": "PLAYER",
            "status": "PASS",
            "resolved_visible_fields": {"action": "Lost balls", "code": "Lost balls"},
        },
        {
            "row_nucleus_candidate_id": "rn_1",
            "source_role": "PLAYER",
            "status": "PASS",
            "resolved_visible_fields": {"action": "Ball recoveries", "code": "Ball recoveries"},
        },
    ]
    contexts = [
        {
            "context_id": f"ctx_{idx}",
            "period": "1",
            "team_label": "team_candidate",
            "zone_candidate": "MIDDLE_THIRD",
            "channel_candidate": "CENTRAL_CHANNEL",
            "time_admission_status": "ADMITTED",
            "football_minute_candidate": 1,
            "_preserved_unmapped": {"row_nucleus_candidate_id": f"rn_{idx}"},
        }
        for idx in range(2)
    ]
    row = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "PASS",
        "row_nucleus_candidate_count": 2,
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    mvc = {
        "module_id": "minimum_viable_context_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_candidate_count": 2,
        "context_candidates": contexts,
        "time_admission_status": "ADMITTED",
        "context_occurrence_basis": "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT",
        "row_nucleus_context_binding": {
            "enabled": True,
            "reflection_inflation_prevented": True,
            "row_nucleus_candidate_count": 2,
        },
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return mvc, row


def test_known_lost_ball_and_recovery_rows_cannot_escape_reconciliation_by_losing_review_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mvc, row = _payloads()
    provider_module, registry = rebind_module.load_registry(ROOT)
    original = provider_module.classify_label

    class PatchedProvider:
        normalize_label = staticmethod(provider_module.normalize_label)

        @staticmethod
        def classify_label(label, **kwargs):
            result = dict(original(label, **kwargs))
            if label in {"Lost balls", "Ball recoveries"}:
                result.update({
                    "semantic_role_candidate": "ACTION_ANCHOR",
                    "action_family_candidate": "PASS",
                    "downstream_eligibility": "ACTION_CANDIDATE_ELIGIBLE",
                    "mapping_status": "TOKEN_FALLBACK_REVIEW_REQUIRED",
                    "review_status": "REVIEW_REQUIRED",
                })
            return result

    monkeypatch.setattr(rebind_module, "load_registry", lambda _root: (PatchedProvider, registry))
    result = build_rebind(mvc, row, repo_root=ROOT)
    audit = result["semantic_collision_audit"]

    assert result["status"] == "FAIL_CLOSED"
    assert audit["lost_ball_record_count"] == 1
    assert audit["lost_ball_reviewed_record_count"] == 0
    assert audit["lost_ball_reconciliation_mismatch_count"] == 1
    assert audit["ball_recovery_record_count"] == 1
    assert audit["ball_recovery_reviewed_record_count"] == 0
    assert audit["ball_recovery_reconciliation_mismatch_count"] == 1
    assert "lost_ball_turnover_reconciliation_mismatch" in result["hard_block_hits"]
    assert "ball_recovery_reconciliation_mismatch" in result["hard_block_hits"]
