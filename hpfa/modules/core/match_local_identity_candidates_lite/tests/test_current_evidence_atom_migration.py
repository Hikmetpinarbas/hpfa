from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.match_local_identity_candidates_lite.src.match_local_identity_candidates import (
    _exact_subject_prefix,
    _parse_actor_subject,
    _parse_team_subject,
    build_match_local_identity_candidates,
    validate_output_root,
)


def _sha(char: str) -> str:
    return char * 64


def _atom(
    atom_id: str,
    *,
    source_role: str = "PLAYER_SURFACE_CANDIDATE",
    atom_class: str = "ACTION_ANCHOR_ATOM",
    code: str = "9. Player Alpha (101) - passes accurate",
    label: str = "passes accurate",
    team: str | None = "Team One (11)",
    atom_status: str = "PASS",
    identity_not_applicable: bool = False,
    binding: str = "msb_fixture",
) -> dict:
    short = {
        "PLAYER_SURFACE_CANDIDATE": "PLAYER",
        "GOALKEEPER_SURFACE_CANDIDATE": "GOALKEEPER",
        "TEAM_SURFACE_CANDIDATE": "TEAM",
    }[source_role]
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": binding,
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
        "source_relative_paths": [f"{short.lower()}.csv", f"{short.lower()}.xml"],
        "source_sha256_lineage": [_sha("1"), _sha("2")],
        "runtime_rehashed_sha256": {"csv": _sha("1"), "xml": _sha("2")},
        "atom_class": atom_class,
        "atom_status": atom_status,
        "raw_label": label,
        "code_raw": code,
        "team_raw_candidate": team,
        "identity_not_applicable": identity_not_applicable,
        "review_hits": ["semantic_mapping_review_required"] if atom_status == "REVIEW_REQUIRED" else [],
        "independent_support_vote_count": 0,
        "independent_source_vote_allowed": False,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "physical_action_identity_truth": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(atoms: list[dict] | None = None, *, status: str = "REVIEW_REQUIRED") -> dict:
    values = atoms or [_atom("ea_1")]
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": status,
        "module_status": status,
        "match_surface_binding_id": "msb_fixture",
        "evidence_atoms": values,
        "evidence_atom_count": len(values),
        "hard_block_hits": [],
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_exact_subject_suffix_is_required() -> None:
    assert _exact_subject_prefix("9. Player Alpha (101) - passes accurate", "passes accurate") == "9. Player Alpha (101)"
    assert _exact_subject_prefix("Player Alpha - shots", "passes") is None


def test_candidate_parsers_preserve_raw_identity_evidence() -> None:
    team = _parse_team_subject("Team One (11)")
    actor = _parse_actor_subject("9. José Álvarez (101)")
    assert team["team_name_raw_candidate"] == "Team One"
    assert team["team_provider_id_candidate"] == "11"
    assert actor["actor_name_raw_candidate"] == "José Álvarez"
    assert actor["actor_provider_id_candidate"] == "101"
    assert actor["jersey_number_candidate"] == "9"
    assert actor["actor_normalized_key"] == "jose_alvarez"


def test_one_evidence_atom_gets_one_identity_binding() -> None:
    result = build_match_local_identity_candidates(_payload())
    assert result["evidence_atom_count"] == 1
    assert result["identity_binding_record_count"] == 1
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND"


def test_team_surface_gets_team_only_binding() -> None:
    atom = _atom(
        "ea_team",
        source_role="TEAM_SURFACE_CANDIDATE",
        code="Team One (11) - passes accurate",
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "TEAM_IDENTITY_CANDIDATE_BOUND"
    assert binding["actor_identity_candidate_id"] is None


def test_goalkeeper_surface_can_bind_actor_candidate() -> None:
    atom = _atom(
        "ea_gk",
        source_role="GOALKEEPER_SURFACE_CANDIDATE",
        code="1. Keeper Alpha (201) - saves",
        label="saves",
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND"


def test_admin_review_atom_is_identity_not_applicable() -> None:
    atom = _atom(
        "ea_admin",
        source_role="TEAM_SURFACE_CANDIDATE",
        atom_class="ADMINISTRATIVE_ATOM",
        code="start of the first half",
        label="start of the first half",
        team=None,
        atom_status="REVIEW_REQUIRED",
        identity_not_applicable=True,
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "IDENTITY_NOT_APPLICABLE"
    assert binding["upstream_review_hits"] == ["semantic_mapping_review_required"]
    assert result["identity_review_required_atom_count"] == 0


def test_semantic_review_does_not_invent_identity_failure() -> None:
    atom = _atom("ea_review", atom_status="REVIEW_REQUIRED")
    result = build_match_local_identity_candidates(_payload([atom]))
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND"
    assert binding["upstream_review_hits"] == ["semantic_mapping_review_required"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_structured_lineage_not_positional_sha_lists_is_authority() -> None:
    atom = _atom("ea_lineage")
    atom["source_relative_paths"] = ["historical-shape-does-not-control"]
    atom["source_sha256_lineage"] = []
    atom["runtime_rehashed_sha256"] = {}
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["hard_block_hits"] == []
    assert result["identity_binding_record_count"] == 1


def test_xlsx_lineage_fails_closed() -> None:
    atom = _atom("ea_xlsx")
    atom["source_lineage_records"][0]["source_format"] = "xlsx"
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["status"] == "FAIL_CLOSED"
    assert any("source_lineage_format_rejected" in item for item in result["hard_block_hits"])


def test_source_row_index_cannot_be_temporal_order_truth() -> None:
    atom = _atom("ea_order")
    atom["source_lineage_records"][0]["source_row_index_is_order_truth"] = True
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["status"] == "FAIL_CLOSED"
    assert any("source_row_index_promoted_to_order_truth" in item for item in result["hard_block_hits"])


def test_independent_support_vote_cannot_be_reintroduced() -> None:
    atom = _atom("ea_vote")
    atom["independent_support_vote_count"] = 1
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["status"] == "FAIL_CLOSED"
    assert any("independent_support_vote_claimed" in item for item in result["hard_block_hits"])


def test_provider_id_conflicts_remain_review_required() -> None:
    atoms = [
        _atom("ea_1", team="Team One (11)"),
        _atom("ea_2", team="Team One (12)", code="10. Player Beta (102) - passes accurate"),
    ]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert result["team_identity_candidates"][0]["decision_state"] == "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
    assert result["identity_review_required_atom_count"] == 2


def test_same_actor_provider_id_across_teams_is_review_required() -> None:
    atoms = [
        _atom("ea_1", team="Team One (11)", code="9. Player Alpha (101) - passes accurate"),
        _atom("ea_2", team="Team Two (22)", code="9. Player Alpha (101) - passes accurate"),
    ]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert all(
        candidate["decision_state"] == "CROSS_TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        for candidate in result["actor_identity_candidates"]
    )


def test_missing_exact_actor_subject_is_review_required_not_guessed() -> None:
    atom = _atom("ea_missing", code="passes accurate", label="passes accurate")
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_CANDIDATE_MISSING"


def test_duplicate_atom_id_fails_closed() -> None:
    result = build_match_local_identity_candidates(_payload([_atom("ea_1"), _atom("ea_1")]))
    assert result["status"] == "FAIL_CLOSED"
    assert any("duplicate_evidence_atom_id" in item for item in result["hard_block_hits"])


def test_claim_and_release_boundaries_remain_closed() -> None:
    result = build_match_local_identity_candidates(_payload())
    for key in (
        "identity_truth_admitted",
        "global_roster_identity_admitted",
        "cross_match_identity_admitted",
        "validated_team_identity",
        "validated_player_identity",
        "validated_event_identity",
        "physical_action_identity_truth",
        "event_instance_allowed",
        "cross_role_fusion_allowed",
        "independent_source_vote_allowed",
        "sequence_truth",
        "possession_truth",
        "phase_truth",
        "tactical_truth",
        "comparison_allowed",
        "claim_allowed",
        "production_release",
    ):
        assert result[key] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root(tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "match_local_identity_candidates.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Australia", "Turkey", "Galatasaray"):
        assert token not in text
