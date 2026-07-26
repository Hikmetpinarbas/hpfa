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
    bundle_id: str,
    source_role: str,
    *,
    family: str = "PASS",
    status: str = "PASS",
    team_id: str = "teamc_alpha",
    actor_id: str | None = "actorc_alpha_7",
    period: str = "1",
    start: object = "12.0",
    end: object = "12.4",
    x: object = "50.0",
    y: object = "30.0",
    coordinate_status: str = "COORDINATE_PRESENT",
) -> dict[str, object]:
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": source_role,
        "team_identity_candidate_id": team_id,
        "actor_identity_candidate_id": (
            None if source_role == "TEAM_SURFACE_CANDIDATE" else actor_id
        ),
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": coordinate_status,
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": [f"ea_{bundle_id}"],
        "provider_row_id_candidates": [bundle_id],
        "raw_labels": [family.title()],
        "normalized_labels": [family.casefold()],
        "bundle_status": status,
        "review_hits": (
            ["same_surface_multiple_action_families"]
            if status == "REVIEW_REQUIRED"
            else []
        ),
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
    }


def relation(
    relation_id: str,
    first_id: str,
    second_id: str,
    *,
    roles: list[str] | None = None,
) -> dict[str, object]:
    return {
        "cross_role_relation_candidate_id": relation_id,
        "match_surface_binding_id": BINDING,
        "action_bundle_candidate_ids": [first_id, second_id],
        "source_roles": roles
        or ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
        "relation_status": "CANDIDATE_EXACT_SURFACE_OVERLAP_NOT_FUSED",
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
    }


def taxonomy_record(
    record_id: str,
    supporting_bundles: list[dict[str, object]],
    *,
    status: str = "PASS_CANDIDATE_CLASSIFICATION",
) -> dict[str, object]:
    first = supporting_bundles[0]
    families = sorted({str(item["action_family_candidate"]) for item in supporting_bundles})
    return {
        "multi_family_review_record_id": record_id,
        "match_surface_binding_id": BINDING,
        "source_role": first["source_role"],
        "team_identity_candidate_id": first["team_identity_candidate_id"],
        "actor_identity_candidate_id": first["actor_identity_candidate_id"],
        "period_candidate": first["period_candidate"],
        "start_candidate": f"{float(first['start_candidate']):.6f}",
        "end_candidate": f"{float(first['end_candidate']):.6f}",
        "pos_x_candidate": (
            None if first["pos_x_candidate"] is None else f"{float(first['pos_x_candidate']):.6f}"
        ),
        "pos_y_candidate": (
            None if first["pos_y_candidate"] is None else f"{float(first['pos_y_candidate']):.6f}"
        ),
        "coordinate_evidence_status": first["coordinate_evidence_status"],
        "family_set": families,
        "family_count": len(families),
        "classification": (
            "RESTART_ACTION_COUPLING_CANDIDATE"
            if status == "PASS_CANDIDATE_CLASSIFICATION"
            else "SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED"
        ),
        "classification_rule_id": "TEST_RULE",
        "parent_family_candidate": None,
        "subtype_family_candidates": [],
        "supporting_action_bundle_candidate_ids": [
            str(item["action_bundle_candidate_id"]) for item in supporting_bundles
        ],
        "supporting_evidence_atom_ids": [
            f"ea_{item['action_bundle_candidate_id']}" for item in supporting_bundles
        ],
        "raw_labels": [],
        "normalized_labels": [],
        "record_status": status,
        "review_hits": [] if status == "PASS_CANDIDATE_CLASSIFICATION" else ["review"],
        "classification_is_event_truth": False,
        "family_parent_is_validated_action": False,
        "subtype_is_validated_action": False,
        "restart_coupling_is_event_fusion": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "MULTI_FAMILY_REVIEW_TAXONOMY_ONLY",
    }


def action_payload(
    bundles: list[dict[str, object]],
    relations: list[dict[str, object]],
    *,
    status: str = "PASS",
) -> dict[str, object]:
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": status,
        "module_status": status,
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "action_bundle_pass_count": sum(item["bundle_status"] == "PASS" for item in bundles),
        "action_bundle_review_required_count": sum(
            item["bundle_status"] == "REVIEW_REQUIRED" for item in bundles
        ),
        "cross_role_relation_candidates": relations,
        "cross_role_relation_candidate_count": len(relations),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def taxonomy_payload(
    records: list[dict[str, object]],
    bundles: list[dict[str, object]],
    *,
    status: str = "PASS",
) -> dict[str, object]:
    review_count = sum(item["bundle_status"] == "REVIEW_REQUIRED" for item in bundles)
    return {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": status,
        "module_status": status,
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": records,
        "multi_family_review_core_count": len(records),
        "source_review_bundle_record_count": review_count,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def build(
    bundles: list[dict[str, object]],
    relations: list[dict[str, object]],
    records: list[dict[str, object]] | None = None,
    *,
    action_status: str = "PASS",
    taxonomy_status: str = "PASS",
) -> dict[str, object]:
    return build_cross_role_relation_candidate_resolver(
        action_payload(bundles, relations, status=action_status),
        taxonomy_payload(records or [], bundles, status=taxonomy_status),
    )


def classified_context_fixture(
    *,
    record_status: str = "PASS_CANDIDATE_CLASSIFICATION",
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    player_pass = bundle(
        "player_pass",
        "PLAYER_SURFACE_CANDIDATE",
        family="PASS",
        status="REVIEW_REQUIRED",
    )
    player_restart = bundle(
        "player_restart",
        "PLAYER_SURFACE_CANDIDATE",
        family="RESTART",
        status="REVIEW_REQUIRED",
    )
    team_pass = bundle(
        "team_pass",
        "TEAM_SURFACE_CANDIDATE",
        family="PASS",
        status="REVIEW_REQUIRED",
    )
    team_restart = bundle(
        "team_restart",
        "TEAM_SURFACE_CANDIDATE",
        family="RESTART",
        status="REVIEW_REQUIRED",
    )
    bundles = [player_pass, player_restart, team_pass, team_restart]
    records = [
        taxonomy_record(
            "tax_player",
            [player_pass, player_restart],
            status=record_status,
        ),
        taxonomy_record(
            "tax_team",
            [team_pass, team_restart],
            status=record_status,
        ),
    ]
    relations = [relation("rel", "player_pass", "team_pass")]
    return bundles, records, relations


def test_exact_player_team_clear_relation() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "PASS"
    record = result["resolved_relation_candidates"][0]
    assert record["relation_classification"] == "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLEAR"
    assert record["relation_record_status"] == "PASS_CANDIDATE_CLASSIFICATION"


def test_exact_goalkeeper_team_clear_relation() -> None:
    bundles = [
        bundle("gk", "GOALKEEPER_SURFACE_CANDIDATE", actor_id="actorc_gk"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    rel = relation(
        "rel",
        "gk",
        "team",
        roles=["GOALKEEPER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
    )
    result = build(bundles, [rel])
    record = result["resolved_relation_candidates"][0]
    assert record["relation_classification"] == "EXACT_GOALKEEPER_TEAM_REFLECTION_CANDIDATE_CLEAR"


def test_classified_multi_family_context_clears_relation_candidate_only() -> None:
    bundles, records, relations = classified_context_fixture()
    result = build(
        bundles,
        relations,
        records,
        action_status="REVIEW_REQUIRED",
        taxonomy_status="REVIEW_REQUIRED",
    )
    assert result["hard_block_hits"] == []
    record = result["resolved_relation_candidates"][0]
    assert record["relation_classification"] == "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLASSIFIED_CONTEXT"
    assert record["relation_record_status"] == "PASS_CANDIDATE_CLASSIFICATION"
    assert record["taxonomy_context_record_ids"] == ["tax_player", "tax_team"]
    assert record["double_count_suppression_is_final"] is False


def test_unresolved_taxonomy_context_stays_review_required() -> None:
    bundles, records, relations = classified_context_fixture(record_status="REVIEW_REQUIRED")
    result = build(
        bundles,
        relations,
        records,
        action_status="REVIEW_REQUIRED",
        taxonomy_status="REVIEW_REQUIRED",
    )
    record = result["resolved_relation_candidates"][0]
    assert record["relation_classification"] == "REVIEW_REQUIRED_PLAYER_TEAM_UNRESOLVED_CONTEXT"
    assert record["relation_record_status"] == "REVIEW_REQUIRED"


def test_taxonomy_wrong_actor_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["actor_identity_candidate_id"] = "actorc_wrong"
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:actor_identity_candidate_id" in hit for hit in result["hard_block_hits"])


def test_taxonomy_wrong_team_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["team_identity_candidate_id"] = "teamc_wrong"
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:team_identity_candidate_id" in hit for hit in result["hard_block_hits"])


def test_taxonomy_wrong_period_time_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["period_candidate"] = "2"
    records[0]["start_candidate"] = "13.000000"
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:period_candidate" in hit for hit in result["hard_block_hits"])
    assert any("taxonomy_bundle_core_mismatch:start_candidate" in hit for hit in result["hard_block_hits"])


def test_taxonomy_wrong_coordinate_and_status_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["pos_x_candidate"] = "51.000000"
    records[0]["coordinate_evidence_status"] = "COORDINATE_MISSING"
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:pos_x_candidate" in hit for hit in result["hard_block_hits"])
    assert any("taxonomy_bundle_core_mismatch:coordinate_evidence_status" in hit for hit in result["hard_block_hits"])


def test_taxonomy_wrong_source_role_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["source_role"] = "TEAM_SURFACE_CANDIDATE"
    records[0]["actor_identity_candidate_id"] = None
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_core_mismatch:source_role" in hit for hit in result["hard_block_hits"])


def test_taxonomy_family_set_mismatch_with_valid_bundle_ids_fails_closed() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["family_set"] = ["PASS", "SHOT"]
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_bundle_family_set_mismatch" in hit for hit in result["hard_block_hits"])


def test_one_taxonomy_record_cannot_claim_cross_role_cores() -> None:
    bundles, _, relations = classified_context_fixture()
    bad = taxonomy_record("tax_bad", bundles)
    result = build(bundles, relations, [bad])
    assert result["status"] == "FAIL_CLOSED"
    assert any("taxonomy_supporting_bundles_not_single_exact_core" in hit for hit in result["hard_block_hits"])


def test_unrelated_pass_taxonomy_record_cannot_clear_relation() -> None:
    bundles, records, relations = classified_context_fixture()
    records[0]["actor_identity_candidate_id"] = "actorc_unrelated"
    records[0]["record_status"] = "PASS_CANDIDATE_CLASSIFICATION"
    result = build(bundles, relations, records)
    assert result["status"] == "FAIL_CLOSED"
    assert result["candidate_clear_relation_count"] == 0


def test_duplicate_relation_id_fails_closed() -> None:
    bundles = [
        bundle("p1", "PLAYER_SURFACE_CANDIDATE", actor_id="a1", start="1"),
        bundle("t1", "TEAM_SURFACE_CANDIDATE", start="1"),
        bundle("p2", "PLAYER_SURFACE_CANDIDATE", actor_id="a2", start="2"),
        bundle("t2", "TEAM_SURFACE_CANDIDATE", start="2"),
    ]
    result = build(
        bundles,
        [relation("dup", "p1", "t1"), relation("dup", "p2", "t2")],
    )
    assert result["status"] == "FAIL_CLOSED"


def test_missing_bundle_reference_fails_closed() -> None:
    bundles = [bundle("player", "PLAYER_SURFACE_CANDIDATE")]
    result = build(bundles, [relation("rel", "player", "missing")])
    assert result["status"] == "FAIL_CLOSED"


def test_bundle_reuse_across_relations_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team1", "TEAM_SURFACE_CANDIDATE"),
        bundle("team2", "TEAM_SURFACE_CANDIDATE"),
    ]
    result = build(
        bundles,
        [relation("r1", "player", "team1"), relation("r2", "player", "team2")],
    )
    assert result["status"] == "FAIL_CLOSED"


def test_same_time_different_team_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE", team_id="team_a"),
        bundle("team", "TEAM_SURFACE_CANDIDATE", team_id="team_b"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "FAIL_CLOSED"


def test_same_time_different_coordinate_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE", x="50"),
        bundle("team", "TEAM_SURFACE_CANDIDATE", x="51"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "FAIL_CLOSED"


def test_family_mismatch_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE", family="PASS"),
        bundle("team", "TEAM_SURFACE_CANDIDATE", family="SHOT"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "FAIL_CLOSED"


def test_missing_primary_actor_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE", actor_id=None),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "FAIL_CLOSED"


def test_actor_on_team_side_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    bundles[1]["actor_identity_candidate_id"] = "invented_actor"
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["status"] == "FAIL_CLOSED"


def test_source_role_pair_outside_allowlist_fails_closed() -> None:
    bundles = [
        bundle("p1", "PLAYER_SURFACE_CANDIDATE", actor_id="a1"),
        bundle("p2", "PLAYER_SURFACE_CANDIDATE", actor_id="a2"),
    ]
    rel = relation(
        "rel",
        "p1",
        "p2",
        roles=["PLAYER_SURFACE_CANDIDATE", "PLAYER_SURFACE_CANDIDATE"],
    )
    result = build(bundles, [rel])
    assert result["status"] == "FAIL_CLOSED"


def test_relation_status_contract_mismatch_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    rel = relation("rel", "player", "team")
    rel["relation_status"] = "OTHER"
    result = build(bundles, [rel])
    assert result["status"] == "FAIL_CLOSED"


def test_missing_coordinate_stays_review_required_not_exact_clear() -> None:
    bundles = [
        bundle(
            "player",
            "PLAYER_SURFACE_CANDIDATE",
            x=None,
            y=None,
            coordinate_status="COORDINATE_MISSING",
        ),
        bundle(
            "team",
            "TEAM_SURFACE_CANDIDATE",
            x=None,
            y=None,
            coordinate_status="COORDINATE_MISSING",
        ),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    record = result["resolved_relation_candidates"][0]
    assert record["relation_record_status"] == "REVIEW_REQUIRED"


def test_taxonomy_review_bundle_coverage_mismatch_fails_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE", status="REVIEW_REQUIRED"),
        bundle("team", "TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED"),
    ]
    result = build(bundles, [relation("rel", "player", "team")], [])
    assert result["status"] == "FAIL_CLOSED"


def test_relation_output_and_double_count_candidate_counts_reconcile() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["source_cross_role_relation_candidate_count"] == 1
    assert result["resolved_relation_candidate_count"] == 1
    assert result["candidate_clear_relation_count"] == 1
    assert result["double_count_suppression_candidate_count"] == 1


def test_claim_boundaries_remain_closed() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    result = build(bundles, [relation("rel", "player", "team")])
    assert result["relation_candidate_is_event_truth"] is False
    assert result["reflection_equivalence_truth"] is False
    assert result["double_count_suppression_is_final"] is False
    assert result["count_value_output_allowed"] is False
    assert result["cross_role_fusion_allowed"] is False
    assert result["event_instance_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_inputs_are_not_mutated() -> None:
    bundles = [
        bundle("player", "PLAYER_SURFACE_CANDIDATE"),
        bundle("team", "TEAM_SURFACE_CANDIDATE"),
    ]
    action = action_payload(bundles, [relation("rel", "player", "team")])
    taxonomy = taxonomy_payload([], bundles)
    original_action = copy.deepcopy(action)
    original_taxonomy = copy.deepcopy(taxonomy)
    build_cross_role_relation_candidate_resolver(action, taxonomy)
    assert action == original_action
    assert taxonomy == original_taxonomy


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/cross_role_relation_candidate_resolver_lite/src/"
        "cross_role_relation_candidate_resolver.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "Australia",
        "Turkey",
        "World Cup",
        "Juventus",
        "Galatasaray",
        "6935",
        "77798",
    )
    assert not any(token in source for token in forbidden)
