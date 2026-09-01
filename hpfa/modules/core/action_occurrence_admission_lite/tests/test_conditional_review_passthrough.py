from __future__ import annotations

import copy

from hpfa.modules.core.action_occurrence_admission_lite.src.conditional_review_passthrough import (
    build_action_occurrence_admission_with_conditional_review,
)

BINDING = "msb_" + "c" * 24

RULE_BY_LABEL = {
    "Dribbles successful": "plvs_v2_dribbles_successful",
    "Dribbling in the final third successful": "plvs_v2_dribbling_in_the_final_third_successful",
    "Challenges won": "plvs_v2_challenges_won",
    "Challenges unsuccessful": "plvs_v2_challenges_unsuccessful",
    "Tackles unsuccessful": "plvs_v2_tackles_unsuccessful",
    "Challenges": "plvs_v2_token_duel",
    "Lost balls": "plvs_v2_lost_balls",
}


def bundle(bid: str, family: str, label: str, *, team: str, actor: str) -> dict:
    return {
        "action_bundle_candidate_id": bid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "44.10",
        "end_candidate": "56.10",
        "pos_x_candidate": "70.00",
        "pos_y_candidate": "30.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": ["ea_" + bid],
        "provider_row_id_candidates": [bid],
        "raw_labels": [label],
        "normalized_labels": [label.casefold()],
        "bundle_status": "REVIEW_REQUIRED",
        "review_hits": ["same_surface_multiple_action_families"],
        "same_role_exact_grouping": True,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def taxonomy_record(
    rid: str,
    bundle_ids: list[str],
    families: list[str],
    *,
    team: str,
    actor: str,
    classification: str,
    status: str,
) -> dict:
    return {
        "multi_family_review_record_id": rid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "44.10",
        "end_candidate": "56.10",
        "pos_x_candidate": "70.00",
        "pos_y_candidate": "30.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "family_set": sorted(families),
        "family_count": len(set(families)),
        "classification": classification,
        "supporting_action_bundle_candidate_ids": bundle_ids,
        "supporting_evidence_atom_ids": ["ea_" + bid for bid in bundle_ids],
        "record_status": status,
        "review_hits": [] if status == "PASS_CANDIDATE_CLASSIFICATION" else ["compound_review_required"],
        "classification_is_event_truth": False,
        "cross_role_fusion_allowed": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def evidence_payload(bundles: list[dict], *, bad_rule_for: str | None = None) -> dict:
    atoms = []
    for row in bundles:
        label = row["raw_labels"][0]
        rule_id = RULE_BY_LABEL.get(label, "plvs_v2_unknown")
        if row["action_bundle_candidate_id"] == bad_rule_for:
            rule_id = "wrong_provider_rule"
        atoms.append({
            "evidence_atom_id": row["supporting_evidence_atom_ids"][0],
            "match_surface_binding_id": BINDING,
            "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
            "semantic_rule_id": rule_id,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        })
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def payloads(*, support_label: bool = True, complex_primary: bool = False, include_counterpart: bool = True):
    primary = [bundle("a_dribble", "DRIBBLE", "Dribbles successful", team="team_a", actor="actor_a")]
    if support_label:
        primary.append(bundle("a_duel", "DUEL", "Challenges won", team="team_a", actor="actor_a"))
    else:
        primary.append(bundle("a_duel", "DUEL", "Challenges", team="team_a", actor="actor_a"))
    if complex_primary:
        primary.append(bundle("a_turnover", "TURNOVER", "Lost balls", team="team_a", actor="actor_a"))

    counterpart = []
    if include_counterpart:
        counterpart = [
            bundle("b_duel", "DUEL", "Challenges unsuccessful", team="team_b", actor="actor_b"),
            bundle("b_tackle", "TACKLE", "Tackles unsuccessful", team="team_b", actor="actor_b"),
        ]

    bundles = primary + counterpart
    primary_families = ["DRIBBLE", "DUEL"] + (["TURNOVER"] if complex_primary else [])
    primary_classification = (
        "MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED"
        if complex_primary
        else "COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED"
    )
    records = [
        taxonomy_record(
            "tax_a",
            [row["action_bundle_candidate_id"] for row in primary],
            primary_families,
            team="team_a",
            actor="actor_a",
            classification=primary_classification,
            status="REVIEW_REQUIRED",
        )
    ]
    if counterpart:
        records.append(
            taxonomy_record(
                "tax_b",
                [row["action_bundle_candidate_id"] for row in counterpart],
                ["DUEL", "TACKLE"],
                team="team_b",
                actor="actor_b",
                classification="HIERARCHICAL_SUBTYPE_CANDIDATE",
                status="PASS_CANDIDATE_CLASSIFICATION",
            )
        )

    action = {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": bundles,
        "action_bundle_candidate_count": len(bundles),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    taxonomy = {
        "module_id": "action_bundle_multi_family_review_taxonomy_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "multi_family_review_records": records,
        "multi_family_review_core_count": len(records),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    relation = {
        "module_id": "cross_role_relation_candidate_resolver_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "resolved_relation_candidates": [],
        "resolved_relation_candidate_count": 0,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    evidence = evidence_payload(bundles)
    return action, taxonomy, relation, evidence


def test_compound_dribble_duel_review_can_be_admitted_with_exact_counterpart() -> None:
    action, taxonomy, relation, evidence = payloads()
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["action_occurrence_candidate_count"] == 1
    assert result["conditional_review_passthrough_candidate_count"] == 1
    candidate = result["action_occurrence_candidates"][0]
    assert candidate["conditional_review_passthrough_used"] is True
    assert candidate["upstream_taxonomy_truth_changed"] is False
    assert candidate["provider_semantics_binding_status"] == "PASS"
    assert candidate["provider_semantics_registry_id"] == "sportsbase_label_semantics_reviewed_v2"
    assert "plvs_v2_dribbles_successful" in candidate["supporting_semantic_rule_ids"]
    provenance = candidate["conditional_review_passthrough_provenance"]
    assert provenance[0]["original_record_status"] == "REVIEW_REQUIRED"
    assert provenance[0]["original_classification"] == "COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED"


def test_compound_review_without_challenges_won_is_not_admitted() -> None:
    action, taxonomy, relation, evidence = payloads(support_label=False)
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["conditional_review_passthrough_record_count"] == 0
    assert result["action_occurrence_candidate_count"] == 0


def test_multi_family_complex_review_remains_withheld() -> None:
    action, taxonomy, relation, evidence = payloads(complex_primary=True)
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["conditional_review_passthrough_record_count"] == 0
    assert result["action_occurrence_candidate_count"] == 0


def test_no_counterpart_means_no_occurrence_candidate() -> None:
    action, taxonomy, relation, evidence = payloads(include_counterpart=False)
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["conditional_review_passthrough_record_count"] == 1
    assert result["action_occurrence_candidate_count"] == 0


def test_passthrough_does_not_mutate_upstream_payloads() -> None:
    action, taxonomy, relation, evidence = payloads()
    before = copy.deepcopy((action, taxonomy, relation, evidence))
    build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert (action, taxonomy, relation, evidence) == before


def test_wrong_provider_semantic_rule_is_not_admitted() -> None:
    action, taxonomy, relation, evidence = payloads()
    evidence = evidence_payload(action["action_bundle_candidates"], bad_rule_for="a_dribble")
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["action_occurrence_candidate_count"] == 0
    assert result["candidate_rejected_provider_semantics_binding_count"] == 1
    assert "candidate_rejected_provider_semantics_binding" in result["review_hits"]


def test_missing_evidence_payload_fails_closed() -> None:
    action, taxonomy, relation, _ = payloads()
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation)
    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == ["provider_semantics_evidence_missing"]


def test_source_row_order_truth_input_fails_closed() -> None:
    action, taxonomy, relation, evidence = payloads()
    action["action_bundle_candidates"][0]["source_row_order_is_temporal_truth"] = True
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["status"] == "FAIL_CLOSED"
    assert "unsafe_source_row_order_truth_admitted" in result["hard_block_hits"]


def test_same_time_order_truth_input_fails_closed() -> None:
    action, taxonomy, relation, evidence = payloads()
    action["action_bundle_candidates"][0]["same_time_order_truth_admitted"] = True
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    assert result["status"] == "FAIL_CLOSED"
    assert "unsafe_same_time_order_truth_admitted" in result["hard_block_hits"]


def test_claim_boundaries_remain_closed() -> None:
    action, taxonomy, relation, evidence = payloads()
    result = build_action_occurrence_admission_with_conditional_review(action, taxonomy, relation, evidence)
    candidate = result["action_occurrence_candidates"][0]
    assert result["conditional_review_passthrough_changes_upstream_taxonomy_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["probability_output_allowed"] is False
    assert result["same_time_total_order_allowed"] is False
    assert result["source_row_order_is_temporal_truth"] is False
    assert result["provider_semantics_binding_required"] is True
    assert candidate["action_occurrence_candidate_is_event_truth"] is False
    assert candidate["validated_event_identity"] is False
