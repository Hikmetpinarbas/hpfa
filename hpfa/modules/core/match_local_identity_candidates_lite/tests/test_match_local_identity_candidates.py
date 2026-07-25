from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.match_local_identity_candidates_lite.src.match_local_identity_candidates import (
    _exact_subject_prefix,
    _normalize,
    _parse_actor_subject,
    _parse_team_subject,
    build_match_local_identity_candidates,
    validate_out,
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
    binding: str = "msb_fixture",
) -> dict[str, object]:
    return {
        "evidence_atom_id": atom_id,
        "match_surface_binding_id": binding,
        "source_role": source_role,
        "source_relative_paths": ["surface.csv", "surface.xml"],
        "source_sha256_lineage": [_sha("1"), _sha("2")],
        "runtime_rehashed_sha256": {"csv": _sha("1"), "xml": _sha("2")},
        "atom_class": atom_class,
        "raw_label": label,
        "code_raw": code,
        "team_raw_candidate": team,
        "atom_status": "PASS",
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(atoms: list[dict[str, object]] | None = None) -> dict[str, object]:
    values = atoms or [_atom("ea_1")]
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": "msb_fixture",
        "evidence_atoms": values,
        "evidence_atom_count": len(values),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def test_exact_subject_suffix_extraction() -> None:
    assert (
        _exact_subject_prefix(
            "9. Player Alpha (101) - passes accurate",
            "passes accurate",
        )
        == "9. Player Alpha (101)"
    )


def test_suffix_mismatch_does_not_invent_actor() -> None:
    assert _exact_subject_prefix("Player Alpha - shots", "passes") is None


def test_actor_parser_preserves_candidates() -> None:
    parsed = _parse_actor_subject("9. Player Alpha (101)")
    assert parsed["actor_name_raw_candidate"] == "Player Alpha"
    assert parsed["actor_provider_id_candidate"] == "101"
    assert parsed["jersey_number_candidate"] == "9"
    assert parsed["actor_normalized_key"] == "player_alpha"


def test_team_parser_preserves_provider_candidate() -> None:
    parsed = _parse_team_subject("Team One (11)")
    assert parsed["team_name_raw_candidate"] == "Team One"
    assert parsed["team_provider_id_candidate"] == "11"
    assert parsed["team_normalized_key"] == "team_one"


def test_unicode_diacritic_normalization_is_comparison_only() -> None:
    assert _normalize("Çağrı Şen") == "cagri_sen"
    parsed = _parse_actor_subject("7. Çağrı Şen (55)")
    assert parsed["actor_subject_raw_candidate"] == "7. Çağrı Şen (55)"
    assert parsed["actor_name_raw_candidate"] == "Çağrı Şen"


def test_player_atom_binds_actor_candidate() -> None:
    result = build_match_local_identity_candidates(_payload())
    assert result["team_identity_candidate_count"] == 1
    assert result["actor_identity_candidate_count"] == 1
    assert result["actor_candidate_bound_atom_count"] == 1
    assert result["identity_review_required_atom_count"] == 0
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND"
    assert binding["validated_player_identity"] is False


def test_goalkeeper_atom_binds_actor_candidate() -> None:
    atom = _atom(
        "ea_gk",
        source_role="GOALKEEPER_SURFACE_CANDIDATE",
        code="1. Goalkeeper Alpha (201) - saves",
        label="saves",
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND"


def test_team_surface_creates_team_only_binding() -> None:
    atom = _atom(
        "ea_team",
        source_role="TEAM_SURFACE_CANDIDATE",
        code="Team One (11) - passes accurate",
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "TEAM_IDENTITY_CANDIDATE_BOUND"
    assert binding["actor_identity_candidate_id"] is None


def test_boundary_atom_is_identity_not_applicable() -> None:
    atom = _atom(
        "ea_admin",
        source_role="TEAM_SURFACE_CANDIDATE",
        atom_class="ADMINISTRATIVE_ATOM",
        code="start of the first half",
        label="start of the first half",
        team=None,
    )
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["identity_not_applicable_atom_count"] == 1
    assert result["identity_bindings"][0]["decision_state"] == "IDENTITY_NOT_APPLICABLE"


def test_provider_ids_remain_candidate_only() -> None:
    result = build_match_local_identity_candidates(_payload())
    assert result["team_identity_candidates"][0]["team_provider_id_candidates"] == ["11"]
    assert result["actor_identity_candidates"][0]["actor_provider_id_candidates"] == ["101"]
    assert result["identity_truth_admitted"] is False
    assert result["global_roster_identity_admitted"] is False


def test_same_team_name_multiple_provider_ids_is_review_required() -> None:
    atoms = [
        _atom("ea_1", team="Team One (11)"),
        _atom("ea_2", team="Team One (12)", code="10. Player Beta (102) - passes accurate"),
    ]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert result["team_identity_candidates"][0]["decision_state"] == "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
    assert result["identity_review_required_atom_count"] == 2


def test_same_actor_team_multiple_provider_ids_is_review_required() -> None:
    atoms = [
        _atom("ea_1", code="9. Player Alpha (101) - passes accurate"),
        _atom("ea_2", code="9. Player Alpha (102) - passes accurate"),
    ]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert result["actor_identity_candidates"][0]["decision_state"] == "ACTOR_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
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


def test_missing_team_blocks_actor_binding() -> None:
    result = build_match_local_identity_candidates(_payload([_atom("ea_1", team=None)]))
    assert result["identity_bindings"][0]["decision_state"] == "TEAM_CANDIDATE_MISSING"


def test_missing_actor_subject_is_review_required() -> None:
    atom = _atom("ea_1", code="passes accurate", label="passes accurate")
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_CANDIDATE_MISSING"


def test_duplicate_evidence_atom_id_fails_closed() -> None:
    result = build_match_local_identity_candidates(_payload([_atom("ea_1"), _atom("ea_1")]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("duplicate_evidence_atom_id") for item in result["hard_block_hits"])


def test_mixed_match_surface_binding_fails_closed() -> None:
    atoms = [_atom("ea_1"), _atom("ea_2", binding="msb_other")]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("match_surface_binding_mismatch") for item in result["hard_block_hits"])


def test_source_sha_lineage_missing_fails_closed() -> None:
    atom = _atom("ea_1")
    atom["source_sha256_lineage"] = []
    result = build_match_local_identity_candidates(_payload([atom]))
    assert result["status"] == "FAIL_CLOSED"
    assert any(item.startswith("source_sha_lineage_invalid") for item in result["hard_block_hits"])


def test_input_count_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["evidence_atom_count"] = 2
    result = build_match_local_identity_candidates(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "evidence_atom_count_mismatch" in result["hard_block_hits"]


def test_cross_role_records_are_not_event_fused() -> None:
    atoms = [
        _atom("ea_player"),
        _atom(
            "ea_team",
            source_role="TEAM_SURFACE_CANDIDATE",
            code="Team One (11) - passes accurate",
        ),
    ]
    result = build_match_local_identity_candidates(_payload(atoms))
    assert result["identity_binding_record_count"] == 2
    assert result["event_instance_count"] == 0
    assert result["action_bundle_candidate_count"] == 0


def test_claim_and_release_layers_remain_closed() -> None:
    result = build_match_local_identity_candidates(_payload())
    for key in (
        "identity_truth_admitted",
        "global_roster_identity_admitted",
        "cross_match_identity_admitted",
        "validated_team_identity",
        "validated_player_identity",
        "validated_event_identity",
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


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "match_local_identity_candidates.py"
    text = source.read_text(encoding="utf-8")
    for token in ("Australia", "Turkey", "World Cup", "Galatasaray", "6935", "77798"):
        assert token not in text
