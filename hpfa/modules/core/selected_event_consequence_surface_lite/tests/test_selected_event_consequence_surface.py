from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from coordinate_frame import resolve_coordinate_frame, zone_candidate  # noqa: E402
from selected_event_consequence_surface import build_selected_event_consequence_surface, validate_out, write_outputs  # noqa: E402

BINDING = "msb_generic"
TEAM_A = "team_a"
TEAM_B = "team_b"


def node(node_id: str, team: str, period: str, start: float, x: float, y: float, families: list[str], actor: str = "actor_a") -> dict:
    return {
        "selected_action_node_id": node_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 1),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidates": families,
        "canonical_event_count": "UNKNOWN",
    }


def consequence(cid: str, anchor: str, layers: list[list[str]], primary: str = "SAME_TEAM_CONTINUATION_CANDIDATE") -> dict:
    visible = [item for layer in layers for item in layer]
    return {
        "selected_action_consequence_candidate_id": cid,
        "anchor_selected_action_node_id": anchor,
        "follow_up_node_ids_by_layer": layers,
        "visible_follow_up_node_ids": visible,
        "primary_consequence_candidate": primary,
        "canonical_event_count": "UNKNOWN",
    }


def payload(nodes: list[dict], records: list[dict], field_version: str = "selected_action_consequence_field_semantics_v1_1") -> dict:
    return {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "field_semantics_version": field_version,
        "selected_action_nodes": nodes,
        "selected_action_node_count": len(nodes),
        "selected_action_consequence_candidates": records,
        "selected_action_consequence_candidate_count": len(records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def frame_support_nodes() -> list[dict]:
    rows = []
    for team, actor in ((TEAM_A, "a"), (TEAM_B, "b")):
        for period in ("1", "2"):
            for index, x in enumerate((82.0, 91.0, 97.0)):
                rows.append(node(f"shot_{team}_{period}_{index}", team, period, 100 + index, x, 34, ["SHOT"], actor))
    rows.extend([
        node("scale_a", TEAM_A, "1", 1, 0, 0, ["PASS"]),
        node("scale_b", TEAM_B, "2", 2, 105, 68, ["PASS"]),
    ])
    return rows


def with_self_records(nodes: list[dict]) -> list[dict]:
    return [consequence(f"c_{record['selected_action_node_id']}", record["selected_action_node_id"], []) for record in nodes]


def test_coordinate_frame_resolves_105x68_high_x_candidate():
    frame = resolve_coordinate_frame(frame_support_nodes())
    assert frame["coordinate_frame_status"] == "PASS_CANDIDATE_FRAME"
    assert frame["coordinate_scale_candidate"] == "PROVIDER_105X68_SCALE_CANDIDATE"
    assert all(row["attack_direction_candidate"] == "ATTACK_TOWARD_HIGH_X_CANDIDATE" for row in frame["team_period_attack_direction_candidates"])


def test_no_zone_classification_without_frame_candidate():
    record = node("n", TEAM_A, "1", 1, 50, 30, ["PASS"])
    zone = zone_candidate(record, resolve_coordinate_frame([record]))
    assert zone["zone_candidate"] == "UNRESOLVED_ZONE_REVIEW_REQUIRED"


def test_same_team_zone_gain_and_box_access():
    nodes = frame_support_nodes()
    anchor = node("anchor", TEAM_A, "1", 10, 20, 30, ["PASS"])
    follow = node("follow", TEAM_A, "1", 14, 92, 34, ["PASS"])
    nodes.extend([anchor, follow])
    records = with_self_records(nodes[:-2]) + [consequence("c_anchor", "anchor", [["follow"]]), consequence("c_follow", "follow", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "anchor")
    assert row["zone_delta_class"] in {"BOX_ACCESS_CANDIDATE", "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE"}
    assert row["retention_after_action_candidate"] is True
    assert row["consequence_class_candidate"] == "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE"


def test_cross_team_coordinate_delta_is_not_compared():
    nodes = frame_support_nodes()
    anchor = node("anchor", TEAM_A, "1", 10, 20, 30, ["PASS"])
    opponent = node("opp", TEAM_B, "1", 14, 95, 34, ["PASS"], "b")
    nodes.extend([anchor, opponent])
    records = with_self_records(nodes[:-2]) + [consequence("c_anchor", "anchor", [["opp"]], "OPPONENT_HANDOVER_CANDIDATE"), consequence("c_opp", "opp", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "anchor")
    assert row["zone_delta_class"] == "LOSS_OR_HANDOVER_CANDIDATE"
    assert row["first_same_team_zone_candidates"] == []


def test_mixed_first_layer_remains_review_required():
    nodes = frame_support_nodes()
    anchor = node("anchor", TEAM_A, "1", 10, 20, 30, ["PASS"])
    same = node("same", TEAM_A, "1", 14, 50, 34, ["PASS"])
    opponent = node("opp", TEAM_B, "1", 14, 50, 34, ["DUEL"], "b")
    nodes.extend([anchor, same, opponent])
    records = with_self_records(nodes[:-3]) + [consequence("c_anchor", "anchor", [["same", "opp"]]), consequence("c_same", "same", []), consequence("c_opp", "opp", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "anchor")
    assert row["first_layer_team_state"] == "MIXED_REVIEW_REQUIRED"
    assert row["consequence_class_candidate"] == "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"


def test_pressure_is_explicitly_unavailable_not_none():
    nodes = frame_support_nodes()
    result = build_selected_event_consequence_surface(payload(nodes, with_self_records(nodes)))
    assert set(result["pressure_first_action_class_counts"]) == {"UNAVAILABLE_EVENT_ONLY_NO_EXPLICIT_PRESSURE_EVIDENCE"}


def test_turnover_to_opponent_shot_precedence():
    nodes = frame_support_nodes()
    anchor = node("loss", TEAM_A, "1", 10, 50, 34, ["TURNOVER"])
    opponent = node("opp_shot", TEAM_B, "1", 14, 92, 34, ["SHOT"], "b")
    nodes.extend([anchor, opponent])
    records = with_self_records(nodes[:-2]) + [consequence("c_loss", "loss", [["opp_shot"]], "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"), consequence("c_opp", "opp_shot", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "loss")
    assert row["turnover_window_class"] == "TURNOVER_TO_OPPONENT_SHOT_CANDIDATE"
    assert row["consequence_class_candidate"] == "FAILED_VISIBLE_CONSEQUENCE_CANDIDATE"


def test_turnover_to_same_team_recovery():
    nodes = frame_support_nodes()
    anchor = node("loss", TEAM_A, "1", 10, 50, 34, ["TURNOVER"])
    recovery = node("recovery", TEAM_A, "1", 13, 48, 34, ["RECOVERY"])
    nodes.extend([anchor, recovery])
    records = with_self_records(nodes[:-2]) + [consequence("c_loss", "loss", [["recovery"]]), consequence("c_rec", "recovery", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "loss")
    assert row["turnover_window_class"] == "TURNOVER_TO_SAME_TEAM_RECOVERY_CANDIDATE"


def test_false_progression_requires_gain_then_handover():
    nodes = frame_support_nodes()
    anchor = node("anchor", TEAM_A, "1", 10, 20, 34, ["CARRY"])
    gain = node("gain", TEAM_A, "1", 13, 75, 34, ["PASS"])
    opponent = node("opp", TEAM_B, "1", 18, 60, 34, ["RECOVERY"], "b")
    nodes.extend([anchor, gain, opponent])
    records = with_self_records(nodes[:-3]) + [consequence("c_anchor", "anchor", [["gain"], ["opp"]]), consequence("c_gain", "gain", [["opp"]]), consequence("c_opp", "opp", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "anchor")
    assert row["zone_delta_class"] in {"THIRD_BREAK_CANDIDATE", "ZONE_GAIN_CANDIDATE"}
    assert row["false_progression_candidate"] == "FALSE_PROGRESSION_CANDIDATE"
    assert row["consequence_class_candidate"] == "RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE"


def test_no_false_progression_without_gain():
    nodes = frame_support_nodes()
    anchor = node("anchor", TEAM_A, "1", 10, 50, 34, ["PASS"])
    follow = node("follow", TEAM_A, "1", 13, 52, 34, ["PASS"])
    nodes.extend([anchor, follow])
    records = with_self_records(nodes[:-2]) + [consequence("c_anchor", "anchor", [["follow"]]), consequence("c_follow", "follow", [])]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    row = next(record for record in result["selected_event_consequence_candidates"] if record["anchor_selected_action_node_id"] == "anchor")
    assert row["false_progression_candidate"] == "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN"


def test_every_input_consequence_is_covered_once():
    nodes = frame_support_nodes()
    result = build_selected_event_consequence_surface(payload(nodes, with_self_records(nodes)))
    assert result["selected_event_consequence_candidate_count"] == len(nodes)
    assert len({record["source_selected_action_consequence_candidate_id"] for record in result["selected_event_consequence_candidates"]}) == len(nodes)


def test_bad_anchor_coverage_fails_closed():
    nodes = frame_support_nodes()
    records = with_self_records(nodes)[:-1]
    result = build_selected_event_consequence_surface(payload(nodes, records))
    assert result["status"] == "FAIL_CLOSED"


def test_claim_boundaries_closed():
    nodes = frame_support_nodes()
    result = build_selected_event_consequence_surface(payload(nodes, with_self_records(nodes)))
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["event_instance_count"] == 0
    assert result["claim_allowed"] is False
    assert result["production_release"] is False
    assert result["zone_delta_not_xT"] is True


def test_nested_phone_output_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_outputs_written(tmp_path: Path):
    nodes = frame_support_nodes()
    result = build_selected_event_consequence_surface(payload(nodes, with_self_records(nodes)))
    paths = write_outputs(result, tmp_path)
    assert all(path.exists() for path in paths.values())
    stored = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert stored["module_id"] == "selected_event_consequence_surface_lite_v1"


def test_no_sample_match_identity_leak():
    text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src").glob("*.py"))
    forbidden = ["Australia", "Turkey", "World Cup", "Galatasaray", "Juventus", "6935", "77798"]
    assert not any(item in text for item in forbidden)
