from __future__ import annotations

import match_local_identity_candidates_lite as runtime_identity
from hpfa.modules.core.match_local_identity_candidates_lite.src.match_local_identity_candidates import (
    build_match_local_identity_candidates,
)


def _sha(char: str) -> str:
    return char * 64


def _team_atom(
    atom_id: str,
    *,
    code: str = "Team One (11) - passes accurate",
    label: str = "passes accurate",
    team: str | None = None,
    atom_class: str = "ACTION_ANCHOR_ATOM",
    identity_not_applicable: bool = False,
) -> dict:
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": "msb_fixture",
        "source_role": "TEAM_SURFACE_CANDIDATE",
        "source_role_short": "TEAM",
        "source_lineage_records": [
            {
                "source_file": "team.csv",
                "source_format": "csv",
                "source_role": "TEAM",
                "source_row_index": 1,
                "source_sha256": _sha("1"),
                "source_row_index_is_order_truth": False,
            },
            {
                "source_file": "team.xml",
                "source_format": "xml",
                "source_role": "TEAM",
                "source_row_index": 2,
                "source_sha256": _sha("2"),
                "source_row_index_is_order_truth": False,
            },
        ],
        "atom_class": atom_class,
        "atom_status": "REVIEW_REQUIRED" if identity_not_applicable else "PASS",
        "raw_label": label,
        "code_raw": code,
        "team_raw_candidate": team,
        "identity_not_applicable": identity_not_applicable,
        "review_hits": ["visible_field_serialization_discrepancy"] if identity_not_applicable else [],
        "independent_support_vote_count": 0,
        "independent_source_vote_allowed": False,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "physical_action_identity_truth": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(atoms: list[dict]) -> dict:
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": "msb_fixture",
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "evidence_atom_pass_count": sum(atom["atom_status"] == "PASS" for atom in atoms),
        "evidence_atom_review_required_count": sum(
            atom["atom_status"] == "REVIEW_REQUIRED" for atom in atoms
        ),
        "current_content_source_role_bridge_status": "PASS",
        "hard_block_hits": [],
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_team_surface_without_team_field_binds_from_exact_code_subject() -> None:
    evidence = _payload([_team_atom("ea_team")])
    bridged, applied, review = runtime_identity._bridge_team_subject_candidates(evidence)
    assert applied == 1
    assert review == 0
    assert evidence["evidence_atoms"][0]["team_raw_candidate"] is None
    assert bridged["evidence_atoms"][0]["team_raw_candidate"] == "Team One (11)"

    result = build_match_local_identity_candidates(bridged)
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "TEAM_IDENTITY_CANDIDATE_BOUND"
    assert binding["team_name_raw_candidate"] == "Team One"
    assert binding["team_provider_id_candidate"] == "11"
    assert binding["actor_identity_candidate_id"] is None


def test_team_subject_bridge_never_guesses_without_exact_label_suffix() -> None:
    evidence = _payload([
        _team_atom("ea_team", code="Team One (11) - shots", label="passes accurate")
    ])
    bridged, applied, review = runtime_identity._bridge_team_subject_candidates(evidence)
    assert applied == 0
    assert review == 1
    assert bridged["evidence_atoms"][0]["team_raw_candidate"] is None

    result = build_match_local_identity_candidates(bridged)
    assert result["identity_bindings"][0]["decision_state"] == "TEAM_CANDIDATE_MISSING"


def test_administrative_team_atom_is_not_subject_bridged() -> None:
    evidence = _payload([
        _team_atom(
            "ea_admin",
            code="start of the first half",
            label="start of the first half",
            atom_class="ADMINISTRATIVE_ATOM",
            identity_not_applicable=True,
        )
    ])
    bridged, applied, review = runtime_identity._bridge_team_subject_candidates(evidence)
    assert applied == 0
    assert review == 0
    result = build_match_local_identity_candidates(bridged)
    assert result["identity_bindings"][0]["decision_state"] == "IDENTITY_NOT_APPLICABLE"


def test_runtime_payload_surfaces_bridge_audit_counts() -> None:
    evidence = _payload([_team_atom("ea_team")])
    result = runtime_identity._build_identity_payload(evidence)
    assert result["team_subject_code_prefix_bridge_mode"] == "EXACT_SUFFIX_ONLY_WHEN_TEAM_FIELD_ABSENT"
    assert result["team_subject_code_prefix_bridge_applied_count"] == 1
    assert result["team_subject_code_prefix_bridge_review_count"] == 0
    assert result["team_candidate_bound_atom_count"] == 1
    assert result["identity_review_required_atom_count"] == 0
