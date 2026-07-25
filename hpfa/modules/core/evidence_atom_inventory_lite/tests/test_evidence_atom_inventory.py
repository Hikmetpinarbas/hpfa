from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.evidence_atom_inventory_lite.src.evidence_atom_inventory import (
    build_evidence_atom_inventory,
    validate_out,
)


def _sha(char: str) -> str:
    return char * 64


def _binding_audit() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, csv_char, xml_char in (
        ("GOALKEEPER_SURFACE_CANDIDATE", "1", "2"),
        ("PLAYER_SURFACE_CANDIDATE", "3", "4"),
        ("TEAM_SURFACE_CANDIDATE", "5", "6"),
    ):
        rows.extend(
            [
                {
                    "source_role": role,
                    "source_format": "csv",
                    "runtime_rehashed_sha256": _sha(csv_char),
                    "audit_sha_match": True,
                },
                {
                    "source_role": role,
                    "source_format": "xml",
                    "runtime_rehashed_sha256": _sha(xml_char),
                    "audit_sha_match": True,
                },
            ]
        )
    return rows


def _nucleus(
    nucleus_id: str = "rn_1",
    *,
    role: str = "ACTION_ANCHOR",
    family: str | None = "PASS",
    eligibility: str = "ACTION_CANDIDATE_ELIGIBLE",
    pos_x: str | None = "0",
    pos_y: str | None = "0",
    aggregate_overlay: bool = False,
) -> dict[str, object]:
    roles = [role]
    statuses = ["EXACT_REVIEWED_CANDIDATE"]
    eligibilities = [eligibility]
    rules = ["rule_1"]
    if aggregate_overlay:
        roles.append("AGGREGATE_METRIC_LABEL")
        statuses.append("XLSX_AGGREGATE_LABEL_CANDIDATE")
        eligibilities.append("AGGREGATE_ONLY")
        rules.append("xlsx_metric_label_surface")
    return {
        "nucleus_id": nucleus_id,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "provider_row_id_candidate": "7",
        "source_relative_paths": ["Players.csv", "Players.xml"],
        "source_sha256_lineage": [_sha("3"), _sha("4")],
        "runtime_rehashed_sha256": {"csv": _sha("3"), "xml": _sha("4")},
        "action_raw": "Passes accurate",
        "code_raw": "Player - Passes accurate",
        "team_raw_candidate": "TEAM_A",
        "period_candidate": "1",
        "start_candidate": "10",
        "end_candidate": "11",
        "pos_x_candidate": pos_x,
        "pos_y_candidate": pos_y,
        "semantic_role_candidates": roles,
        "action_family_candidates": [family] if family else [],
        "outcome_candidates": ["SUCCESS"] if family else [],
        "downstream_eligibility_candidates": eligibilities,
        "mapping_statuses": statuses,
        "mapping_rule_ids": rules,
        "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
        "aggregate_definition_dependency": "DERIVATION_DEPENDENCY_UNRESOLVED",
        "nucleus_status": "PASS",
        "review_hits": [],
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(nuclei: list[dict[str, object]] | None = None) -> dict[str, object]:
    values = nuclei or [_nucleus()]
    return {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "row_nuclei": values,
        "row_nucleus_candidate_count": len(values),
        "source_binding_audit": _binding_audit(),
        "g01_g18_rollup": {"status": "REVIEW_REQUIRED"},
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_one_nucleus_creates_one_atom() -> None:
    result = build_evidence_atom_inventory(_payload())
    assert result["evidence_atom_count"] == 1
    assert result["row_nucleus_count_matches_atom_count"] is True
    assert result["evidence_atoms"][0]["atom_class"] == "ACTION_ANCHOR_ATOM"


def test_match_binding_and_atom_id_are_deterministic() -> None:
    first = build_evidence_atom_inventory(_payload())
    second = build_evidence_atom_inventory(_payload())
    assert first["match_surface_binding_id"] == second["match_surface_binding_id"]
    assert first["evidence_atoms"][0]["evidence_atom_id"] == second["evidence_atoms"][0]["evidence_atom_id"]


def test_match_binding_changes_with_runtime_source_sha() -> None:
    first = build_evidence_atom_inventory(_payload())
    changed = _payload()
    changed["source_binding_audit"][0]["runtime_rehashed_sha256"] = _sha("a")
    second = build_evidence_atom_inventory(changed)
    assert first["match_surface_binding_id"] != second["match_surface_binding_id"]


def test_duplicate_nucleus_id_fails_closed() -> None:
    result = build_evidence_atom_inventory(_payload([_nucleus(), _nucleus()]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("duplicate_nucleus_id") for item in result["hard_block_hits"])


def test_nucleus_count_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["row_nucleus_candidate_count"] = 2
    result = build_evidence_atom_inventory(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "row_nucleus_count_mismatch" in result["hard_block_hits"]


def test_aggregate_overlay_does_not_create_second_atom() -> None:
    result = build_evidence_atom_inventory(_payload([_nucleus(aggregate_overlay=True)]))
    assert result["evidence_atom_count"] == 1
    atom = result["evidence_atoms"][0]
    assert atom["aggregate_overlay_present"] is True
    assert atom["atom_class"] == "ACTION_ANCHOR_ATOM"


def test_action_anchor_requires_exactly_one_family() -> None:
    result = build_evidence_atom_inventory(_payload([_nucleus(family=None)]))
    atom = result["evidence_atoms"][0]
    assert atom["atom_status"] == "REVIEW_REQUIRED"
    assert "action_anchor_family_not_single" in atom["review_hits"]


def test_non_action_role_does_not_require_action_family() -> None:
    nucleus = _nucleus(role="CONTEXT_INTERVAL", family=None, eligibility="CONTEXT_ONLY")
    result = build_evidence_atom_inventory(_payload([nucleus]))
    atom = result["evidence_atoms"][0]
    assert atom["atom_status"] == "PASS"
    assert atom["atom_class"] == "CONTEXT_INTERVAL_ATOM"


def test_unknown_role_remains_review_required() -> None:
    nucleus = _nucleus(role="UNKNOWN_ROLE", family=None, eligibility="REFERENCE_ONLY")
    result = build_evidence_atom_inventory(_payload([nucleus]))
    atom = result["evidence_atoms"][0]
    assert atom["atom_class"] == "REVIEW_REQUIRED_ATOM"
    assert atom["atom_status"] == "REVIEW_REQUIRED"


def test_token_fallback_remains_review_required() -> None:
    nucleus = _nucleus()
    nucleus["mapping_statuses"] = ["TOKEN_FALLBACK_REVIEW_REQUIRED"]
    result = build_evidence_atom_inventory(_payload([nucleus]))
    assert result["evidence_atoms"][0]["atom_status"] == "REVIEW_REQUIRED"


def test_source_sha_lineage_missing_fails_closed() -> None:
    nucleus = _nucleus()
    nucleus["source_sha256_lineage"] = []
    result = build_evidence_atom_inventory(_payload([nucleus]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("nucleus_source_sha_lineage_invalid") for item in result["hard_block_hits"])


def test_zero_coordinate_is_not_missing() -> None:
    result = build_evidence_atom_inventory(_payload([_nucleus(pos_x="0", pos_y="0")]))
    atom = result["evidence_atoms"][0]
    assert atom["coordinate_evidence_status"] == "COORDINATE_PRESENT"
    assert atom["pos_x_candidate"] == "0"
    assert atom["pos_y_candidate"] == "0"


def test_missing_coordinate_remains_explicit() -> None:
    result = build_evidence_atom_inventory(_payload([_nucleus(pos_x=None, pos_y=None)]))
    assert result["coordinate_missing_atom_count"] == 1
    assert result["evidence_atoms"][0]["coordinate_evidence_status"] == "COORDINATE_MISSING"


def test_claim_and_identity_layers_remain_closed() -> None:
    result = build_evidence_atom_inventory(_payload())
    for key in (
        "evidence_atom_is_canonical_event",
        "validated_event_identity",
        "validated_team_identity",
        "validated_player_identity",
        "identity_binding_allowed",
        "base_event_admission_allowed",
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
    assert result["canonical_event_count"] == "UNKNOWN"


def test_input_canonical_event_claim_fails_closed() -> None:
    payload = _payload()
    payload["canonical_event_count"] = 1
    result = build_evidence_atom_inventory(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "canonical_event_count_claimed_by_input" in result["hard_block_hits"]


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "evidence_atom_inventory.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Australia", "Turkey", "World Cup", "Galatasaray", "6935", "77798"):
        assert token not in text
