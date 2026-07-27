from __future__ import annotations

import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from field_semantics import (  # noqa: E402
    actor_identity_applicability,
    enrich_actor_semantics,
    enrich_consequence_records,
    response_latency_class,
    semantic_counters,
)


def node(node_id, team, start, families, x=10, y=20, role="PLAYER_SURFACE_CANDIDATE", actor="a"):
    return {
        "selected_action_node_id": node_id,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "source_role": role,
        "start_candidate": str(start),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "action_family_candidates": families,
    }


def record(anchor, layers, visible, delta):
    return {
        "anchor_selected_action_node_id": anchor,
        "follow_up_node_ids_by_layer": layers,
        "visible_follow_up_node_ids": visible,
        "first_visible_follow_up_delta_seconds": delta,
    }


def test_actor_not_applicable_for_team_surface():
    assert actor_identity_applicability({"source_role": "TEAM_SURFACE_CANDIDATE", "actor_identity_candidate_id": None}) == "NOT_APPLICABLE_TEAM_SURFACE"


def test_actor_missing_for_player_is_review_required():
    assert actor_identity_applicability({"source_role": "PLAYER_SURFACE_CANDIDATE", "actor_identity_candidate_id": None}) == "MISSING_REVIEW_REQUIRED"


def test_latency_classes():
    assert response_latency_class(4.0, visible=True) == "WITHIN_5S"
    assert response_latency_class(6.0, visible=True) == "BETWEEN_5_AND_8S"
    assert response_latency_class(10.0, visible=True) == "BETWEEN_8_AND_12S"
    assert response_latency_class(None, visible=False) == "NO_VISIBLE_RESPONSE"


def test_same_team_first_layer_retention_and_displacement():
    nodes = {
        "a": node("a", "ta", 10, ["PASS"], 10, 20),
        "b": node("b", "ta", 14, ["PASS"], 16, 28),
    }
    row = enrich_consequence_records([record("a", [["b"]], ["b"], 4)], nodes)[0]
    assert row["first_layer_team_state"] == "SAME_TEAM"
    assert row["retention_after_action_candidate"] == "SAME_TEAM_VISIBLE_RETENTION_CANDIDATE"
    assert row["same_team_response_latency_class"] == "WITHIN_5S"
    assert row["opponent_response_latency_class"] == "NO_VISIBLE_RESPONSE"
    assert row["raw_coordinate_delta_x_candidate"] == 6.0
    assert row["raw_coordinate_delta_y_candidate"] == 8.0
    assert row["raw_coordinate_displacement_candidate"] == 10.0
    assert row["raw_coordinate_displacement_class"] == "SHORT_RAW_PROVIDER_DISPLACEMENT"
    assert row["progression_interpretation_status"] == "WAIT_ATTACK_DIRECTION_AND_COORDINATE_SCALE_CONTRACT"


def test_opponent_first_layer_handover_and_latency():
    nodes = {
        "a": node("a", "ta", 10, ["PASS"]),
        "b": node("b", "tb", 16, ["RECOVERY"], 20, 20),
    }
    row = enrich_consequence_records([record("a", [["b"]], ["b"], 6)], nodes)[0]
    assert row["first_layer_team_state"] == "OPPONENT"
    assert row["retention_after_action_candidate"] == "OPPONENT_VISIBLE_HANDOVER_CANDIDATE"
    assert row["opponent_response_latency_class"] == "BETWEEN_5_AND_8S"


def test_mixed_first_layer_is_review_required_and_no_arbitrary_displacement():
    nodes = {
        "a": node("a", "ta", 10, ["PASS"]),
        "b": node("b", "ta", 12, ["PASS"], 20, 20),
        "c": node("c", "tb", 12, ["SHOT"], 30, 20),
    }
    row = enrich_consequence_records([record("a", [["b", "c"]], ["b", "c"], 2)], nodes)[0]
    assert row["first_layer_team_state"] == "MIXED"
    assert row["retention_after_action_candidate"] == "MIXED_TEAM_SAME_TIME_REVIEW_REQUIRED_CANDIDATE"
    assert row["coordinate_displacement_status"] == "MIXED_FIRST_LAYER_COORDINATE_REVIEW_REQUIRED"
    assert row["raw_coordinate_displacement_candidate"] is None


def test_no_follow_up_has_explicit_status_not_ambiguous_null():
    nodes = {"a": node("a", "ta", 10, ["PASS"])}
    row = enrich_consequence_records([record("a", [], [], None)], nodes)[0]
    assert row["first_visible_follow_up_status"] == "NOT_VISIBLE_WITHIN_12S"
    assert row["first_visible_follow_up_delta_status"] == "NOT_APPLICABLE_NO_VISIBLE_FOLLOW_UP"
    assert row["first_follow_up_window_class"] == "NO_VISIBLE_RESPONSE"
    assert row["coordinate_displacement_status"] == "NOT_VISIBLE_WITHIN_12S"


def test_turnover_response_same_team_recovery():
    nodes = {
        "a": node("a", "ta", 10, ["TURNOVER"]),
        "b": node("b", "ta", 13, ["RECOVERY"]),
    }
    row = enrich_consequence_records([record("a", [["b"]], ["b"], 3)], nodes)[0]
    assert row["turnover_response_candidate"] == "SAME_TEAM_RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
    assert row["turnover_response_is_counterpress_success_truth"] is False


def test_non_turnover_response_is_not_applicable():
    nodes = {
        "a": node("a", "ta", 10, ["PASS"]),
        "b": node("b", "ta", 13, ["PASS"]),
    }
    row = enrich_consequence_records([record("a", [["b"]], ["b"], 3)], nodes)[0]
    assert row["turnover_response_candidate"] == "NOT_APPLICABLE"


def test_pressure_is_explicitly_unavailable_not_inferred():
    nodes = {"a": node("a", "ta", 10, ["PASS"])}
    row = enrich_consequence_records([record("a", [], [], None)], nodes)[0]
    assert row["pressure_interpretation_status"] == "UNAVAILABLE_EVENT_ONLY_NO_TRACKING_OR_EXPLICIT_PRESSURE_EVENT"


def test_missing_reference_routes_review():
    nodes = {"a": node("a", "ta", 10, ["PASS"])}
    row = enrich_consequence_records([record("a", [["missing"]], ["missing"], 2)], nodes)[0]
    assert row["field_semantics_status"] == "REVIEW_REQUIRED"
    assert row["first_visible_follow_up_status"] == "UNKNOWN_REVIEW"


def test_semantic_counters_have_no_undefined_for_enriched_rows():
    nodes = {"a": node("a", "ta", 10, ["PASS"])}
    counters = semantic_counters(enrich_consequence_records([record("a", [], [], None)], nodes))
    assert all("UNDEFINED" not in values for values in counters.values())


def test_surface_records_can_be_enriched_without_mutating_identity_value():
    rows = [{"source_role": "TEAM_SURFACE_CANDIDATE", "actor_identity_candidate_id": None}]
    enrich_actor_semantics(rows)
    assert rows[0]["actor_identity_candidate_id"] is None
    assert rows[0]["actor_identity_applicability"] == "NOT_APPLICABLE_TEAM_SURFACE"


def test_contract_registry_contains_current_source_classes():
    contract = json.loads((MODULE_ROOT / "contract" / "selected_action_consequence_surface_lite_v1.json").read_text(encoding="utf-8"))
    assert contract["version"] == "1.1.0"
    assert contract["field_semantics_version"] == "selected_action_consequence_field_semantics_v1_1"
    assert "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE" in contract["primary_consequence_candidates"]
