from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from analyst_episode_locator import build_episode_locator, validate_output_root


def _nucleus(idx: int, action: str, *, review: bool = False) -> dict:
    return {
        "row_nucleus_candidate_id": f"rn_{idx}",
        "status": "REVIEW_REQUIRED" if review else "PASS",
        "resolved_visible_fields": {
            "action": action,
            "code": action,
        },
    }


def _context(
    idx: int,
    second: float,
    period: str,
    family: str,
    *,
    team: str = "team_a",
    zone: str = "MIDDLE_THIRD",
    channel: str = "CENTRAL_CHANNEL",
    review: bool = False,
) -> dict:
    reasons = ["visible_field_serialization_discrepancy"] if review else []
    return {
        "context_id": f"ctx_{idx}",
        "period": period,
        "team_label": team,
        "action_family": family,
        "zone_candidate": zone,
        "channel_candidate": channel,
        "time_admission_status": "ADMITTED",
        "time_unit_status": "SECOND",
        "time_source_value": second,
        "admitted_time_evidence": [
            {
                "field": "absolute_time_seconds",
                "raw_value": second,
                "unit": "SECOND",
                "minute_bucket": int(second // 60),
            }
        ],
        "_preserved_unmapped": {
            "row_nucleus_candidate_id": f"rn_{idx}",
            "row_nucleus_status": "REVIEW_REQUIRED" if review else "PASS",
            "review_reasons": reasons,
            "lineage_review_reasons": reasons,
        },
    }


def _payloads() -> tuple[dict, dict]:
    rows = [
        ("start of the 1st half", 4.15, "1", "UNKNOWN_OR_OTHER", True),
        ("pass", 10.0, "1", "PASS", False),
        ("recovery", 12.0, "1", "RECOVERY", False),
        ("corner", 40.0, "1", "RESTART", False),
        ("shot", 45.0, "1", "SHOT", False),
        ("halftime", 2921.15, "1", "UNKNOWN_OR_OTHER", True),
        ("start of the 2nd half", 2955.49, "2", "UNKNOWN_OR_OTHER", True),
        ("pass", 3000.0, "2", "PASS", False),
        ("shot", 3010.0, "2", "SHOT", False),
        ("end of the match", 5977.49, "2", "UNKNOWN_OR_OTHER", True),
    ]
    nuclei = [_nucleus(i, action, review=review) for i, (action, *_rest, review) in enumerate(rows)]
    contexts = [
        _context(
            i,
            second,
            period,
            family,
            team="unknown" if review else "team_a",
            zone="UNKNOWN_ZONE" if review else "MIDDLE_THIRD",
            channel="UNKNOWN_CHANNEL" if review else "CENTRAL_CHANNEL",
            review=review,
        )
        for i, (_action, second, period, family, review) in enumerate(rows)
    ]
    row_payload = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "row_nucleus_candidate_count": len(nuclei),
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
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
    return mvc, row_payload


def test_episode_locator_builds_navigation_units_and_admin_boundaries() -> None:
    mvc, row = _payloads()
    result = build_episode_locator(mvc, row)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["administrative_boundary_candidate_count"] == 4
    assert result["administrative_boundary_type_counts"] == {
        "FIRST_HALF_START": 1,
        "FULL_TIME": 1,
        "HALFTIME": 1,
        "SECOND_HALF_START": 1,
    }
    assert result["episode_candidate_count"] == 3
    assert result["context_assignment_complete"] is True
    assert result["context_assignment_count"] == 10
    assert result["reflection_inflation_prevented"] is True
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_admin_boundary_missing_team_space_is_not_football_contradiction() -> None:
    mvc, row = _payloads()
    result = build_episode_locator(mvc, row)
    assert result["administrative_boundary_review_debt_count"] > 0
    for boundary in result["administrative_boundary_candidates"]:
        assert boundary["boundary_is_football_action_truth"] is False
        assert boundary["boundary_is_phase_truth"] is False


def test_same_time_membership_never_creates_internal_order() -> None:
    mvc, row = _payloads()
    extra_nucleus = _nucleus(10, "pass")
    row["row_nuclei"].append(extra_nucleus)
    row["row_nucleus_candidate_count"] += 1
    extra_context = _context(10, 10.0, "1", "PASS")
    mvc["context_candidates"].append(extra_context)
    mvc["context_candidate_count"] += 1
    mvc["row_nucleus_context_binding"]["row_nucleus_candidate_count"] += 1
    result = build_episode_locator(mvc, row)
    assert result["same_time_unordered_layer_count"] >= 1
    layer = next(x for x in result["episode_time_layer_candidates"] if x["second_candidate"] == 10.0)
    assert layer["same_time_unordered"] is True
    assert layer["same_timestamp_internal_ordering_allowed"] is False
    assert layer["source_row_order_is_temporal_truth"] is False


def test_non_admin_review_debt_propagates_into_episode() -> None:
    mvc, row = _payloads()
    mvc["context_candidates"][1]["_preserved_unmapped"]["row_nucleus_status"] = "REVIEW_REQUIRED"
    mvc["context_candidates"][1]["_preserved_unmapped"]["review_reasons"] = ["identity_review_required"]
    row["row_nuclei"][1]["status"] = "REVIEW_REQUIRED"
    result = build_episode_locator(mvc, row)
    assert result["episode_review_debt_count"] > 0
    assert any(ep["status"] == "EPISODE_CANDIDATE_WITH_REVIEW_DEBT" for ep in result["episode_candidates"])


def test_episode_requires_admitted_time() -> None:
    mvc, row = _payloads()
    mvc["context_candidates"][1]["time_admission_status"] = "REVIEW_REQUIRED"
    result = build_episode_locator(mvc, row)
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("context_admitted_second_missing") for hit in result["hard_block_hits"])


def test_episode_requires_row_nucleus_bound_context_not_raw_reflections() -> None:
    mvc, row = _payloads()
    mvc["row_nucleus_context_binding"]["enabled"] = False
    mvc["row_nucleus_context_binding"]["reflection_inflation_prevented"] = False
    result = build_episode_locator(mvc, row)
    assert result["status"] == "FAIL_CLOSED"
    assert "row_nucleus_context_binding_missing" in result["hard_block_hits"]
    assert "reflection_inflation_not_prevented" in result["hard_block_hits"]


def test_claim_locks_and_no_truth_promotion() -> None:
    mvc, row = _payloads()
    result = build_episode_locator(mvc, row)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["phase_truth"] is False
    assert result["rhythm_truth"] is False
    assert result["tactical_truth"] is False
    assert result["dominance_truth"] is False
    assert result["fatigue_truth"] is False
    for episode in result["episode_candidates"]:
        assert episode["episode_is_possession_truth"] is False
        assert episode["episode_is_sequence_truth"] is False
        assert episode["episode_is_phase_truth"] is False
        assert episode["episode_is_rhythm_truth"] is False
        assert episode["episode_is_tactical_truth"] is False


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root(Path("/sdcard/Download/HPFA/episode"))


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "analyst_episode_locator.py").read_text(encoding="utf-8")
    forbidden = ["Fenerbahce", "Galatasaray", "Genclerbirligi", "15.08.2026", "Turkey", "World Cup"]
    assert not any(token in text for token in forbidden)
