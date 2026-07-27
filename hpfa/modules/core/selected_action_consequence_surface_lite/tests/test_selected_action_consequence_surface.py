from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from selected_action_consequence_surface import (  # noqa: E402
    build_selected_action_consequence_surface,
    validate_out,
    write_outputs,
)

BINDING = "msb_generic_surface"
TEAM_A = "teamc_a"
TEAM_B = "teamc_b"
ACTOR_A = "actorc_a"
ACTOR_B = "actorc_b"


def bundle(
    bundle_id: str,
    *,
    role: str,
    team: str,
    actor: str | None,
    start: float,
    family: str,
    status: str = "PASS",
    x: float = 10.0,
    y: float = 20.0,
    period: str = "1",
) -> dict:
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 1.0),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": [f"ea_{bundle_id}"],
        "provider_row_id_candidates": [bundle_id],
        "raw_labels": [family.lower()],
        "normalized_labels": [family.lower()],
        "bundle_status": status,
        "review_hits": [] if status == "PASS" else ["same_surface_multiple_action_families"],
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def taxonomy(record_id: str, bundles: list[dict], status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict:
    first = bundles[0]
    return {
        "multi_family_review_record_id": record_id,
        "match_surface_binding_id": BINDING,
        "source_role": first["source_role"],
        "team_identity_candidate_id": first["team_identity_candidate_id"],
        "actor_identity_candidate_id": first["actor_identity_candidate_id"],
        "period_candidate": first["period_candidate"],
        "start_candidate": f"{float(first['start_candidate']):.6f}",
        "end_candidate": f"{float(first['end_candidate']):.6f}",
        "pos_x_candidate": f"{float(first['pos_x_candidate']):.6f}",
        "pos_y_candidate": f"{float(first['pos_y_candidate']):.6f}",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "family_set": sorted({item["action_family_candidate"] for item in bundles}),
        "family_count": len({item["action_family_candidate"] for item in bundles}),
        "supporting_action_bundle_candidate_ids": [item["action_bundle_candidate_id"] for item in bundles],
        "supporting_evidence_atom_ids": [f"ea_{item['action_bundle_candidate_id']}" for item in bundles],
        "record_status": status,
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE" if status.startswith("PASS") else "MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED",
        "classification_is_event_truth": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def relation(
    relation_id: str,
    primary: dict,
    reflection: dict,
    status: str = "PASS_CANDIDATE_CLASSIFICATION",
) -> dict:
    return {
        "resolved_relation_candidate_id": relation_id,
        "match_surface_binding_id": BINDING,
        "relation_record_status": status,
        "relation_classification": "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLEAR" if status.startswith("PASS") else "REVIEW_REQUIRED_PLAYER_TEAM_UNRESOLVED_CONTEXT",
        "primary_action_bundle_candidate_id": primary["action_bundle_candidate_id"],
        "reflection_action_bundle_candidate_id": reflection["action_bundle_candidate_id"],
        "source_roles": sorted([primary["source_role"], reflection["source_role"]]),
        "team_identity_candidate_id": primary["team_identity_candidate_id"],
        "actor_identity_candidate_id": primary["actor_identity_candidate_id"],
        "period_candidate": primary["period_candidate"],
        "start_candidate": primary["start_candidate"],
        "end_candidate": primary["end_candidate"],
        "pos_x_candidate": primary["pos_x_candidate"],
        "pos_y_candidate": primary["pos_y_candidate"],
        "action_family_candidate": primary["action_family_candidate"],
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def atom(
    atom_id: str,
    *,
    role: str,
    start: float,
    atom_class: str,
    label: str,
    x: float = 10.0,
    y: float = 20.0,
    period: str = "1",
) -> dict:
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "atom_class": atom_class,
        "atom_status": "PASS",
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 1.0),
        "pos_x_candidate": str(x),
        "pos_y_candidate": str(y),
        "normalized_label": label,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(
    bundles: list[dict],
    taxonomy_records: list[dict] | None = None,
    relations: list[dict] | None = None,
    atoms: list[dict] | None = None,
) -> tuple[dict, dict, dict, dict]:
    taxonomy_records = taxonomy_records or []
    relations = relations or []
    atoms = atoms or []
    action = {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    tax = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": taxonomy_records,
        "multi_family_review_core_count": len(taxonomy_records),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    rel = {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "resolved_relation_candidates": relations,
        "resolved_relation_candidate_count": len(relations),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    evidence = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return action, tax, rel, evidence


def build(*args):
    return build_selected_action_consequence_surface(*payloads(*args))


def test_clear_relation_selects_primary_and_suppresses_team_reflection():
    primary = bundle("p1", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    reflection = bundle("t1", role="TEAM_SURFACE_CANDIDATE", team=TEAM_A, actor=None, start=10, family="PASS")
    result = build([primary, reflection], [], [relation("r1", primary, reflection)])
    assert result["selected_action_surface_candidate_count"] == 1
    assert result["suppressed_team_reflection_candidate_count"] == 1
    assert result["quarantined_unresolved_surface_count"] == 0
    assert result["selection_records"][0]["action_bundle_candidate_id"] == "p1"


def test_unresolved_relation_quarantines_both_surfaces():
    primary = bundle("p1", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS", status="REVIEW_REQUIRED")
    reflection = bundle("t1", role="TEAM_SURFACE_CANDIDATE", team=TEAM_A, actor=None, start=10, family="PASS", status="REVIEW_REQUIRED")
    result = build([primary, reflection], [], [relation("r1", primary, reflection, "REVIEW_REQUIRED")])
    assert result["selected_action_surface_candidate_count"] == 0
    assert result["quarantined_unresolved_surface_count"] == 2


def test_classified_review_bundle_is_selected():
    first = bundle("p1", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS", status="REVIEW_REQUIRED")
    second = bundle("p2", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="RESTART", status="REVIEW_REQUIRED")
    record = taxonomy("m1", [first, second])
    result = build([first, second], [record], [])
    assert result["selected_action_surface_candidate_count"] == 2
    assert result["selected_action_node_count"] == 1
    assert result["same_time_multi_family_node_count"] == 1
    assert result["selected_action_nodes"][0]["action_family_candidates"] == ["PASS", "RESTART"]


def test_unclassified_review_bundle_is_quarantined():
    first = bundle("p1", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS", status="REVIEW_REQUIRED")
    second = bundle("p2", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="RESTART", status="REVIEW_REQUIRED")
    record = taxonomy("m1", [first, second], "REVIEW_REQUIRED")
    result = build([first, second], [record], [])
    assert result["selected_action_surface_candidate_count"] == 0
    assert result["quarantined_unresolved_surface_count"] == 2


def test_same_time_nodes_are_not_linked_as_follow_up():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    b = bundle("b", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_B, start=10, family="CARRY", x=30)
    c = bundle("c", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=14, family="PASS", x=40)
    result = build([a, b, c], [], [])
    records = {r["anchor_selected_action_node_id"]: r for r in result["selected_action_consequence_candidates"]}
    nodes = {n["selected_action_node_id"]: n for n in result["selected_action_nodes"]}
    for node_id, node in nodes.items():
        if float(node["start_candidate"]) == 10:
            assert records[node_id]["first_visible_follow_up_delta_seconds"] == 4.0
            assert len(records[node_id]["visible_follow_up_node_ids"]) == 1


def test_cross_period_links_are_not_created():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=100, family="PASS", period="1")
    b = bundle("b", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=101, family="PASS", period="2")
    result = build([a, b], [], [])
    assert all(r["primary_consequence_candidate"] == "NO_VISIBLE_FOLLOW_UP_CANDIDATE" for r in result["selected_action_consequence_candidates"])


def test_window_counts_use_5_8_12_seconds_and_three_time_layers():
    anchors = [
        bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS"),
        bundle("b", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=14, family="PASS", x=20),
        bundle("c", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=17, family="PASS", x=30),
        bundle("d", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=21, family="PASS", x=40),
        bundle("e", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=22, family="PASS", x=50),
    ]
    result = build(anchors, [], [])
    first_node = min(result["selected_action_nodes"], key=lambda n: float(n["start_candidate"]))
    record = next(r for r in result["selected_action_consequence_candidates"] if r["anchor_selected_action_node_id"] == first_node["selected_action_node_id"])
    assert record["visible_follow_up_node_count_5s"] == 1
    assert record["visible_follow_up_node_count_8s"] == 2
    assert record["visible_follow_up_node_count_12s"] == 3
    assert record["follow_up_layer_count"] == 3


def test_opponent_handover_and_same_team_continuation_are_classified():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    b = bundle("b", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=14, family="PASS", x=20)
    c = bundle("c", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_B, actor=ACTOR_B, start=18, family="PASS", x=30)
    result = build([a, b, c], [], [])
    ordered_nodes = sorted(result["selected_action_nodes"], key=lambda n: float(n["start_candidate"]))
    by_anchor = {r["anchor_selected_action_node_id"]: r for r in result["selected_action_consequence_candidates"]}
    assert by_anchor[ordered_nodes[0]["selected_action_node_id"]]["primary_consequence_candidate"] == "SAME_TEAM_CONTINUATION_CANDIDATE"
    assert by_anchor[ordered_nodes[1]["selected_action_node_id"]]["primary_consequence_candidate"] == "OPPONENT_HANDOVER_CANDIDATE"


def test_shot_follow_up_is_visible_without_claiming_chance_quality():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    shot = bundle("s", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_B, start=14, family="SHOT", x=90)
    result = build([a, shot], [], [])
    first_node = min(result["selected_action_nodes"], key=lambda n: float(n["start_candidate"]))
    record = next(r for r in result["selected_action_consequence_candidates"] if r["anchor_selected_action_node_id"] == first_node["selected_action_node_id"])
    assert record["primary_consequence_candidate"] == "SHOT_FOLLOW_UP_CANDIDATE"
    assert record["consequence_candidate_is_causal_truth"] is False


def test_breakdown_and_recovery_response_are_classified():
    loss = bundle("loss", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="TURNOVER")
    recovery = bundle("rec", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_B, start=13, family="RECOVERY", x=20)
    result = build([loss, recovery], [], [])
    first_node = min(result["selected_action_nodes"], key=lambda n: float(n["start_candidate"]))
    record = next(r for r in result["selected_action_consequence_candidates"] if r["anchor_selected_action_node_id"] == first_node["selected_action_node_id"])
    assert record["primary_consequence_candidate"] == "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"


def test_terminal_and_derived_support_atoms_attach_only_on_exact_role_time_location():
    anchor = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="SHOT")
    terminal = atom("goal", role="PLAYER_SURFACE_CANDIDATE", start=10, atom_class="TERMINAL_OUTCOME_ATOM", label="goals")
    wrong_role = atom("team_goal", role="TEAM_SURFACE_CANDIDATE", start=10, atom_class="TERMINAL_OUTCOME_ATOM", label="goals")
    derived = atom("chance", role="PLAYER_SURFACE_CANDIDATE", start=10, atom_class="DERIVED_CONSEQUENCE_ATOM", label="chances created")
    result = build([anchor], [], [], [terminal, wrong_role, derived])
    node = result["selected_action_nodes"][0]
    assert node["terminal_outcome_support_visible"] is True
    assert node["derived_consequence_support_visible"] is True
    assert set(node["supporting_evidence_atom_ids"]) == {"goal", "chance"}
    assert result["selected_action_consequence_candidates"][0]["primary_consequence_candidate"] == "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"


def test_team_and_actor_profiles_are_generated():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    b = bundle("b", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=14, family="PASS", x=20)
    result = build([a, b], [], [])
    assert result["team_action_family_consequence_profile_count"] == 1
    assert result["actor_action_family_consequence_profile_count"] == 1
    assert result["team_action_family_consequence_profiles"][0]["selected_action_node_count"] == 2


def test_claim_boundaries_remain_closed():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    result = build([a], [], [])
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["event_instance_count"] == 0
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False
    assert result["phase_truth"] is False
    assert result["tactical_truth"] is False
    assert result["production_release"] is False


def test_invalid_module_id_fails_closed():
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    action, tax, rel, evidence = payloads([a])
    action["module_id"] = "wrong"
    result = build_selected_action_consequence_surface(action, tax, rel, evidence)
    assert result["status"] == "FAIL_CLOSED"
    assert "action_module_id_mismatch" in result["hard_block_hits"]


def test_nested_phone_output_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_outputs_are_written(tmp_path: Path):
    a = bundle("a", role="PLAYER_SURFACE_CANDIDATE", team=TEAM_A, actor=ACTOR_A, start=10, family="PASS")
    result = build([a], [], [])
    paths = write_outputs(result, tmp_path)
    assert all(path.exists() for path in paths.values())
    stored = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert stored["module_id"] == "selected_action_consequence_surface_lite_v1"


def test_no_sample_match_identity_leak():
    text = "\n".join(path.read_text(encoding="utf-8") for path in (MODULE_ROOT / "src").glob("*.py"))
    forbidden = ["Australia", "Turkey", "World Cup", "Galatasaray", "Juventus", "6935", "77798"]
    assert not any(item in text for item in forbidden)
