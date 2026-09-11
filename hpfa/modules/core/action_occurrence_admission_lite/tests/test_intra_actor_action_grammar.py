from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.action_occurrence_admission_lite.src.intra_actor_action_grammar import (
    build_intra_actor_action_grammar_candidates,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.action_occurrence_admission import (
    load_registry,
)

BINDING = "msb_" + "g" * 24


def bundle(
    bid: str,
    family: str,
    labels: list[str],
    *,
    actor: str = "actor_a",
    team: str = "team_a",
) -> dict:
    return {
        "action_bundle_candidate_id": bid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": "10.00",
        "end_candidate": "10.40",
        "pos_x_candidate": "55.00",
        "pos_y_candidate": "42.00",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidate": family,
        "supporting_evidence_atom_ids": [f"ea_{bid}_{index}" for index in range(len(labels))],
        "provider_row_id_candidates": [f"row_{bid}_{index}" for index in range(len(labels))],
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


def evidence(bundles: list[dict], *, override_rule_id: str | None = None) -> dict:
    registry = load_registry()
    label_to_rule = {}
    for rule in registry.get("intra_actor_occurrence_rules") or []:
        for label, meta in (rule.get("semantic_labels") or {}).items():
            label_to_rule[label] = meta["semantic_rule_id"]

    atoms = []
    for row in bundles:
        for index, label in enumerate(row["raw_labels"]):
            atoms.append(
                {
                    "evidence_atom_id": row["supporting_evidence_atom_ids"][index],
                    "semantic_mapping_status": "EXACT_REVIEWED_CANDIDATE",
                    "semantic_rule_id": override_rule_id or label_to_rule[label],
                }
            )
    return {"evidence_atoms": atoms}


def test_pass_qualifier_stack_collapses_to_one_occurrence_candidate() -> None:
    row = bundle(
        "pass_a",
        "PASS",
        ["Passes accurate", "Passes forward accurate", "Progressive passes accurate"],
    )
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": [row]}, evidence([row]), load_registry()
    )

    assert result["action_occurrence_candidate_count"] == 1
    candidate = result["action_occurrence_candidates"][0]
    assert candidate["admission_class"] == "EXACT_SAME_ACTOR_SEMANTIC_COLLAPSE"
    assert candidate["occurrence_topology"] == "SINGLE_ACTOR_ACTION"
    assert candidate["primary_family_candidate"] == "PASS"
    assert candidate["attributes"]["outcome_candidate"] == "SUCCESS"
    assert candidate["attributes"]["direction_candidates"] == ["FORWARD"]
    assert candidate["attributes"]["progression_candidates"] == ["PROGRESSIVE_CANDIDATE"]
    assert candidate["attributes"]["distinct_semantic_label_count"] == 3
    assert len(candidate["supporting_action_bundle_candidate_ids"]) == 1
    assert candidate["canonical_event_count"] == "UNKNOWN"
    assert candidate["true_action_count"] == "UNKNOWN"


def test_dribble_final_third_label_is_context_not_second_action() -> None:
    row = bundle(
        "dribble_a",
        "DRIBBLE",
        ["Dribbles successful", "Dribbling in the final third successful"],
    )
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": [row]}, evidence([row]), load_registry()
    )

    assert result["action_occurrence_candidate_count"] == 1
    candidate = result["action_occurrence_candidates"][0]
    assert candidate["primary_family_candidate"] == "DRIBBLE"
    assert candidate["attributes"]["outcome_candidate"] == "SUCCESS"
    assert candidate["attributes"]["zone_context_candidates"] == ["FINAL_THIRD"]
    assert candidate["attributes"]["distinct_semantic_label_count"] == 2


def test_contradictory_success_failure_annotations_do_not_collapse() -> None:
    row = bundle("pass_conflict", "PASS", ["Passes accurate", "Inaccurate passes"])
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": [row]}, evidence([row]), load_registry()
    )

    assert result["action_occurrence_candidate_count"] == 0
    assert result["contradictory_semantics_count"] == 1
    assert "intra_actor_candidate_contradictory_outcome_semantics" in result["review_hits"]


def test_wrong_provider_semantic_binding_is_withheld() -> None:
    row = bundle("pass_bad_semantics", "PASS", ["Passes accurate", "Passes forward accurate"])
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": [row]},
        evidence([row], override_rule_id="wrong_provider_rule"),
        load_registry(),
    )

    assert result["action_occurrence_candidate_count"] == 0
    assert result["rejected_provider_semantics_binding_count"] == 1


def test_same_timestamp_unrelated_action_families_remain_separate() -> None:
    pass_row = bundle(
        "pass_same_time",
        "PASS",
        ["Passes accurate", "Passes forward accurate"],
    )
    dribble_row = bundle(
        "dribble_same_time",
        "DRIBBLE",
        ["Dribbles successful", "Dribbling in the final third successful"],
    )
    rows = [pass_row, dribble_row]
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": rows}, evidence(rows), load_registry()
    )

    assert result["action_occurrence_candidate_count"] == 2
    families = sorted(row["primary_family_candidate"] for row in result["action_occurrence_candidates"])
    assert families == ["DRIBBLE", "PASS"]
    assert result["cross_bundle_merge_allowed"] is False
    assert result["same_timestamp_alone_is_merge_authority"] is False


def test_single_label_does_not_promote_action_occurrence() -> None:
    row = bundle("pass_single", "PASS", ["Passes accurate"])
    result = build_intra_actor_action_grammar_candidates(
        {"action_bundle_candidates": [row]}, evidence([row]), load_registry()
    )
    assert result["action_occurrence_candidate_count"] == 0


def test_claim_locks_and_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/action_occurrence_admission_lite/src/intra_actor_action_grammar.py"
    ).read_text(encoding="utf-8")
    for token in (
        "Genclerbirligi",
        "Fenerbahce",
        "Sporting",
        "Galatasaray",
        "09.09.2026",
    ):
        assert token not in source
