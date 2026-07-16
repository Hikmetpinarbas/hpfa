from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from match_local_identity_decoder import build_match_local_identity_decoder, write_outputs


def _atom(
    atom_id: str | None,
    team: str | None,
    player: str | None,
    *,
    match_binding_id: str | None = "active_single_match_current",
    source_format: str = "csv",
    **extra,
):
    atom = {
        "evidence_atom_id": atom_id,
        "match_binding_id": match_binding_id,
        "team_raw": team,
        "player_raw": player,
        "source_file": f"surface.{source_format}",
        "source_format": source_format,
        "source_role": "players",
        "source_row_index": 1,
        "source_extra_fields": {},
    }
    atom.update(extra)
    return atom


def test_team_and_actor_bind_match_locally_without_event_admission():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [_atom("ea_1", "Team A", "Player One")]
    })
    assert result["identity_bound_atom_count"] == 1
    assert result["identity_bindings"][0]["decision_state"] == "ACTOR_IDENTITY_BOUND"
    assert result["identity_scope"] == "MATCH_LOCAL_ONLY"
    assert result["identity_truth_admitted"] is False
    assert result["global_roster_identity_admitted"] is False
    assert result["base_event_admission_allowed"] is False
    assert result["event_instance_count"] == 0
    assert result["action_bundle_candidate_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_team_only_atom_does_not_invent_actor():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [_atom("ea_1", "Team A", None)]
    })
    binding = result["identity_bindings"][0]
    assert binding["decision_state"] == "TEAM_IDENTITY_BOUND"
    assert binding["actor_identity_id"] is None


def test_missing_team_fails_closed():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [_atom("ea_1", None, "Player One")]
    })
    assert result["identity_bindings"][0]["decision_state"] == "TEAM_IDENTITY_MISSING"
    assert result["unresolved_atom_count"] == 1


def test_same_actor_name_across_teams_requires_review_without_provider_id():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Alex"),
            _atom("ea_2", "Team B", "Alex"),
        ]
    })
    assert all(
        binding["decision_state"] == "CROSS_TEAM_CONFLICT_REVIEW_REQUIRED"
        for binding in result["identity_bindings"]
    )
    assert result["identity_bound_atom_count"] == 0


def test_provider_actor_id_disambiguates_same_name_across_teams():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Alex", source_extra_fields={"player_id": "10"}),
            _atom("ea_2", "Team B", "Alex", source_extra_fields={"player_id": "20"}),
        ]
    })
    assert all(
        binding["decision_state"] == "ACTOR_IDENTITY_BOUND"
        for binding in result["identity_bindings"]
    )


def test_same_provider_id_across_teams_requires_review():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Alex", source_extra_fields={"player_id": "10"}),
            _atom("ea_2", "Team B", "Alex", source_extra_fields={"player_id": "10"}),
        ]
    })
    assert all(
        binding["decision_state"] == "CROSS_TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        for binding in result["identity_bindings"]
    )


def test_conflicting_provider_ids_require_alias_review():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Player One", source_extra_fields={"player_id": "10"}),
            _atom("ea_2", "Team A", "Player One", source_extra_fields={"player_id": "11"}),
        ]
    })
    assert all(
        binding["decision_state"] == "AMBIGUOUS_ALIAS_REVIEW_REQUIRED"
        for binding in result["identity_bindings"]
    )


def test_identity_is_scoped_to_same_match_binding():
    first = build_match_local_identity_decoder({
        "match_binding_id": "match_a",
        "evidence_atoms": [_atom("ea_1", "Team A", "Player One", match_binding_id="match_a")],
    })
    second = build_match_local_identity_decoder({
        "match_binding_id": "match_b",
        "evidence_atoms": [_atom("ea_1", "Team A", "Player One", match_binding_id="match_b")],
    })
    assert first["actor_identity_candidates"][0]["actor_identity_id"] != second["actor_identity_candidates"][0]["actor_identity_id"]


def test_case_and_diacritic_variants_share_candidate_but_preserve_raw_aliases():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "José Álvarez", source_format="csv"),
            _atom("ea_2", "TEAM A", "Jose Alvarez", source_format="xml"),
        ]
    })
    assert len(result["actor_identity_candidates"]) == 1
    candidate = result["actor_identity_candidates"][0]
    assert candidate["actor_aliases_raw"] == ["Jose Alvarez", "José Álvarez"]
    assert candidate["cross_surface_support"] is True
    assert candidate["supporting_evidence_atom_ids"] == ["ea_1", "ea_2"]


def test_empty_evidence_fails_closed():
    result = build_match_local_identity_decoder({
        "match_binding_id": "match_a",
        "evidence_atoms": [],
    })
    assert result["decision_state"] == "FAIL_CLOSED_NO_EVIDENCE_ATOMS"
    assert result["identity_bound_atom_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"


def test_missing_match_binding_fails_closed():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Player One", match_binding_id=None)
        ]
    })
    assert result["decision_state"] == "FAIL_CLOSED_MATCH_BINDING_MISSING"
    assert result["identity_bindings"][0]["decision_state"] == "MATCH_BINDING_MISSING"
    assert result["identity_bound_atom_count"] == 0


def test_conflicting_match_bindings_require_review():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [
            _atom("ea_1", "Team A", "Player One", match_binding_id="match_a"),
            _atom("ea_2", "Team A", "Player One", match_binding_id="match_b"),
        ]
    })
    assert result["decision_state"] == "REVIEW_REQUIRED_MATCH_BINDING_CONFLICT"
    assert result["match_binding_consistent"] is False
    assert result["identity_bound_atom_count"] == 0


def test_missing_evidence_atom_id_remains_unresolved():
    result = build_match_local_identity_decoder({
        "evidence_atoms": [_atom(None, "Team A", "Player One")]
    })
    assert result["identity_bindings"][0]["decision_state"] == "EVIDENCE_ATOM_ID_MISSING"
    assert result["unresolved_atom_count"] == 1


def test_no_sample_match_identity_leak():
    result = build_match_local_identity_decoder({"evidence_atoms": []})
    serialized = json.dumps(result)
    for forbidden in ("Australia", "Turkey", "World Cup", "13.06.2026"):
        assert forbidden not in serialized


def test_nested_phone_output_directory_rejected(tmp_path):
    source = tmp_path / "atoms.json"
    source.write_text(json.dumps({"evidence_atoms": []}), encoding="utf-8")
    nested = tmp_path / "HPFA" / "HPFA"
    try:
        write_outputs(source, nested)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested output was not rejected")
