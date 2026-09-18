from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.action_grammar_public_adapter import (
    bind_intra_actor_action_grammar,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    load_registry,
)

BINDING = "msb_" + "p" * 24


def _pass_bundle() -> dict:
    labels = ["Passes accurate", "Passes forward accurate", "Progressive passes accurate"]
    return {
        "action_bundle_candidate_id": "pass_bundle",
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "period_candidate": "1",
        "start_candidate": "21.10",
        "end_candidate": "21.55",
        "pos_x_candidate": "48.00",
        "pos_y_candidate": "39.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": "PASS",
        "supporting_evidence_atom_ids": ["ea_pass", "ea_forward", "ea_progressive"],
        "provider_row_id_candidates": ["r_pass", "r_forward", "r_progressive"],
        "raw_labels": labels,
        "normalized_labels": [label.casefold() for label in labels],
        "bundle_status": "PASS",
        "review_hits": [],
        "same_role_exact_grouping": True,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _evidence() -> dict:
    return {
        "evidence_atoms": [
            {"evidence_atom_id": "ea_pass", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_passes_accurate"},
            {"evidence_atom_id": "ea_forward", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_passes_forward_accurate"},
            {"evidence_atom_id": "ea_progressive", "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE", "semantic_rule_id": "plvs_v2_progressive_passes_accurate"},
        ]
    }


def _base_occurrence() -> dict:
    return {
        "status": "PASS",
        "module_status": "PASS",
        "action_occurrence_candidates": [],
        "action_occurrence_candidate_count": 0,
        "candidate_rejected_provider_semantics_binding_count": 0,
        "admission_class_counts": {},
        "interaction_type_counts": {},
        "review_hits": [],
        "provider_semantics_binding_status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_public_adapter_adds_grammar_candidate_without_inflating_label_count() -> None:
    row = _pass_bundle()
    result = bind_intra_actor_action_grammar(
        _base_occurrence(),
        {"action_bundle_candidates": [row]},
        _evidence(),
        load_registry(),
    )

    assert result["interaction_occurrence_candidate_count"] == 0
    assert result["intra_actor_action_grammar_candidate_count"] == 1
    assert result["action_occurrence_candidate_count"] == 1
    assert result["action_occurrence_candidates"][0]["attributes"]["distinct_semantic_label_count"] == 3
    assert result["provider_semantics_binding_status"] == "PASS"
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_public_adapter_repairs_false_pass_when_existing_candidate_semantics_were_rejected() -> None:
    occurrence = _base_occurrence()
    occurrence["candidate_rejected_provider_semantics_binding_count"] = 1
    occurrence["provider_semantics_binding_status"] = "PASS"
    result = bind_intra_actor_action_grammar(
        occurrence,
        {"action_bundle_candidates": []},
        {"evidence_atoms": []},
        load_registry(),
    )

    assert result["action_occurrence_candidate_count"] == 0
    assert result["candidate_rejected_provider_semantics_binding_count"] == 1
    assert result["provider_semantics_binding_status"] == "REVIEW_REQUIRED"
    assert "candidate_rejected_provider_semantics_binding" in result["review_hits"]
