from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    build_action_occurrence_admission,
)

BINDING = "msb_" + "a" * 24


def bundle(
    bid: str,
    family: str,
    label: str,
    *,
    team: str,
    actor: str,
    status: str = "REVIEW_REQUIRED",
    start: object = "18.42",
    end: object = "30.42",
    x: object = "78.04",
    y: object = "64.76",
    period: str = "1",
) -> dict:
    return {
        "action_bundle_candidate_id": bid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": ["ea_" + bid],
        "provider_row_id_candidates": [bid],
        "raw_labels": [label],
        "normalized_labels": [label.casefold()],
        "bundle_status": status,
        "review_hits": ["same_surface_multiple_action_families"] if status == "REVIEW_REQUIRED" else [],
        "same_role_exact_grouping": True,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def taxonomy_record(rid: str, bundle_ids: list[str], families: list[str], *, team: str, actor: str) -> dict:
    return {
        "multi_family_review_record_id": rid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "18.42",
        "end_candidate": "30.42",
        "pos_x_candidate": "78.04",
        "pos_y_candidate": "64.76",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "family_set": sorted(families),
        "family_count": len(set(families)),
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
        "supporting_action_bundle_candidate_ids": bundle_ids,
        "supporting_evidence_atom_ids": ["ea_" + bid for bid in bundle_ids],
        "record_status": "PASS_CANDIDATE_CLASSIFICATION",
        "review_hits": [],
        "classification_is_event_truth": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(bundles: list[dict], taxonomy_records: list[dict]) -> tuple[dict, dict, dict]:
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
    taxonomy = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": taxonomy_records,
        "multi_family_review_core_count": len(taxonomy_records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    relation = {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "resolved_relation_candidates": [],
        "resolved_relation_candidate_count": 0,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return action, taxonomy, relation


def dribble_fixture() -> tuple[dict, dict, dict]:
    bundles = [
        bundle("a_dribble", "DRIBBLE", "Dribbles successful", team="team_us", actor="actor_berhalter"),
        bundle("a_duel", "DUEL", "Challenges won", team="team_us", actor="actor_berhalter"),
        bundle("a_final", "DRIBBLE", "Dribbling in the final third successful", team="team_us", actor="actor_berhalter"),
        bundle("b_duel", "DUEL", "Challenges unsuccessful", team="team_tr", actor="actor_baris"),
        bundle("b_tackle", "TACKLE", "Tackles unsuccessful", team="team_tr", actor="actor_baris"),
    ]
    taxonomy_records = [
        taxonomy_record("tax_a", ["a_dribble", "a_duel", "a_final"], ["DRIBBLE", "DUEL"], team="team_us", actor="actor_berhalter"),
        taxonomy_record("tax_b", ["b_duel", "b_tackle"], ["DUEL", "TACKLE"], team="team_tr", actor="actor_baris"),
    ]
    return payloads(bundles, taxonomy_records)


def test_exact_dribble_challenge_interaction_candidate() -> None:
    action, taxonomy, relation = dribble_fixture()
    result = build_action_occurrence_admission(action, taxonomy, relation)
    assert result["status"] == "PASS"
    assert result["action_occurrence_candidate_count"] == 1
    candidate = result["action_occurrence_candidates"][0]
    assert candidate["admission_class"] == "EXACT_COMPATIBLE"
    assert candidate["primary_family_candidate"] == "DRIBBLE"
    assert candidate["actor_identity_candidate_id"] == "actor_berhalter"
    assert candidate["opponent_identity_candidate_id"] == "actor_baris"
    assert candidate["attributes"]["final_third_candidate"] is True
    assert candidate["relation_bundle"]["challenge_result_candidate"] == "ACTOR_WON"
    assert candidate["relation_bundle"]["opponent_tackle_attempt_candidate"] == "UNSUCCESSFUL"
    assert len(candidate["supporting_action_bundle_candidate_ids"]) == 5


def test_same_interval_without_semantic_rule_not_admitted() -> None:
    bundles = [
        bundle("a_pass", "PASS", "Passes accurate", team="team_a", actor="actor_a", status="PASS"),
        bundle("b_pass", "PASS", "Passes accurate", team="team_b", actor="actor_b", status="PASS"),
    ]
    action, taxonomy, relation = payloads(bundles, [])
    result = build_action_occurrence_admission(action, taxonomy, relation)
    assert result["action_occurrence_candidate_count"] == 0


def test_same_team_player_pair_not_admitted() -> None:
    action, taxonomy, relation = dribble_fixture()
    for record in action["action_bundle_candidates"]:
        record["team_identity_candidate_id"] = "same_team"
    result = build_action_occurrence_admission(action, taxonomy, relation)
    assert result["action_occurrence_candidate_count"] == 0


def test_different_anchor_not_admitted_from_same_time_only() -> None:
    action, taxonomy, relation = dribble_fixture()
    for record in action["action_bundle_candidates"]:
        if record["actor_identity_candidate_id"] == "actor_baris":
            record["pos_x_candidate"] = "79.04"
    result = build_action_occurrence_admission(action, taxonomy, relation)
    assert result["action_occurrence_candidate_count"] == 0


def test_candidate_is_not_canonical_event() -> None:
    action, taxonomy, relation = dribble_fixture()
    result = build_action_occurrence_admission(action, taxonomy, relation)
    candidate = result["action_occurrence_candidates"][0]
    assert candidate["action_occurrence_candidate_is_event_truth"] is False
    assert candidate["validated_event_identity"] is False
    assert candidate["event_instance_allowed"] is False
    assert candidate["canonical_event_count"] == "UNKNOWN"
    assert candidate["true_action_count"] == "UNKNOWN"
    assert candidate["probability_output_allowed"] is False
    assert candidate["location"]["physical_player_position_truth"] is False
    assert candidate["temporal_relation"]["internal_order"] == "UNKNOWN"
    assert result["production_release"] is False


def test_source_row_order_not_chronology() -> None:
    action, taxonomy, relation = dribble_fixture()
    action["action_bundle_candidates"] = list(reversed(action["action_bundle_candidates"]))
    result = build_action_occurrence_admission(action, taxonomy, relation)
    assert result["action_occurrence_candidate_count"] == 1
    assert result["source_row_order_is_temporal_truth"] is False
    assert result["same_time_total_order_allowed"] is False


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/action_occurrence_admission_lite/src/action_occurrence_admission.py"
    ).read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Berhalter", "Baris")
    assert not any(token in source for token in forbidden)
