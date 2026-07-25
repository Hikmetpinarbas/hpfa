from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hpfa.modules.core.action_bundle_multi_family_review_taxonomy_lite.src.action_bundle_multi_family_review_taxonomy import (
    build_action_bundle_multi_family_review_taxonomy,
    validate_out,
)

BINDING = "msb_" + "a" * 24


def bundle(
    bundle_id: str,
    family: str,
    *,
    source_role: str = "PLAYER_SURFACE_CANDIDATE",
    team_id: str = "teamc_alpha",
    actor_id: str | None = "actorc_alpha_7",
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
            reasons
            if reasons is not None
            else ["same_surface_multiple_action_families"]
        ),
        "same_role_exact_grouping": True,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "ACTION_BUNDLE_CANDIDATE_ONLY",
    }


def payload(*bundles: dict[str, object], module_status: str = "PASS") -> dict[str, object]:
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
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def record_for(*families: str, **kwargs: object) -> dict[str, object]:
    items = [
        bundle(f"b{index}", family, **kwargs)
        for index, family in enumerate(families, 1)
    ]
    result = build_action_bundle_multi_family_review_taxonomy(payload(*items))
    assert result["hard_block_hits"] == []
    assert result["multi_family_review_core_count"] == 1
    return result["multi_family_review_records"][0]


def test_duel_tackle_is_hierarchical_candidate_without_event_promotion() -> None:
    record = record_for("DUEL", "TACKLE")
    assert record["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert record["parent_family_candidate"] == "DUEL"
    assert record["subtype_family_candidates"] == ["TACKLE"]
    assert record["record_status"] == "PASS_CANDIDATE_CLASSIFICATION"
    assert record["validated_event_identity"] is False
    assert record["event_instance_allowed"] is False


def test_pass_cross_is_hierarchical_candidate() -> None:
    record = record_for("PASS", "CROSS")
    assert record["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert record["parent_family_candidate"] == "PASS"
    assert record["subtype_family_candidates"] == ["CROSS"]


def test_turnover_control_error_is_hierarchical_candidate() -> None:
    record = record_for("TURNOVER", "CONTROL_ERROR")
    assert record["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert record["parent_family_candidate"] == "TURNOVER"


def test_pass_restart_is_coupling_candidate_not_fusion() -> None:
    record = record_for("PASS", "RESTART")
    assert record["classification"] == "RESTART_ACTION_COUPLING_CANDIDATE"
    assert record["restart_coupling_is_event_fusion"] is False
    assert record["cross_role_fusion_allowed"] is False


def test_dribble_duel_stays_compound_review_required() -> None:
    record = record_for("DRIBBLE", "DUEL")
    assert record["classification"] == (
        "COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED"
    )
    assert record["record_status"] == "REVIEW_REQUIRED"


def test_pass_recovery_stays_same_time_risk_review_required() -> None:
    record = record_for("PASS", "RECOVERY")
    assert record["classification"] == "SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED"
    assert record["record_status"] == "REVIEW_REQUIRED"


def test_three_plus_family_core_stays_complex_review_required() -> None:
    record = record_for("PASS", "RECOVERY", "RESTART")
    assert record["classification"] == "MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED"
    assert record["family_count"] == 3


def test_unregistered_exact_set_stays_review_required() -> None:
    record = record_for("FOUL", "SHOT")
    assert record["classification"] == "UNREGISTERED_FAMILY_SET_REVIEW_REQUIRED"
    assert record["record_status"] == "REVIEW_REQUIRED"


def test_zero_coordinate_is_present_and_not_missing() -> None:
    record = record_for("DUEL", "TACKLE", x=0, y=0)
    assert record["pos_x_candidate"] == "0.000000"
    assert record["pos_y_candidate"] == "0.000000"
    assert record["coordinate_evidence_status"] == "COORDINATE_PRESENT"
    assert "coordinate_surface_missing_preserved" not in record["review_hits"]


def test_missing_coordinate_preserves_review_even_for_registered_set() -> None:
    record = record_for(
        "DUEL",
        "TACKLE",
        x=None,
        y=None,
        coordinate_status="COORDINATE_MISSING",
    )
    assert record["classification"] == "HIERARCHICAL_SUBTYPE_CANDIDATE"
    assert record["record_status"] == "REVIEW_REQUIRED"
    assert "coordinate_surface_missing_preserved" in record["review_hits"]


def test_same_time_different_actor_never_shares_core() -> None:
    bundles = [
        bundle("b1", "PASS", actor_id="actorc_one"),
        bundle("b2", "RESTART", actor_id="actorc_one"),
        bundle("b3", "DUEL", actor_id="actorc_two"),
        bundle("b4", "TACKLE", actor_id="actorc_two"),
    ]
    result = build_action_bundle_multi_family_review_taxonomy(payload(*bundles))
    assert result["multi_family_review_core_count"] == 2
    assert {
        item["actor_identity_candidate_id"]
        for item in result["multi_family_review_records"]
    } == {"actorc_one", "actorc_two"}


def test_different_source_roles_never_share_core() -> None:
    bundles = [
        bundle("b1", "PASS", source_role="PLAYER_SURFACE_CANDIDATE"),
        bundle("b2", "RESTART", source_role="PLAYER_SURFACE_CANDIDATE"),
        bundle("b3", "PASS", source_role="TEAM_SURFACE_CANDIDATE"),
        bundle("b4", "RESTART", source_role="TEAM_SURFACE_CANDIDATE"),
    ]
    result = build_action_bundle_multi_family_review_taxonomy(payload(*bundles))
    assert result["multi_family_review_core_count"] == 2
    assert result["source_role_counts"] == {
        "PLAYER_SURFACE_CANDIDATE": 1,
        "TEAM_SURFACE_CANDIDATE": 1,
    }


def test_review_bundle_coverage_reconciles() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(
            bundle("b1", "PASS"),
            bundle("b2", "RESTART"),
            bundle("b3", "DUEL", actor_id="actorc_two"),
            bundle("b4", "TACKLE", actor_id="actorc_two"),
            bundle("b5", "SHOT", status="PASS", reasons=[]),
        )
    )
    covered = sum(
        len(item["supporting_action_bundle_candidate_ids"])
        for item in result["multi_family_review_records"]
    )
    assert covered == result["source_review_bundle_record_count"] == 4
    assert result["source_pass_bundle_record_count"] == 1


def test_duplicate_bundle_id_fails_closed() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(bundle("dup", "PASS"), bundle("dup", "RESTART"))
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(
        hit.startswith("duplicate_action_bundle_candidate_id")
        for hit in result["hard_block_hits"]
    )


def test_mixed_match_binding_fails_closed() -> None:
    second = bundle("b2", "RESTART")
    second["match_surface_binding_id"] = "msb_" + "b" * 24
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(bundle("b1", "PASS"), second)
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(
        hit.startswith("match_surface_binding_mismatch")
        for hit in result["hard_block_hits"]
    )


def test_review_reason_contract_mismatch_fails_closed() -> None:
    bad = bundle(
        "b2",
        "RESTART",
        reasons=["coordinate_surface_missing_preserved"],
    )
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(bundle("b1", "PASS"), bad)
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(
        hit.startswith("review_reason_contract_mismatch")
        for hit in result["hard_block_hits"]
    )


def test_claim_boundaries_remain_closed() -> None:
    result = build_action_bundle_multi_family_review_taxonomy(
        payload(bundle("b1", "PASS"), bundle("b2", "RESTART"))
    )
    assert result["classification_is_event_truth"] is False
    assert result["family_parent_is_validated_action"] is False
    assert result["subtype_is_validated_action"] is False
    assert result["cross_role_fusion_allowed"] is False
    assert result["event_instance_count"] == 0
    assert result["claim_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_input_payload_is_not_mutated() -> None:
    source = payload(bundle("b1", "PASS"), bundle("b2", "RESTART"))
    original = copy.deepcopy(source)
    build_action_bundle_multi_family_review_taxonomy(source)
    assert source == original


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/action_bundle_multi_family_review_taxonomy_lite/src/"
        "action_bundle_multi_family_review_taxonomy.py"
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
