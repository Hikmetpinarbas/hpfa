from __future__ import annotations

from hpfa.modules.core.evidence_atom_inventory_lite.src.evidence_atom_inventory import (
    build_evidence_atom_inventory,
)


def _sha(char: str) -> str:
    return char * 64


def _payload(role: str, family: str, eligibility: str) -> dict[str, object]:
    nucleus = {
        "nucleus_id": "rn_role_family",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "provider_row_id_candidate": "1",
        "source_relative_paths": ["Players.csv", "Players.xml"],
        "source_sha256_lineage": [_sha("3"), _sha("4")],
        "runtime_rehashed_sha256": {"csv": _sha("3"), "xml": _sha("4")},
        "action_raw": "Provider label",
        "code_raw": "Subject - Provider label",
        "team_raw_candidate": "TEAM_A",
        "period_candidate": "1",
        "start_candidate": "10",
        "end_candidate": "11",
        "pos_x_candidate": "20",
        "pos_y_candidate": "30",
        "semantic_role_candidates": [role],
        "action_family_candidates": [family],
        "outcome_candidates": [],
        "downstream_eligibility_candidates": [eligibility],
        "mapping_statuses": ["EXACT_REVIEWED_CANDIDATE"],
        "mapping_rule_ids": ["rule_1"],
        "cross_format_support_status": "CSV_XML_REQUIRED_ALIGNED_PRESENT_SUPPORT",
        "aggregate_definition_dependency": "DERIVATION_DEPENDENCY_UNRESOLVED",
        "nucleus_status": "PASS",
        "review_hits": [],
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }
    bindings = []
    for source_role, csv_char, xml_char in (
        ("GOALKEEPER_SURFACE_CANDIDATE", "1", "2"),
        ("PLAYER_SURFACE_CANDIDATE", "3", "4"),
        ("TEAM_SURFACE_CANDIDATE", "5", "6"),
    ):
        bindings.extend(
            [
                {
                    "source_role": source_role,
                    "source_format": "csv",
                    "runtime_rehashed_sha256": _sha(csv_char),
                    "audit_sha_match": True,
                },
                {
                    "source_role": source_role,
                    "source_format": "xml",
                    "runtime_rehashed_sha256": _sha(xml_char),
                    "audit_sha_match": True,
                },
            ]
        )
    return {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "row_nuclei": [nucleus],
        "row_nucleus_candidate_count": 1,
        "source_binding_audit": bindings,
        "g01_g18_rollup": {"status": "REVIEW_REQUIRED"},
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_reference_role_may_preserve_descriptive_action_family() -> None:
    result = build_evidence_atom_inventory(
        _payload("OPPONENT_ACTION_REFERENCE", "SHOT", "REFERENCE_ONLY")
    )
    atom = result["evidence_atoms"][0]
    assert atom["atom_status"] == "PASS"
    assert atom["atom_class"] == "REFERENCE_ATOM"
    assert atom["action_family_candidates"] == ["SHOT"]


def test_derived_role_may_preserve_source_action_family() -> None:
    result = build_evidence_atom_inventory(
        _payload("DERIVED_CONSEQUENCE_CANDIDATE", "ERROR", "DERIVED_ONLY")
    )
    atom = result["evidence_atoms"][0]
    assert atom["atom_status"] == "PASS"
    assert atom["atom_class"] == "DERIVED_CONSEQUENCE_ATOM"


def test_administrative_role_may_preserve_marker_family() -> None:
    result = build_evidence_atom_inventory(
        _payload("ADMINISTRATIVE_MARKER", "CARD", "ADMIN_ONLY")
    )
    atom = result["evidence_atoms"][0]
    assert atom["atom_status"] == "PASS"
    assert atom["atom_class"] == "ADMINISTRATIVE_ATOM"
