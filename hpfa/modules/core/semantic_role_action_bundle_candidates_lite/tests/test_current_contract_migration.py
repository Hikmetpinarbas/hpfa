from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.semantic_role_action_bundle_candidates_lite.src.semantic_role_action_bundle_candidates import (
    build_semantic_role_action_bundle_candidates,
    validate_out,
)


def _sha(char: str) -> str:
    return char * 64


def _atom(
    atom_id: str = "ea_1",
    *,
    source_role: str = "PLAYER_SURFACE_CANDIDATE",
    atom_class: str = "ACTION_ANCHOR_ATOM",
    semantic_role: str = "ACTION_ANCHOR",
    family: str | None = "PASS",
    label: str = "passes accurate",
    period: str | None = "1",
    start: str | None = "10",
    end: str | None = "11",
    x: str | None = "0",
    y: str | None = "0",
    atom_status: str = "PASS",
) -> dict:
    short = {
        "PLAYER_SURFACE_CANDIDATE": "PLAYER",
        "GOALKEEPER_SURFACE_CANDIDATE": "GOALKEEPER",
        "TEAM_SURFACE_CANDIDATE": "TEAM",
    }[source_role]
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": "msb_fixture",
        "source_role": source_role,
        "source_role_short": short,
        "source_lineage_records": [
            {
                "source_file": f"{short.lower()}.csv",
                "source_format": "csv",
                "source_role": short,
                "source_row_index": 1,
                "source_sha256": _sha("1"),
                "source_row_index_is_order_truth": False,
            },
            {
                "source_file": f"{short.lower()}.xml",
                "source_format": "xml",
                "source_role": short,
                "source_row_index": 2,
                "source_sha256": _sha("2"),
                "source_row_index_is_order_truth": False,
            },
        ],
        # Historical positional lineage fields are intentionally non-authoritative.
        "source_relative_paths": ["historical-shape-does-not-control"],
        "source_sha256_lineage": [],
        "runtime_rehashed_sha256": {},
        "atom_class": atom_class,
        "atom_status": atom_status,
        "raw_label": label,
        "normalized_label": label.casefold(),
        "semantic_role_candidate": semantic_role,
        "action_family_candidates": [family] if family else [],
        "provider_row_id_candidate": atom_id,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "independent_support_vote_count": 0,
        "independent_source_vote_allowed": False,
        "same_time_link_allowed": False,
        "negative_time_link_allowed": False,
        "cross_period_link_allowed": False,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "physical_action_identity_truth": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _binding(
    atom_id: str = "ea_1",
    *,
    source_role: str = "PLAYER_SURFACE_CANDIDATE",
    state: str | None = None,
    team_id: str | None = "teamc_1",
    actor_id: str | None = "actorc_1",
) -> dict:
    if state is None:
        state = "TEAM_IDENTITY_CANDIDATE_BOUND" if source_role == "TEAM_SURFACE_CANDIDATE" else "ACTOR_IDENTITY_CANDIDATE_BOUND"
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": "msb_fixture",
        "source_role": source_role,
        "team_identity_candidate_id": team_id,
        "actor_identity_candidate_id": None if source_role == "TEAM_SURFACE_CANDIDATE" else actor_id,
        "decision_state": state,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "validated_event_identity": False,
    }


def _payloads(atoms=None, bindings=None, *, evidence_status="PASS", identity_status="PASS"):
    atom_values = atoms or [_atom()]
    binding_values = bindings or [_binding()]
    evidence = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": evidence_status,
        "module_status": evidence_status,
        "match_surface_binding_id": "msb_fixture",
        "evidence_atoms": atom_values,
        "evidence_atom_count": len(atom_values),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": identity_status,
        "module_status": identity_status,
        "match_surface_binding_id": "msb_fixture",
        "identity_bindings": binding_values,
        "identity_binding_record_count": len(binding_values),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return evidence, identity


def test_current_structured_lineage_routes_and_bundles() -> None:
    evidence, identity = _payloads()
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "PASS"
    assert result["semantic_route_record_count"] == 1
    assert result["action_bundle_candidate_count"] == 1
    assert result["semantic_route_records"][0]["semantic_route"] == "PRIMARY_ACTION_ANCHOR_ROUTE"


def test_historical_positional_lineage_fields_do_not_control_current_validation() -> None:
    evidence, identity = _payloads()
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["hard_block_hits"] == []


def test_xlsx_lineage_fails_closed() -> None:
    atom = _atom()
    atom["source_lineage_records"][0]["source_format"] = "xlsx"
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any("source_lineage_format_rejected" in item for item in result["hard_block_hits"])


def test_source_row_order_cannot_be_promoted() -> None:
    atom = _atom()
    atom["source_lineage_records"][0]["source_row_index_is_order_truth"] = True
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any("source_row_index_promoted_to_order_truth" in item for item in result["hard_block_hits"])


def test_independent_support_vote_cannot_be_reintroduced() -> None:
    atom = _atom()
    atom["independent_support_vote_count"] = 1
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"


def test_administrative_review_preserves_role_without_action_admission() -> None:
    atom = _atom(
        atom_class="ADMINISTRATIVE_ATOM",
        semantic_role="PERIOD_OR_META",
        family=None,
        atom_status="REVIEW_REQUIRED",
        x="none",
        y="none",
    )
    binding = _binding(state="IDENTITY_NOT_APPLICABLE", team_id=None, actor_id=None)
    evidence, identity = _payloads([atom], [binding], evidence_status="REVIEW_REQUIRED", identity_status="REVIEW_REQUIRED")
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    route = result["semantic_route_records"][0]
    assert route["semantic_route"] == "ADMINISTRATIVE_ROUTE"
    assert route["route_status"] == "REVIEW_REQUIRED"
    assert "upstream_atom_review_preserved" in route["review_hits"]
    assert result["action_bundle_candidate_count"] == 0


def test_semantic_review_action_anchor_is_blocked_from_bundle() -> None:
    atom = _atom(atom_status="REVIEW_REQUIRED", family="SHOT")
    evidence, identity = _payloads([atom], [_binding()], evidence_status="REVIEW_REQUIRED", identity_status="REVIEW_REQUIRED")
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["semantic_route_records"][0]["semantic_route"] == "REVIEW_REQUIRED_ROUTE"
    assert result["semantic_route_blocked_action_anchor_count"] == 1
    assert result["action_bundle_candidate_count"] == 0


def test_team_surface_gets_team_reflection_bundle_without_actor() -> None:
    atom = _atom(source_role="TEAM_SURFACE_CANDIDATE")
    binding = _binding(source_role="TEAM_SURFACE_CANDIDATE")
    evidence, identity = _payloads([atom], [binding])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    bundle = result["action_bundle_candidates"][0]
    assert result["semantic_route_records"][0]["semantic_route"] == "TEAM_ACTION_REFLECTION_ROUTE"
    assert bundle["actor_identity_candidate_id"] is None


def test_same_timestamp_different_actor_does_not_group() -> None:
    atoms = [_atom("ea_1"), _atom("ea_2")]
    bindings = [_binding("ea_1", actor_id="actorc_1"), _binding("ea_2", actor_id="actorc_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2
    assert all(item["same_time_order_truth_admitted"] is False for item in result["action_bundle_candidates"])


def test_different_source_roles_never_group_and_relation_is_candidate_only() -> None:
    atoms = [_atom("ea_1"), _atom("ea_2", source_role="TEAM_SURFACE_CANDIDATE")]
    bindings = [_binding("ea_1"), _binding("ea_2", source_role="TEAM_SURFACE_CANDIDATE")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2
    assert result["cross_role_relation_candidate_count"] == 1
    assert result["cross_role_relation_candidates"][0]["cross_role_fusion_allowed"] is False


def test_same_surface_multiple_families_remain_review_required() -> None:
    atoms = [_atom("ea_1", family="PASS"), _atom("ea_2", family="CROSS")]
    bindings = [_binding("ea_1"), _binding("ea_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2
    assert result["action_bundle_review_required_count"] == 2
    assert all("same_surface_multiple_action_families" in item["review_hits"] for item in result["action_bundle_candidates"])


def test_missing_coordinate_is_explicit_review() -> None:
    atom = _atom(x="none", y="none")
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_review_required_count"] == 1
    assert "coordinate_surface_missing_preserved" in result["action_bundle_candidates"][0]["review_hits"]


def test_identity_source_role_mismatch_fails_closed() -> None:
    evidence, identity = _payloads([_atom()], [_binding(source_role="GOALKEEPER_SURFACE_CANDIDATE")])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any("identity_binding_source_role_mismatch" in item for item in result["hard_block_hits"])


def test_claim_and_release_boundaries_remain_closed() -> None:
    evidence, identity = _payloads()
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    for key in (
        "action_bundle_is_canonical_event",
        "validated_event_identity",
        "physical_action_identity_truth",
        "base_event_admission_allowed",
        "cross_role_fusion_allowed",
        "independent_source_vote_allowed",
        "metric_value_output_allowed",
        "comparison_allowed",
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


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "semantic_role_action_bundle_candidates.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray", "Australia", "Turkey"):
        assert token not in text
