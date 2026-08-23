from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hpfa.modules.core.action_bundle_multi_family_review_taxonomy_lite.src.action_bundle_multi_family_review_taxonomy import (
    build_action_bundle_multi_family_review_taxonomy,
    validate_out,
)

BINDING = "msb_fixture"


def bundle(
    bundle_id: str,
    family: str,
    *,
    source_role: str = "PLAYER_SURFACE_CANDIDATE",
    team_id: str = "teamc_alpha",
    actor_id: str | None = "actorc_alpha",
    period: str = "1",
    start: object = "10.0",
    end: object = "10.4",
    x: object = "0",
    y: object = "0",
    coordinate_status: str = "COORDINATE_PRESENT",
    status: str = "REVIEW_REQUIRED",
    reasons: list[str] | None = None,
) -> dict[str, object]:
    return {
        "action_bundle_candidate_id": bundle_id,
        "match_surface_binding_id": BINDING,
        "source_role": source_role,
        "team_identity_candidate_id": team_id,
        "actor_identity_candidate_id": None if source_role == "TEAM_SURFACE_CANDIDATE" else actor_id,
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
        "review_hits": reasons if reasons is not None else ["same_surface_multiple_action_families"],
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "same_time_order_truth_admitted": False,
        "canonical_event_count": "UNKNOWN",
    }


def payload(*bundles: dict[str, object], module_status: str = "REVIEW_REQUIRED") -> dict[str, object]:
    pass_count = sum(item["bundle_status"] == "PASS" for item in bundles)
    review_count = sum(item["bundle_status"] == "REVIEW_REQUIRED" for item in bundles)
    return {
        "module_id": "semantic_role_action_bundle_candidates_lite_v1",
        "module_status": module_status,
        "status": module_status,
        "match_surface_binding_id": BINDING,
        "action_bundle_candidates": list(bundles),
        "action_bundle_candidate_count": len(bundles),
        "action_bundle_pass_count": pass_count,
        "action_bundle_review_required_count": review_count,
        "hard_block_hits": [],
        "action_bundle_is_canonical_event": False,
        "cross_role_fusion_allowed": False,
        "sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def record_for(*families: str, **kwargs: object) -> dict[str, object]:
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(*[bundle(f"b{i}", family, **kwargs) for i, family in enumerate(families, 1)])
    )
    assert result["hard_block_hits"] == []
    assert result["multi_family_review_core_count"] == 1
    return result["multi_family_review_records"][0]


def test_exact_registered_sets_are_candidate_only() -> None:
    duel = record_for("DUEL", "TACKLE")
    cross = record_for("PASS", "CROSS")
    turnover = record_for("TURNOVER", "CONTROL_ERROR")
    restart = record_for("PASS", "RESTART")
    assert duel["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert cross["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert turnover["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert restart["classification"] == "RESTART_ACTION_COUPLING_CANDIDATE"
    assert all(item["record_status"] == "PASS_CANDIDATE_CLASSIFICATION" for item in (duel, cross, turnover, restart))
    assert all(item["validated_event_identity"] is False for item in (duel, cross, turnover, restart))


def test_compound_and_same_time_sets_stay_review_required() -> None:
    assert record_for("DRIBBLE", "DUEL")["classification"] == "COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED"
    assert record_for("PASS", "RECOVERY")["classification"] == "SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED"


def test_three_plus_and_unregistered_sets_stay_review_required() -> None:
    assert record_for("DUEL", "RECOVERY", "TACKLE")["classification"] == "MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED"
    assert record_for("FOUL", "TURNOVER")["classification"] == "UNREGISTERED_FAMILY_SET_REVIEW_REQUIRED"


def test_zero_coordinate_is_valid() -> None:
    record = record_for("DUEL", "TACKLE", x=0, y=0)
    assert record["pos_x_candidate"] == "0.000000"
    assert record["pos_y_candidate"] == "0.000000"
    assert record["coordinate_evidence_status"] == "COORDINATE_PRESENT"


def test_missing_coordinate_preserves_review() -> None:
    record = record_for("DUEL", "TACKLE", x=None, y=None, coordinate_status="COORDINATE_MISSING")
    assert record["record_status"] == "REVIEW_REQUIRED"
    assert "coordinate_surface_missing_preserved" in record["review_hits"]


def test_same_time_different_actor_never_shares_core() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(
        bundle("b1", "PASS", actor_id="actor_one"),
        bundle("b2", "RECOVERY", actor_id="actor_one"),
        bundle("b3", "DUEL", actor_id="actor_two"),
        bundle("b4", "TACKLE", actor_id="actor_two"),
    ))
    assert result["multi_family_review_core_count"] == 2


def test_different_source_roles_never_share_core() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(
        bundle("b1", "PASS", source_role="PLAYER_SURFACE_CANDIDATE"),
        bundle("b2", "RECOVERY", source_role="PLAYER_SURFACE_CANDIDATE"),
        bundle("b3", "PASS", source_role="TEAM_SURFACE_CANDIDATE"),
        bundle("b4", "RECOVERY", source_role="TEAM_SURFACE_CANDIDATE"),
    ))
    assert result["multi_family_review_core_count"] == 2


def test_review_bundle_coverage_reconciles() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(
        bundle("b1", "PASS"),
        bundle("b2", "RESTART"),
        bundle("b3", "SHOT", status="PASS", reasons=[]),
    ))
    covered = sum(len(item["supporting_action_bundle_candidate_ids"]) for item in result["multi_family_review_records"])
    assert covered == result["source_review_bundle_record_count"] == 2
    assert result["source_pass_bundle_record_count"] == 1


def test_review_reason_contract_mismatch_fails_closed() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(
        bundle("b1", "PASS"),
        bundle("b2", "RESTART", reasons=["other_review_reason"]),
    ))
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("review_reason_contract_mismatch") for hit in result["hard_block_hits"])


def test_duplicate_bundle_id_fails_closed() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(bundle("dup", "PASS"), bundle("dup", "RESTART")))
    assert result["status"] == "FAIL_CLOSED"


def test_source_row_order_cannot_be_temporal_truth() -> None:
    first = bundle("b1", "PASS")
    first["source_row_order_is_temporal_truth"] = True
    result = build_action_bundle_multi_family_review_taxonomy(payload(first, bundle("b2", "RECOVERY")))
    assert result["status"] == "FAIL_CLOSED"
    assert any("source_row_order_promoted_to_temporal_truth" in hit for hit in result["hard_block_hits"])


def test_same_time_order_truth_cannot_be_admitted() -> None:
    first = bundle("b1", "PASS")
    first["same_time_order_truth_admitted"] = True
    result = build_action_bundle_multi_family_review_taxonomy(payload(first, bundle("b2", "RECOVERY")))
    assert result["status"] == "FAIL_CLOSED"
    assert any("same_time_order_truth_admitted" in hit for hit in result["hard_block_hits"])


def test_cross_role_fusion_claim_fails_closed() -> None:
    first = bundle("b1", "PASS")
    first["cross_role_fusion_allowed"] = True
    result = build_action_bundle_multi_family_review_taxonomy(payload(first, bundle("b2", "RECOVERY")))
    assert result["status"] == "FAIL_CLOSED"


def test_upstream_review_status_is_preserved_not_failure() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(bundle("b1", "DUEL"), bundle("b2", "TACKLE")))
    assert result["status"] == "REVIEW_REQUIRED"
    assert "action_bundle_upstream_review_required" in result["review_hits"]


def test_claim_boundaries_remain_closed() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(payload(bundle("b1", "DUEL"), bundle("b2", "TACKLE")))
    for key in (
        "classification_is_event_truth",
        "family_parent_is_validated_action",
        "subtype_is_validated_action",
        "restart_coupling_is_event_fusion",
        "same_time_order_truth_admitted",
        "source_row_order_is_temporal_truth",
        "cross_role_fusion_allowed",
        "independent_source_vote_allowed",
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


def test_input_payload_not_mutated() -> None:
    source = payload(bundle("b1", "PASS"), bundle("b2", "RESTART"))
    before = copy.deepcopy(source)
    build_action_bundle_multi_family_review_taxonomy(source)
    assert source == before


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "action_bundle_multi_family_review_taxonomy.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray"):
        assert token not in text
