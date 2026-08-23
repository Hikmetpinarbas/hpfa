from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hpfa.modules.core.cross_role_relation_candidate_resolver_lite.src.cross_role_relation_candidate_resolver import (
    build_cross_role_relation_candidate_resolver,
    validate_out,
)

BINDING = "msb_" + "a" * 24


def bundle(
    bid: str,
    family: str = "PASS",
    *,
    role: str = "PLAYER_SURFACE_CANDIDATE",
    status: str = "PASS",
    team: str = "teamc_one",
    actor: str | None = "actorc_one",
    period: str = "1",
    start: object = "10",
    end: object = "11",
    x: object = "20",
    y: object = "30",
) -> dict:
    return {
        "action_bundle_candidate_id": bid,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": None if role == "TEAM_SURFACE_CANDIDATE" else actor,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": ["ea_" + bid],
        "provider_row_id_candidates": [bid],
        "raw_labels": [family.title()],
        "normalized_labels": [family.casefold()],
        "bundle_status": status,
        "review_hits": ["same_surface_multiple_action_families"] if status == "REVIEW_REQUIRED" else [],
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def relation(rid: str, primary: str, team: str, roles: list[str] | None = None) -> dict:
    return {
        "cross_role_relation_candidate_id": rid,
        "match_surface_binding_id": BINDING,
        "action_bundle_candidate_ids": [primary, team],
        "source_roles": roles or ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
        "relation_status": "CANDIDATE_EXACT_SURFACE_OVERLAP_NOT_FUSED",
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def taxonomy_record(
    rid: str,
    bundle_ids: list[str],
    families: list[str],
    *,
    role: str,
    actor: str | None,
    status: str = "PASS_CANDIDATE_CLASSIFICATION",
    team: str = "teamc_one",
    period: str = "1",
    start: object = "10",
    end: object = "11",
    x: object = "20",
    y: object = "30",
) -> dict:
    return {
        "multi_family_review_record_id": rid,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": None if role == "TEAM_SURFACE_CANDIDATE" else actor,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "family_set": sorted(families),
        "family_count": len(set(families)),
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE" if status == "PASS_CANDIDATE_CLASSIFICATION" else "SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED",
        "supporting_action_bundle_candidate_ids": bundle_ids,
        "supporting_evidence_atom_ids": ["ea_" + bid for bid in bundle_ids],
        "record_status": status,
        "review_hits": [] if status == "PASS_CANDIDATE_CLASSIFICATION" else ["same_time_grouping_risk_review_required"],
        "classification_is_event_truth": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(bundles: list[dict], relations: list[dict], tax_records: list[dict]) -> tuple[dict, dict]:
    action = {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "action_bundle_pass_count": sum(b["bundle_status"] == "PASS" for b in bundles),
        "action_bundle_review_required_count": sum(b["bundle_status"] == "REVIEW_REQUIRED" for b in bundles),
        "cross_role_relation_candidates": relations,
        "cross_role_relation_candidate_count": len(relations),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    taxonomy = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": tax_records,
        "source_action_bundle_candidate_count": len(bundles),
        "source_review_bundle_record_count": sum(b["bundle_status"] == "REVIEW_REQUIRED" for b in bundles),
        "multi_family_review_core_count": len(tax_records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return action, taxonomy


def test_clear_player_team_exact_relation_is_candidate_only() -> None:
    p = bundle("p1")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE")
    action, taxonomy = payloads([p, t], [relation("r1", "p1", "t1")], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["resolved_relation_candidate_count"] == 1
    assert result["candidate_clear_relation_count"] == 1
    record = result["resolved_relation_candidates"][0]
    assert record["relation_classification"] == "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLEAR"
    assert record["relation_candidate_is_event_truth"] is False
    assert record["double_count_suppression_is_final"] is False


def test_goalkeeper_team_role_pair_is_supported() -> None:
    g = bundle("g1", role="GOALKEEPER_SURFACE_CANDIDATE", actor="actorc_gk")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE")
    rel = relation("r1", "g1", "t1", ["GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"])
    action, taxonomy = payloads([g, t], [rel], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["relation_classification_counts"] == {"EXACT_GOALKEEPER_TEAM_REFLECTION_CANDIDATE_CLEAR": 1}


def test_registered_taxonomy_context_can_clear_review_relation_candidate() -> None:
    p1 = bundle("p_pass", "PASS", status="REVIEW_REQUIRED")
    p2 = bundle("p_cross", "CROSS", status="REVIEW_REQUIRED")
    t1 = bundle("t_pass", "PASS", role="TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    t2 = bundle("t_cross", "CROSS", role="TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    rel = relation("r1", "p_pass", "t_pass")
    tax_p = taxonomy_record("tax_p", ["p_pass", "p_cross"], ["PASS", "CROSS"], role="PLAYER_SURFACE_CANDIDATE", actor="actorc_one")
    tax_t = taxonomy_record("tax_t", ["t_pass", "t_cross"], ["PASS", "CROSS"], role="TEAM_SURFACE_CANDIDATE", actor=None)
    action, taxonomy = payloads([p1, p2, t1, t2], [rel], [tax_p, tax_t])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["candidate_clear_relation_count"] == 1
    assert result["resolved_relation_candidates"][0]["relation_classification"] == "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT"


def test_unresolved_taxonomy_context_stays_review_required() -> None:
    p1 = bundle("p_pass", "PASS", status="REVIEW_REQUIRED")
    p2 = bundle("p_recovery", "RECOVERY", status="REVIEW_REQUIRED")
    t1 = bundle("t_pass", "PASS", role="TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    t2 = bundle("t_recovery", "RECOVERY", role="TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    rel = relation("r1", "p_pass", "t_pass")
    tax_p = taxonomy_record("tax_p", ["p_pass", "p_recovery"], ["PASS", "RECOVERY"], role="PLAYER_SURFACE_CANDIDATE", actor="actorc_one", status="REVIEW_REQUIRED")
    tax_t = taxonomy_record("tax_t", ["t_pass", "t_recovery"], ["PASS", "RECOVERY"], role="TEAM_SURFACE_CANDIDATE", actor=None, status="REVIEW_REQUIRED")
    action, taxonomy = payloads([p1, p2, t1, t2], [rel], [tax_p, tax_t])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["review_required_relation_count"] == 1
    assert "UNRESOLVED_CONTEXT" in result["resolved_relation_candidates"][0]["relation_classification"]


def test_exact_team_mismatch_fails_closed() -> None:
    p = bundle("p1", team="teamc_one")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE", team="teamc_two")
    action, taxonomy = payloads([p, t], [relation("r1", "p1", "t1")], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "FAIL_CLOSED"
    assert any("relation_exact_field_mismatch:team_identity_candidate_id" in hit for hit in result["hard_block_hits"])


def test_same_timestamp_alone_cannot_link_different_coordinates() -> None:
    p = bundle("p1", x="20", y="30")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE", x="21", y="30")
    action, taxonomy = payloads([p, t], [relation("r1", "p1", "t1")], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "FAIL_CLOSED"
    assert any("relation_exact_field_mismatch:pos_x_candidate" in hit for hit in result["hard_block_hits"])


def test_bundle_reuse_across_relations_fails_closed() -> None:
    p = bundle("p1")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE")
    rels = [relation("r1", "p1", "t1"), relation("r2", "p1", "t1")]
    action, taxonomy = payloads([p, t], rels, [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "FAIL_CLOSED"
    assert any("relation_bundle_reused" in hit for hit in result["hard_block_hits"])


def test_taxonomy_must_cover_every_review_bundle_exactly_once() -> None:
    p1 = bundle("p_pass", "PASS", status="REVIEW_REQUIRED")
    p2 = bundle("p_cross", "CROSS", status="REVIEW_REQUIRED")
    action, taxonomy = payloads([p1, p2], [], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "FAIL_CLOSED"
    assert "taxonomy_review_bundle_coverage_mismatch" in result["hard_block_hits"]


def test_taxonomy_core_mismatch_fails_closed() -> None:
    p1 = bundle("p_pass", "PASS", status="REVIEW_REQUIRED")
    p2 = bundle("p_cross", "CROSS", status="REVIEW_REQUIRED")
    tax = taxonomy_record("tax_p", ["p_pass", "p_cross"], ["PASS", "CROSS"], role="PLAYER_SURFACE_CANDIDATE", actor="actorc_one", x="99")
    action, taxonomy = payloads([p1, p2], [], [tax])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:pos_x_candidate" in hit for hit in result["hard_block_hits"])


def test_inputs_are_not_mutated() -> None:
    p = bundle("p1")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE")
    action, taxonomy = payloads([p, t], [relation("r1", "p1", "t1")], [])
    before_a = copy.deepcopy(action)
    before_t = copy.deepcopy(taxonomy)
    build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert action == before_a
    assert taxonomy == before_t


def test_claim_and_order_boundaries_remain_closed() -> None:
    p = bundle("p1")
    t = bundle("t1", role="TEAM_SURFACE_CANDIDATE")
    action, taxonomy = payloads([p, t], [relation("r1", "p1", "t1")], [])
    result = build_cross_role_relation_candidate_resolver(action, taxonomy)
    for key in (
        "same_time_only_link_allowed",
        "source_row_order_is_temporal_truth",
        "relation_candidate_is_event_truth",
        "reflection_equivalence_truth",
        "double_count_suppression_is_final",
        "count_value_output_allowed",
        "cross_role_fusion_allowed",
        "claim_allowed",
        "sequence_truth",
        "possession_truth",
        "phase_truth",
        "tactical_truth",
        "production_release",
    ):
        assert result[key] is False
    assert result["event_instance_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/cross_role_relation_candidate_resolver_lite/src/"
        "cross_role_relation_candidate_resolver.py"
    ).read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray")
    assert not any(token in source for token in forbidden)
