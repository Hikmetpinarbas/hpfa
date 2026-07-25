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
    label: str = "Passes accurate",
    period: str | None = "1",
    start: str | None = "10",
    end: str | None = "11",
    x: str | None = "0",
    y: str | None = "0",
    atom_status: str = "PASS",
) -> dict[str, object]:
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": "msb_1",
        "row_nucleus_id": "rn_" + atom_id,
        "source_role": source_role,
        "provider_row_id_candidate": atom_id,
        "source_relative_paths": ["surface.csv", "surface.xml"],
        "source_sha256_lineage": [_sha("1"), _sha("2")],
        "runtime_rehashed_sha256": {"csv": _sha("1"), "xml": _sha("2")},
        "atom_class": atom_class,
        "raw_label": label,
        "normalized_label": label.casefold(),
        "semantic_role_candidate": semantic_role,
        "semantic_role_candidates": [semantic_role],
        "action_family_candidates": [family] if family else [],
        "outcome_candidates": [],
        "downstream_eligibility_candidates": [],
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT" if x is not None and y is not None else "COORDINATE_MISSING",
        "atom_status": atom_status,
        "review_hits": [],
        "event_instance_allowed": False,
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
) -> dict[str, object]:
    if state is None:
        state = "TEAM_IDENTITY_CANDIDATE_BOUND" if source_role == "TEAM_SURFACE_CANDIDATE" else "ACTOR_IDENTITY_CANDIDATE_BOUND"
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": "msb_1",
        "source_role": source_role,
        "atom_class": "ACTION_ANCHOR_ATOM",
        "team_identity_candidate_id": team_id,
        "actor_identity_candidate_id": None if source_role == "TEAM_SURFACE_CANDIDATE" else actor_id,
        "decision_state": state,
        "event_instance_allowed": False,
        "validated_event_identity": False,
    }


def _payloads(
    atoms: list[dict[str, object]] | None = None,
    bindings: list[dict[str, object]] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    atom_values = atoms or [_atom()]
    binding_values = bindings or [_binding()]
    evidence = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": "msb_1",
        "evidence_atoms": atom_values,
        "evidence_atom_count": len(atom_values),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    identity = {
        "module_id": "match_local_identity_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": "msb_1",
        "identity_bindings": binding_values,
        "identity_binding_record_count": len(binding_values),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return evidence, identity


def test_one_identity_binding_per_atom_routes_and_bundles() -> None:
    evidence, identity = _payloads()
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "PASS"
    assert result["semantic_route_record_count"] == 1
    assert result["action_bundle_candidate_count"] == 1
    assert result["semantic_route_records"][0]["semantic_route"] == "PRIMARY_ACTION_ANCHOR_ROUTE"


def test_duplicate_atom_id_fails_closed() -> None:
    atoms = [_atom(), _atom()]
    bindings = [_binding(), _binding("ea_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("duplicate_evidence_atom_id") for item in result["hard_block_hits"])


def test_duplicate_identity_binding_id_fails_closed() -> None:
    atoms = [_atom(), _atom("ea_2")]
    bindings = [_binding(), _binding()]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("duplicate_identity_binding_atom_id") for item in result["hard_block_hits"])


def test_mixed_match_binding_fails_closed() -> None:
    evidence, identity = _payloads()
    identity["match_surface_binding_id"] = "msb_2"
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert "match_surface_binding_mismatch" in result["hard_block_hits"]


def test_action_anchor_requires_exact_one_family() -> None:
    evidence, identity = _payloads([_atom(family=None)], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 0


def test_action_anchor_requires_bound_identity() -> None:
    evidence, identity = _payloads([_atom()], [_binding(state="ACTOR_CANDIDATE_MISSING", actor_id=None)])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["semantic_route_records"][0]["semantic_route"] == "REVIEW_REQUIRED_ROUTE"
    assert result["action_bundle_candidate_count"] == 0


def test_same_role_exact_key_groups_multiple_labels() -> None:
    atoms = [_atom("ea_1", label="Passes"), _atom("ea_2", label="Passes accurate")]
    bindings = [_binding("ea_1"), _binding("ea_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 1
    assert result["action_bundle_candidates"][0]["supporting_evidence_atom_ids"] == ["ea_1", "ea_2"]


def test_same_timestamp_different_actor_does_not_group() -> None:
    atoms = [_atom("ea_1"), _atom("ea_2")]
    bindings = [_binding("ea_1", actor_id="actorc_1"), _binding("ea_2", actor_id="actorc_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2


def test_different_source_roles_never_group() -> None:
    atoms = [_atom("ea_1"), _atom("ea_2", source_role="TEAM_SURFACE_CANDIDATE")]
    bindings = [_binding("ea_1"), _binding("ea_2", source_role="TEAM_SURFACE_CANDIDATE")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2
    assert result["cross_role_relation_candidate_count"] == 1
    assert all(item["cross_role_fusion_allowed"] is False for item in result["action_bundle_candidates"])


def test_same_surface_family_conflict_remains_review_required() -> None:
    atoms = [_atom("ea_1", family="PASS"), _atom("ea_2", family="SHOT")]
    bindings = [_binding("ea_1"), _binding("ea_2")]
    evidence, identity = _payloads(atoms, bindings)
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_candidate_count"] == 2
    assert result["action_bundle_review_required_count"] == 2
    assert all("same_surface_multiple_action_families" in item["review_hits"] for item in result["action_bundle_candidates"])


def test_zero_coordinate_is_valid() -> None:
    evidence, identity = _payloads([_atom(x="0", y="0")], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_pass_count"] == 1
    assert result["action_bundle_candidates"][0]["pos_x_candidate"] == "0"


def test_missing_coordinate_is_explicit_review() -> None:
    evidence, identity = _payloads([_atom(x=None, y=None)], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["action_bundle_review_required_count"] == 1
    assert "coordinate_surface_missing_preserved" in result["action_bundle_candidates"][0]["review_hits"]


def test_non_action_atom_routes_without_bundle() -> None:
    atom = _atom(atom_class="CONTEXT_INTERVAL_ATOM", semantic_role="CONTEXT_INTERVAL", family=None)
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["semantic_route_records"][0]["semantic_route"] == "CONTEXT_INTERVAL_ROUTE"
    assert result["action_bundle_candidate_count"] == 0


def test_administrative_atom_identity_not_applicable_routes_safely() -> None:
    atom = _atom(atom_class="ADMINISTRATIVE_ATOM", semantic_role="ADMINISTRATIVE_MARKER", family=None)
    binding = _binding(state="IDENTITY_NOT_APPLICABLE", team_id=None, actor_id=None)
    evidence, identity = _payloads([atom], [binding])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["semantic_route_records"][0]["semantic_route"] == "ADMINISTRATIVE_ROUTE"
    assert result["action_bundle_candidate_count"] == 0


def test_review_atom_stays_review_route() -> None:
    atom = _atom(atom_class="REVIEW_REQUIRED_ATOM", semantic_role="UNKNOWN", family=None, atom_status="REVIEW_REQUIRED")
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["semantic_route_review_required_count"] == 1
    assert result["action_bundle_candidate_count"] == 0


def test_source_sha_lineage_missing_fails_closed() -> None:
    atom = _atom()
    atom["source_sha256_lineage"] = []
    evidence, identity = _payloads([atom], [_binding()])
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("source_sha_lineage_invalid") for item in result["hard_block_hits"])


def test_claim_and_release_layers_remain_closed() -> None:
    evidence, identity = _payloads()
    result = build_semantic_role_action_bundle_candidates(evidence, identity)
    for key in (
        "action_bundle_is_canonical_event",
        "validated_event_identity",
        "base_event_admission_allowed",
        "cross_role_fusion_allowed",
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


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "semantic_role_action_bundle_candidates.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Australia", "Turkey", "World Cup", "Galatasaray", "6935", "77798"):
        assert token not in text
