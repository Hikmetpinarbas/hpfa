from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from analyst_episode_locator import build_episode_locator, validate_output_root


def _context(idx: int, second: float, period: str = "1", *, review: bool = False) -> dict:
    reasons = ["visible_field_serialization_discrepancy"] if review else []
    return {
        "context_id": f"ctx_{idx}",
        "period": period,
        "team_label": "team_a",
        "zone_candidate": "MIDDLE_THIRD",
        "channel_candidate": "CENTRAL_CHANNEL",
        "time_admission_status": "ADMITTED",
        "time_unit_status": "SECOND",
        "time_source_value": second,
        "admitted_time_evidence": [{"field": "absolute_time_seconds", "raw_value": second, "unit": "SECOND"}],
        "_preserved_unmapped": {
            "row_nucleus_candidate_id": f"rn_{idx}",
            "row_nucleus_status": "REVIEW_REQUIRED" if review else "PASS",
            "review_reasons": reasons,
            "lineage_review_reasons": reasons,
        },
    }


def _semantic(
    idx: int,
    role: str,
    family: str,
    eligible: bool,
    raw_label: str,
    *,
    non_action: bool = False,
    reviewed: bool = True,
) -> dict:
    return {
        "context_id": f"ctx_{idx}",
        "row_nucleus_candidate_id": f"rn_{idx}",
        "raw_label": raw_label,
        "provider_semantic_role_candidate": role,
        "provider_action_family_candidate": family,
        "provider_semantics_review_status": "REVIEWED_CANDIDATE" if reviewed else "REVIEW_REQUIRED",
        "action_occurrence_eligible": eligible,
        "non_action_context_or_reference": non_action,
    }


def _payloads() -> tuple[dict, dict, dict]:
    specs = [
        (4.15, "PERIOD_OR_META", "UNKNOWN", False, "start of the 1st half", True, True, True),
        (10.0, "ACTION_ANCHOR", "PASS", True, "passes accurate", False, True, False),
        (10.0, "ATTRIBUTE_REFERENCE", "PASS", False, "goal kicks short", True, True, False),
        (12.0, "ACTION_ANCHOR", "RESTART", True, "goal kicks", False, True, False),
        (14.0, "ACTION_ANCHOR", "TURNOVER", True, "lost balls", False, True, False),
        (16.0, "ACTION_ANCHOR", "RECOVERY", True, "ball recoveries", False, True, False),
        (18.0, "ACTION_ANCHOR", "SHOT", True, "shots on target", False, True, False),
        (18.0, "OPPONENT_ACTION_REFERENCE", "SHOT", False, "shots on target", True, True, False),
        (19.0, "UNKNOWN_UNREVIEWED", "UNKNOWN", False, "provider unresolved label", False, False, False),
        (45.0, "ACTION_ANCHOR", "PASS", True, "passes accurate", False, True, False),
        (2921.15, "PERIOD_OR_META", "UNKNOWN", False, "halftime", True, True, True),
    ]
    contexts = [_context(i, second, review=review) for i, (second, *_rest, review) in enumerate(specs)]
    nuclei = [
        {"row_nucleus_candidate_id": f"rn_{i}", "status": "REVIEW_REQUIRED" if review else "PASS"}
        for i, (_second, *_rest, review) in enumerate(specs)
    ]
    semantic_rows = [
        _semantic(i, role, family, eligible, raw_label, non_action=non_action, reviewed=reviewed)
        for i, (_second, role, family, eligible, raw_label, non_action, reviewed, _review) in enumerate(specs)
    ]

    mvc = {
        "module_id": "minimum_viable_context_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_candidate_count": len(contexts),
        "context_candidates": contexts,
        "time_admission_status": "ADMITTED",
        "context_occurrence_basis": "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT",
        "row_nucleus_context_binding": {
            "enabled": True,
            "reflection_inflation_prevented": True,
            "row_nucleus_candidate_count": len(nuclei),
        },
        "source_row_order_is_temporal_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    row = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "row_nucleus_candidate_count": len(nuclei),
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    semantics = {
        "module_id": "context_action_semantics_rebind_lite_v1",
        "status": "REVIEW_REQUIRED",
        "context_action_semantic_records": semantic_rows,
        "context_action_semantic_record_count": len(semantic_rows),
        "context_semantic_assignment_complete": True,
        "action_occurrence_eligible_count": 6,
        "non_action_context_or_reference_count": 4,
        "provider_semantics_unresolved_or_review_required_count": 1,
        "eligible_action_family_candidate_counts": {
            "PASS": 2,
            "RECOVERY": 1,
            "RESTART": 1,
            "SHOT": 1,
            "TURNOVER": 1,
        },
        "semantic_collision_audit": {
            "team_goal_kick_length_action_occurrence_eligible_count": 0,
            "goalkeeper_shot_reference_action_occurrence_eligible_count": 0,
        },
        "reflection_inflation_prevented": True,
        "reference_participation_context_adds_action_volume": False,
        "review_limited_semantics_adds_action_volume": False,
        "same_timestamp_internal_ordering_allowed": False,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return mvc, row, semantics


def test_episode_uses_reviewed_action_eligible_volume_only() -> None:
    mvc, row, semantics = _payloads()
    result = build_episode_locator(mvc, row, semantics)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["context_assignment_complete"] is True
    assert result["context_assignment_count"] == len(mvc["context_candidates"])
    assert result["episode_candidate_count"] == 2
    assert result["episode_action_occurrence_eligible_count"] == 6
    assert result["episode_support_only_context_count"] == 3
    assert result["episode_eligible_action_family_candidate_counts"] == semantics["eligible_action_family_candidate_counts"]
    assert result["action_volume_basis"] == "REVIEWED_ACTION_OCCURRENCE_ELIGIBLE_ONLY"
    assert result["support_rows_add_action_volume"] is False


def test_reference_rows_do_not_inflate_shot_pass_or_restart_volume() -> None:
    mvc, row, semantics = _payloads()
    result = build_episode_locator(mvc, row, semantics)
    counts = result["episode_eligible_action_family_candidate_counts"]
    assert counts["SHOT"] == 1
    assert counts["PASS"] == 2
    assert counts["RESTART"] == 1
    assert counts["TURNOVER"] == 1
    assert counts["RECOVERY"] == 1


def test_same_time_support_and_action_rows_remain_unordered() -> None:
    mvc, row, semantics = _payloads()
    result = build_episode_locator(mvc, row, semantics)
    assert result["same_time_unordered_layer_count"] >= 2
    layer = next(x for x in result["episode_time_layer_candidates"] if x["second_candidate"] == 10.0)
    assert layer["action_occurrence_eligible_context_count"] == 1
    assert layer["support_only_context_count"] == 1
    assert layer["same_time_unordered"] is True
    assert layer["same_timestamp_internal_ordering_allowed"] is False


def test_semantic_assignment_is_required() -> None:
    mvc, row, semantics = _payloads()
    semantics = copy.deepcopy(semantics)
    semantics["context_semantic_assignment_complete"] = False
    result = build_episode_locator(mvc, row, semantics)
    assert result["status"] == "FAIL_CLOSED"
    assert "semantic_context_assignment_incomplete" in result["hard_block_hits"]


def test_semantic_collision_guard_fails_closed() -> None:
    mvc, row, semantics = _payloads()
    semantics = copy.deepcopy(semantics)
    semantics["semantic_collision_audit"]["team_goal_kick_length_action_occurrence_eligible_count"] = 1
    result = build_episode_locator(mvc, row, semantics)
    assert result["status"] == "FAIL_CLOSED"
    assert "team_goal_kick_length_reference_promoted_to_action" in result["hard_block_hits"]


def test_action_family_reconciliation_fails_closed() -> None:
    mvc, row, semantics = _payloads()
    semantics = copy.deepcopy(semantics)
    semantics["eligible_action_family_candidate_counts"]["SHOT"] = 2
    result = build_episode_locator(mvc, row, semantics)
    assert result["status"] == "FAIL_CLOSED"
    assert "episode_action_family_reconciliation_mismatch" in result["hard_block_hits"]


def test_claim_locks() -> None:
    mvc, row, semantics = _payloads()
    result = build_episode_locator(mvc, row, semantics)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["phase_truth"] is False
    assert result["rhythm_truth"] is False
    assert result["tactical_truth"] is False
    assert result["dominance_truth"] is False
    assert result["fatigue_truth"] is False
    assert result["production_release"] is False


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root(Path("/sdcard/Download/HPFA/episode"))


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "analyst_episode_locator.py").read_text(encoding="utf-8")
    forbidden = ["Fenerbahce", "Galatasaray", "Genclerbirligi", "15.08.2026", "Turkey", "World Cup"]
    assert not any(token in text for token in forbidden)
