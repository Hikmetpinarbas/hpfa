from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "analyst_episode_locator_lite" / "src"
sys.path.insert(0, str(SRC))

from analyst_episode_locator import build_episode_locator


def _nucleus(idx: int, action: str) -> dict:
    return {
        "row_nucleus_candidate_id": f"rn_{idx}",
        "status": "PASS",
        "resolved_visible_fields": {"action": action, "code": action},
    }


def _context(idx: int, second: float, action_family: str) -> dict:
    return {
        "context_id": f"ctx_{idx}",
        "period": "1",
        "team_label": "team_a",
        "action_family": action_family,
        "zone_candidate": "MIDDLE_THIRD",
        "channel_candidate": "CENTRAL_CHANNEL",
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
            "row_nucleus_status": "PASS",
            "review_reasons": [],
            "lineage_review_reasons": [],
        },
    }


def _payloads() -> tuple[dict, dict]:
    # All four football observations are within the 20-second continuity gap.
    # A RESTART or SHOT label must therefore remain an observation inside one
    # navigation episode, not become episode-boundary authority.
    rows = [
        ("pass", 100.0, "PASS"),
        ("corner", 105.0, "RESTART"),
        ("shot", 110.0, "SHOT"),
        ("recovery", 115.0, "RECOVERY"),
    ]
    nuclei = [_nucleus(i, action) for i, (action, _second, _family) in enumerate(rows)]
    contexts = [_context(i, second, family) for i, (_action, second, family) in enumerate(rows)]
    row_payload = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "PASS",
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


def test_restart_and_shot_labels_do_not_fragment_episode_navigation() -> None:
    mvc, row = _payloads()
    result = build_episode_locator(mvc, row)
    assert result["episode_candidate_count"] == 1
    episode = result["episode_candidates"][0]
    assert episode["start_second_candidate"] == 100.0
    assert episode["end_second_candidate"] == 115.0
    assert episode["restart_layer_count"] == 1
    assert episode["terminal_layer_count"] == 1
    assert episode["restart_observation_only"] is True
    assert episode["terminal_action_observation_only"] is True
    assert result["restart_boundary_authority"] is False
    assert result["terminal_action_boundary_authority"] is False
    assert result["action_family_labels_are_boundary_authority"] is False
    assert result["soft_boundary_rules"] == ["VISIBLE_TIME_GAP_BOUNDARY"]
    assert "RESTART_VISIBLE_BOUNDARY" not in result["soft_boundary_rules"]
    assert "TERMINAL_ACTION_VISIBLE_BOUNDARY" not in result["soft_boundary_rules"]


def test_time_gap_remains_neutral_soft_boundary() -> None:
    mvc, row = _payloads()
    mvc["context_candidates"][3]["time_source_value"] = 140.0
    mvc["context_candidates"][3]["admitted_time_evidence"][0]["raw_value"] = 140.0
    result = build_episode_locator(mvc, row)
    assert result["episode_candidate_count"] == 2
    assert result["episode_candidates"][0]["boundary_end_reason"] == "VISIBLE_TIME_GAP_BOUNDARY"
    assert result["episode_candidates"][1]["boundary_start_reason"] == "AFTER_VISIBLE_TIME_GAP"
