from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import load_registry
from hpfa.modules.core.action_occurrence_admission_lite.src.observation_occurrence_cardinality import (
    bind_observation_occurrence_cardinality,
)


def _bundle(bid: str, family: str, labels: list[str]) -> dict:
    return {
        "action_bundle_candidate_id": bid,
        "match_surface_binding_id": "msb_test",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "10.4",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": [f"ea_{bid}_{i}" for i in range(len(labels))],
        "provider_row_id_candidates": [f"row_{bid}_{i}" for i in range(len(labels))],
        "raw_labels": labels,
        "normalized_labels": [label.casefold() for label in labels],
    }


def _evidence(bundles: list[dict], *, wrong: bool = False) -> dict:
    registry = load_registry()
    mapping = {}
    for rule in registry.get("intra_actor_occurrence_rules") or []:
        for label, meta in (rule.get("semantic_labels") or {}).items():
            mapping[label] = meta["semantic_rule_id"]
    atoms = []
    for bundle in bundles:
        for i, label in enumerate(bundle["raw_labels"]):
            atoms.append({
                "evidence_atom_id": bundle["supporting_evidence_atom_ids"][i],
                "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "semantic_rule_id": "wrong_rule" if wrong else mapping[label],
            })
    return {"evidence_atoms": atoms}


def _grammar_candidate(bundle: dict, labels: list[str], *, drop_last: bool = False) -> dict:
    registry = load_registry()
    rule = next(row for row in registry["intra_actor_occurrence_rules"] if row["action_family"] == bundle["action_family_candidate"])
    components = []
    for label in labels:
        meta = rule["semantic_labels"][label]
        components.append({
            "label": label,
            "semantic_rule_id": meta.get("semantic_rule_id"),
            "outcome": meta.get("outcome"),
            "direction": meta.get("direction"),
            "distance": meta.get("distance"),
            "zone_context": meta.get("zone_context"),
            "progression": meta.get("progression"),
            "key_action": meta.get("key_action"),
        })
    if drop_last:
        components = components[:-1]
    return {
        "action_occurrence_candidate_id": f"aoc_{bundle['action_bundle_candidate_id']}",
        "admission_class": "EXACT_SAME_ACTOR_SEMANTIC_COLLAPSE",
        "occurrence_topology": "SINGLE_ACTOR_ACTION",
        "compatibility_rule_id": rule["rule_id"],
        "primary_family_candidate": bundle["action_family_candidate"],
        "team_identity_candidate_id": bundle["team_identity_candidate_id"],
        "actor_identity_candidate_id": bundle["actor_identity_candidate_id"],
        "supporting_action_bundle_candidate_ids": [bundle["action_bundle_candidate_id"]],
        "supporting_evidence_atom_ids": bundle["supporting_evidence_atom_ids"],
        "provider_row_id_candidates": bundle["provider_row_id_candidates"],
        "semantic_components": components,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
    }


def test_multiple_observations_one_occurrence_is_explicit_and_lossless() -> None:
    labels = ["Passes accurate", "Passes forward accurate", "Progressive passes accurate"]
    bundle = _bundle("pass_a", "PASS", labels)
    candidate = _grammar_candidate(bundle, labels)
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": [bundle]},
        _evidence([bundle]),
        load_registry(),
        [candidate],
    )
    assert result["hard_block_hits"] == []
    assert result["state_counts"] == {"MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE": 1}
    record = result["records"][0]
    assert record["occurrence_candidate_id"] == "aoc_pass_a"
    assert record["source_observation_count"] == 3
    assert record["information_loss_state"] == "LOSSLESS_SEMANTIC_COMPONENT_PRESERVATION"
    assert record["qualifier_attributes"] == ["direction:FORWARD", "progression:PROGRESSIVE_CANDIDATE"]
    assert record["outcome_attributes"] == ["SUCCESS"]
    assert candidate["observation_occurrence_cardinality"]["cardinality_pattern"] == "MULTIPLE_OBSERVATIONS_ONE_OCCURRENCE"
    assert record["canonical_event_count"] == "UNKNOWN"
    assert record["true_action_count"] == "UNKNOWN"


def test_contradictory_semantics_become_cardinality_ambiguous_not_forced_collapse() -> None:
    labels = ["Passes accurate", "Inaccurate passes"]
    bundle = _bundle("pass_conflict", "PASS", labels)
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": [bundle]},
        _evidence([bundle]),
        load_registry(),
        [],
    )
    assert result["state_counts"] == {"CARDINALITY_AMBIGUOUS": 1}
    record = result["records"][0]
    assert record["occurrence_candidate_id"] is None
    assert record["contradiction_state"] == "CONTRADICTORY_OUTCOME_SEMANTICS"
    assert "MULTIPLE_ACTIONS_POSSIBLE" in record["alternative_cardinality_state"]


def test_missing_provider_semantic_binding_is_not_reconstructable() -> None:
    labels = ["Passes accurate", "Passes forward accurate"]
    bundle = _bundle("pass_bad_binding", "PASS", labels)
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": [bundle]},
        _evidence([bundle], wrong=True),
        load_registry(),
        [],
    )
    assert result["state_counts"] == {"NOT_RECONSTRUCTABLE": 1}
    assert result["records"][0]["information_loss_state"] == "NOT_APPLICABLE_NO_COLLAPSE"


def test_dropped_semantic_component_is_fail_closed() -> None:
    labels = ["Passes accurate", "Passes forward accurate", "Progressive passes accurate"]
    bundle = _bundle("pass_loss", "PASS", labels)
    candidate = _grammar_candidate(bundle, labels, drop_last=True)
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": [bundle]},
        _evidence([bundle]),
        load_registry(),
        [candidate],
    )
    assert result["hard_block_hits"] == ["cardinality_information_loss:pass_loss"]
    assert result["records"][0]["information_loss_state"] == "INFORMATION_LOSS_DETECTED"


def test_single_reviewed_anchor_is_one_observation_one_occurrence_candidate() -> None:
    candidate = {
        "action_occurrence_candidate_id": "aoc_anchor_1",
        "admission_class": "EXACT_SINGLE_ACTION_ANCHOR_SEMANTIC_ADMISSION",
        "occurrence_topology": "SINGLE_ACTOR_ACTION",
        "compatibility_rule_id": "single_action_anchor_exact_v1",
        "primary_family_candidate": "PASS",
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "supporting_action_bundle_candidate_ids": ["bundle_single"],
        "supporting_evidence_atom_ids": ["ea_single"],
        "provider_row_id_candidates": ["row_single"],
        "supporting_semantic_rule_ids": ["plvs_single"],
        "temporal_relation": {"period_candidate": "1", "start_candidate": "1.0", "end_candidate": "1.2"},
    }
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": []},
        {"evidence_atoms": []},
        load_registry(),
        [candidate],
    )
    assert result["state_counts"] == {"ONE_OBSERVATION_ONE_OCCURRENCE": 1}
    assert candidate["observation_occurrence_cardinality"]["cardinality_resolution_is_physical_action_truth"] is False


def test_global_cardinality_claim_locks_remain_closed() -> None:
    result = bind_observation_occurrence_cardinality(
        {"action_bundle_candidates": []},
        {"evidence_atoms": []},
        load_registry(),
        [],
    )
    assert result["row_count_is_action_count"] is False
    assert result["label_count_is_action_count"] is False
    assert result["same_actor_same_timestamp_is_single_action_authority"] is False
    assert result["shared_base_label_is_sufficient_collapse_authority"] is False
    assert result["multiple_rows_automatically_single_occurrence"] is False
    assert result["xlsx_can_create_action_identity"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
