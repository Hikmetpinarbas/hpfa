from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "match_local_actor_team_identity_decoder.py"
spec = importlib.util.spec_from_file_location("identity_decoder", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def atom(atom_id: str, *, team: str = "", player: str = "", fmt: str = "csv", atom_class: str = "EXPLANATORY_EVIDENCE_ATOM") -> dict:
    return {
        "evidence_atom_id": atom_id,
        "match_binding_id": "active_single_match_current",
        "source_file": f"surface.{fmt}",
        "source_format": fmt,
        "source_role": "PLAYERS_EVENT_SURFACE",
        "source_row_index": 1,
        "atom_class": atom_class,
        "team_raw": team,
        "player_raw": player,
    }


def payload(*atoms: dict) -> dict:
    return {"match_binding_id": "active_single_match_current", "evidence_atoms": list(atoms)}


def test_team_scoped_player_candidate_is_created() -> None:
    result = module.build_identity_decoder(payload(atom("a1", team="Team Alpha", player="Player One")))
    assert result["team_identity_candidate_count"] == 1
    assert result["actor_identity_candidate_count"] == 1
    assert result["atom_identity_bindings"][0]["binding_status"] == "PROVISIONAL_ACTOR_TEAM_BOUND"


def test_csv_xml_same_surface_supports_one_match_local_actor_candidate() -> None:
    result = module.build_identity_decoder(
        payload(
            atom("a1", team="Team Alpha", player="Player One", fmt="csv"),
            atom("a2", team="Team Alpha", player="Player One", fmt="xml"),
        )
    )
    assert result["actor_identity_candidate_count"] == 1
    candidate = result["actor_identity_candidates"][0]
    assert candidate["cross_surface_support"] is True
    assert candidate["supporting_atom_count"] == 2


def test_case_and_diacritic_variants_remain_raw_but_share_match_local_key() -> None:
    result = module.build_identity_decoder(
        payload(
            atom("a1", team="Team Alpha", player="José Álvarez"),
            atom("a2", team="TEAM ALPHA", player="Jose Alvarez", fmt="xml"),
        )
    )
    assert result["actor_identity_candidate_count"] == 1
    assert result["actor_identity_candidates"][0]["raw_name_variants"] == ["Jose Alvarez", "José Álvarez"]


def test_same_normalized_actor_under_two_teams_requires_review() -> None:
    result = module.build_identity_decoder(
        payload(
            atom("a1", team="Team Alpha", player="Alex Smith"),
            atom("a2", team="Team Beta", player="Alex Smith"),
        )
    )
    assert result["cross_team_actor_name_collision_count"] == 1
    assert result["decision_state"] == "REVIEW_REQUIRED_MATCH_LOCAL_IDENTITY_GAPS"
    assert {item["binding_status"] for item in result["atom_identity_bindings"]} == {"REVIEW_REQUIRED_ACTOR_TEAM_COLLISION"}


def test_actor_without_team_remains_unresolved() -> None:
    result = module.build_identity_decoder(payload(atom("a1", player="Player One")))
    assert result["identity_unresolved_atom_count"] == 1
    assert result["unresolved_identity_surfaces"][0]["reason"] == "actor_present_team_missing"


def test_team_only_atom_can_receive_provisional_team_binding() -> None:
    result = module.build_identity_decoder(payload(atom("a1", team="Team Alpha")))
    assert result["atom_identity_bindings"][0]["binding_status"] == "PROVISIONAL_TEAM_ONLY_BOUND"
    assert result["actor_identity_candidate_count"] == 0


def test_global_identity_truth_is_never_claimed() -> None:
    result = module.build_identity_decoder(payload(atom("a1", team="Team Alpha", player="Player One")))
    assert result["identity_scope"] == "MATCH_LOCAL_ONLY"
    assert result["identity_truth_admitted"] is False
    assert result["global_roster_identity_admitted"] is False


def test_identity_decoder_does_not_admit_base_events() -> None:
    result = module.build_identity_decoder(payload(atom("a1", team="Team Alpha", player="Player One")))
    assert result["base_event_admission_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_empty_evidence_fails_closed() -> None:
    result = module.build_identity_decoder(payload())
    assert result["decision_state"] == "FAIL_CLOSED_NO_EVIDENCE_ATOMS"


def test_nested_phone_output_directory_rejected(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"evidence_atoms": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        module.write_outputs(evidence, tmp_path / "HPFA" / "nested" / "HPFA")


def test_no_sample_match_identity_leak() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8").casefold()
    forbidden = ["australia", "turkey", "irankunda", "calhanoglu", "demiral"]
    assert not any(name in source for name in forbidden)
