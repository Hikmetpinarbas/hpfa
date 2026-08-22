from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.trackable_action_trace_candidates import (
    build_trackable_action_trace_candidates,
    validate_out,
)

BINDING = "msb_" + "a" * 24


def atom(atom_id: str, role: str) -> dict[str, object]:
    short = {
        "PLAYER_SURFACE_CANDIDATE": "PLAYER",
        "GOALKEEPER_SURFACE_CANDIDATE": "GOALKEEPER",
        "TEAM_SURFACE_CANDIDATE": "TEAM",
    }[role]
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "atom_status": "PASS",
        "source_lineage_records": [
            {
                "source_file": f"surface_{short.lower()}.csv",
                "source_format": "csv",
                "source_role": short,
                "source_row_index": 1,
                "source_row_index_is_order_truth": False,
                "source_sha256": "1" * 64,
            },
            {
                "source_file": f"surface_{short.lower()}.xml",
                "source_format": "xml",
                "source_role": short,
                "source_row_index": 1,
                "source_row_index_is_order_truth": False,
                "source_sha256": "2" * 64,
            },
        ],
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def bundle(
    bundle_id: str,
    role: str,
    family: str = "PASS",
    *,
    status: str = "PASS",
    actor: str | None = "actorc_1",
    start: str = "10",
    x: str = "50",
    y: str = "40",
) -> dict[str, object]:
    if role == "TEAM_SURFACE_CANDIDATE":
        actor = None
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "team_identity_candidate_id": "teamc_1",
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": start,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": [f"ea_{bundle_id}"],
        "provider_row_id_candidates": [bundle_id],
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


def taxonomy_record(record_id: str, bundle_ids: list[str], status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict[str, object]:
    return {
        "multi_family_review_record_id": record_id,
        "match_surface_binding_id": BINDING,
        "source_role": "GOALKEEPER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "teamc_1",
        "actor_identity_candidate_id": "actorc_1",
        "period_candidate": "1",
        "start_candidate": "10.000000",
        "end_candidate": "10.000000",
        "pos_x_candidate": "50.000000",
        "pos_y_candidate": "40.000000",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "family_set": ["DUEL", "TACKLE"],
        "family_count": 2,
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
        "classification_rule_id": "MFRT_EXACT_DUEL_TACKLE_V1",
        "parent_family_candidate": "DUEL",
        "subtype_family_candidates": ["TACKLE"],
        "supporting_action_bundle_candidate_ids": bundle_ids,
        "supporting_evidence_atom_ids": [f"ea_{item}" for item in bundle_ids],
        "record_status": status,
        "review_hits": [] if status == "PASS_CANDIDATE_CLASSIFICATION" else ["unresolved"],
        "classification_is_event_truth": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def relation(
    relation_id: str,
    primary_id: str,
    team_id: str,
    *,
    status: str = "PASS_CANDIDATE_CLASSIFICATION",
    classification: str = "EXACT_PLAYER_TEAM_REFLECTION_CANDIDATE_CLEAR",
) -> dict[str, object]:
    return {
        "resolved_relation_candidate_id": relation_id,
        "source_relation_candidate_id": "src_" + relation_id,
        "match_surface_binding_id": BINDING,
        "relation_classification": classification,
        "relation_record_status": status,
        "source_roles": ["PLAYER_SURFACE_CANDIDATE", "TEAM_SURFACE_CANDIDATE"],
        "team_identity_candidate_id": "teamc_1",
        "actor_identity_candidate_id": "actorc_1",
        "period_candidate": "1",
        "start_candidate": "10",
        "end_candidate": "10",
        "pos_x_candidate": "50",
        "pos_y_candidate": "40",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": "PASS",
        "primary_action_bundle_candidate_id": primary_id,
        "reflection_action_bundle_candidate_id": team_id,
        "taxonomy_context_record_ids": [],
        "double_count_suppression_candidate_state": (
            "CANDIDATE_PRIMARY_ROLE_ONLY" if status == "PASS_CANDIDATE_CLASSIFICATION" else "REVIEW_REQUIRED_CONTEXT_UNRESOLVED"
        ),
        "relation_candidate_is_event_truth": False,
        "reflection_equivalence_truth": False,
        "double_count_suppression_is_final": False,
        "count_value_output_allowed": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(
    bundles: list[dict[str, object]],
    relations: list[dict[str, object]] | None = None,
    taxonomy: list[dict[str, object]] | None = None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    relations = relations or []
    taxonomy = taxonomy or []
    roles_by_atom = {
        str(b["supporting_evidence_atom_ids"][0]): str(b["source_role"])
        for b in bundles
    }
    atoms = [atom(atom_id, role) for atom_id, role in roles_by_atom.items()]
    action = {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    tax = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": taxonomy,
        "multi_family_review_core_count": len(taxonomy),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    rel = {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "resolved_relation_candidates": relations,
        "resolved_relation_candidate_count": len(relations),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    evidence = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return action, tax, rel, evidence


def build(*args: object) -> dict[str, object]:
    return build_trackable_action_trace_candidates(*args)  # type: ignore[arg-type]


def test_clear_player_team_relation_selects_primary_and_keeps_team_context_only() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    data = payloads([p, t], [relation("r1", "p1", "t1")])
    result = build(*data)
    assert result["selected_primary_surface_candidate_count"] == 1
    assert result["reflection_context_surface_candidate_count"] == 1
    assert result["quarantined_surface_candidate_count"] == 0
    assert result["trackable_action_trace_candidate_count"] == 1
    trace = result["trackable_action_trace_candidates"][0]
    assert trace["source_role"] == "PLAYER_SURFACE_CANDIDATE"
    assert trace["reflection_context_action_bundle_candidate_ids"] == ["t1"]
    assert trace["team_reflection_context_visible"] is True


def test_review_relation_quarantines_both_surfaces() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE", status="REVIEW_REQUIRED")
    trp = taxonomy_record("tp", ["p1"], status="REVIEW_REQUIRED")
    trt = copy.deepcopy(trp)
    trt["multi_family_review_record_id"] = "tt"
    trt["source_role"] = "TEAM_SURFACE_CANDIDATE"
    trt["actor_identity_candidate_id"] = None
    trt["supporting_action_bundle_candidate_ids"] = ["t1"]
    trt["supporting_evidence_atom_ids"] = ["ea_t1"]
    data = payloads(
        [p, t],
        [relation("r1", "p1", "t1", status="REVIEW_REQUIRED", classification="REVIEW_REQUIRED_PLAYER_TEAM_UNRESOLVED_CONTEXT")],
        [trp, trt],
    )
    result = build(*data)
    assert result["selected_primary_surface_candidate_count"] == 0
    assert result["reflection_context_surface_candidate_count"] == 0
    assert result["quarantined_surface_candidate_count"] == 2
    assert result["trackable_action_trace_candidate_count"] == 0


def test_standalone_team_pass_is_never_primary_trace() -> None:
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    result = build(*payloads([t]))
    assert result["selected_primary_surface_candidate_count"] == 0
    assert result["quarantined_surface_candidate_count"] == 1
    assert result["quarantine_basis_counts"] == {
        "UNMATCHED_TEAM_SURFACE_NOT_PRIMARY_TRACE": 1
    }


def test_standalone_goalkeeper_pass_with_actor_is_trackable_candidate() -> None:
    g = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE")
    result = build(*payloads([g]))
    assert result["selected_primary_surface_candidate_count"] == 1
    assert result["standalone_primary_trace_candidate_count"] == 1
    assert result["trackable_action_trace_candidates"][0]["source_role"] == "GOALKEEPER_SURFACE_CANDIDATE"


def test_classified_multi_family_primary_can_enrich_one_trace_without_event_promotion() -> None:
    g1 = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE", "DUEL", status="REVIEW_REQUIRED")
    g2 = bundle("g2", "GOALKEEPER_SURFACE_CANDIDATE", "TACKLE", status="REVIEW_REQUIRED")
    tax = taxonomy_record("tax1", ["g1", "g2"])
    result = build(*payloads([g1, g2], taxonomy=[tax]))
    assert result["selected_primary_surface_candidate_count"] == 2
    assert result["trackable_action_trace_candidate_count"] == 1
    assert result["same_surface_multi_family_trace_candidate_count"] == 1
    trace = result["trackable_action_trace_candidates"][0]
    assert trace["action_family_candidates"] == ["DUEL", "TACKLE"]
    assert trace["trackable_action_candidate_is_event_truth"] is False


def test_unresolved_multi_family_primary_stays_quarantined() -> None:
    g1 = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE", "DUEL", status="REVIEW_REQUIRED")
    g2 = bundle("g2", "GOALKEEPER_SURFACE_CANDIDATE", "TACKLE", status="REVIEW_REQUIRED")
    tax = taxonomy_record("tax1", ["g1", "g2"], status="REVIEW_REQUIRED")
    result = build(*payloads([g1, g2], taxonomy=[tax]))
    assert result["selected_primary_surface_candidate_count"] == 0
    assert result["quarantined_surface_candidate_count"] == 2


def test_partition_is_complete_without_duplicate_assignment() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    g = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE", start="20")
    result = build(*payloads([p, t, g], [relation("r1", "p1", "t1")]))
    assert result["selection_partition_complete"] is True
    assert result["selection_partition_coverage_count"] == 3


def test_trace_contains_primary_and_reflection_lineage_without_source_row_order_truth() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    result = build(*payloads([p, t], [relation("r1", "p1", "t1")]))
    trace = result["trackable_action_trace_candidates"][0]
    assert len(trace["primary_source_lineage_records"]) == 2
    assert len(trace["reflection_source_lineage_records"]) == 2
    assert all(
        item["source_row_index_is_order_truth"] is False
        for item in trace["primary_source_lineage_records"] + trace["reflection_source_lineage_records"]
    )


def test_evidence_source_role_mismatch_fails_closed() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    action, tax, rel, evidence = payloads([p])
    evidence["evidence_atoms"][0]["source_role"] = "TEAM_SURFACE_CANDIDATE"
    result = build(action, tax, rel, evidence)
    assert result["status"] == "FAIL_CLOSED"
    assert any("action_bundle_evidence_source_role_mismatch" in hit for hit in result["hard_block_hits"])


def test_relation_bundle_reuse_fails_closed() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    t1 = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    t2 = bundle("t2", "TEAM_SURFACE_CANDIDATE", start="20")
    data = payloads(
        [p, t1, t2],
        [relation("r1", "p1", "t1"), relation("r2", "p1", "t2")],
    )
    result = build(*data)
    assert result["status"] == "FAIL_CLOSED"
    assert any("relation_bundle_reused:p1" == hit for hit in result["hard_block_hits"])


def test_final_double_count_suppression_claim_fails_closed() -> None:
    p = bundle("p1", "PLAYER_SURFACE_CANDIDATE")
    t = bundle("t1", "TEAM_SURFACE_CANDIDATE")
    rel = relation("r1", "p1", "t1")
    rel["double_count_suppression_is_final"] = True
    result = build(*payloads([p, t], [rel]))
    assert result["status"] == "FAIL_CLOSED"
    assert any("relation_final_suppression_claimed" in hit for hit in result["hard_block_hits"])


def test_claim_and_next_layer_boundaries_remain_closed() -> None:
    g = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE")
    result = build(*payloads([g]))
    for key in (
        "trackable_action_candidate_is_event_truth",
        "physical_action_identity_truth",
        "trace_count_is_physical_action_count",
        "reflection_context_is_event_equivalence_truth",
        "final_double_count_suppression_admitted",
        "count_value_output_allowed",
        "consequence_classification_allowed",
        "sequence_link_allowed",
        "same_time_order_truth_admitted",
        "source_row_order_is_temporal_truth",
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


def test_input_payloads_are_not_mutated() -> None:
    g = bundle("g1", "GOALKEEPER_SURFACE_CANDIDATE")
    data = payloads([g])
    originals = copy.deepcopy(data)
    build(*data)
    assert data == originals


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/trackable_action_trace_candidates_lite/src/"
        "trackable_action_trace_candidates.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray"):
        assert token not in source
