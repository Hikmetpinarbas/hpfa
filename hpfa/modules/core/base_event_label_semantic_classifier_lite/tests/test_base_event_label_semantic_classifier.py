from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from base_event_label_semantic_classifier import build_match_test, write_outputs

RUNTIME_HEAD = "a" * 40


def atom(label, *, fmt="csv", event_id="1", start=1.0, end=2.0, period=1, x=10.0, y=20.0, code=None, role="players"):
    return {
        "evidence_atom_id": f"{fmt}-{event_id}-{label}",
        "match_binding_id": "active_single_match_current",
        "source_file": f"Players.{fmt}",
        "source_format": fmt,
        "source_role": role,
        "source_row_index": 1,
        "source_event_id_raw": event_id,
        "atom_class": "EXPLANATORY_EVIDENCE_ATOM",
        "raw_label": label,
        "normalized_label": label,
        "period_candidate": period,
        "start_seconds_candidate": start,
        "end_seconds_candidate": end,
        "x_meters": x,
        "y_meters": y,
        "team_raw": "TEAM_A (1)",
        "player_raw": "",
        "code_raw": code or f"9. Player One (1001) - {label}",
    }


def payload(atoms):
    return {"runtime_code_head_sha": RUNTIME_HEAD, "evidence_atoms": atoms}


def test_runtime_code_head_sha_is_required():
    with pytest.raises(ValueError, match="MISSING_RUNTIME_CODE_HEAD_SHA"):
        build_match_test({"evidence_atoms": [atom("passes_accurate")]})


def test_runtime_code_head_sha_must_be_lowercase_full_sha():
    with pytest.raises(ValueError, match="INVALID_RUNTIME_CODE_HEAD_SHA"):
        build_match_test({"runtime_code_head_sha": "A" * 40, "evidence_atoms": []})
    with pytest.raises(ValueError, match="INVALID_RUNTIME_CODE_HEAD_SHA"):
        build_match_test({"runtime_code_head_sha": "a" * 39, "evidence_atoms": []})


def test_runtime_code_head_sha_propagates_to_classifier_payload():
    result = build_match_test(payload([atom("passes_accurate")]))
    assert result["runtime_code_head_sha"] == RUNTIME_HEAD


def test_base_pass_can_be_event_candidate():
    result = build_match_test(payload([atom("passes_accurate")]))
    assert result["base_event_surface_candidate_count"] == 1
    assert result["base_event_family_counts"] == {"PASS": 1}


def test_shot_recovery_duel_are_base_event_families():
    atoms = [
        atom("shots_on_target", event_id="1", start=1),
        atom("ball_recoveries", event_id="2", start=2),
        atom("aerial_challenges_won", event_id="3", start=3),
    ]
    result = build_match_test(payload(atoms))
    assert result["base_event_family_counts"] == {"DUEL": 1, "RECOVERY": 1, "SHOT": 1}


def test_qualifier_label_does_not_create_second_event():
    atoms = [atom("passes_accurate"), atom("passes_forward_accurate", event_id="2"), atom("progressive_passes_accurate", event_id="3")]
    result = build_match_test(payload(atoms))
    assert result["base_event_surface_candidate_count"] == 1
    assert result["attached_event_label_count"] == 3


def test_csv_xml_mirror_is_one_trace_unit():
    atoms = [atom("passes_accurate", fmt="csv", event_id="9"), atom("passes_accurate", fmt="xml", event_id="9")]
    result = build_match_test(payload(atoms))
    assert result["surface_trace_unit_count"] == 1
    assert result["csv_xml_conformant_trace_unit_count"] == 1


def test_goal_kick_is_restart_not_shot():
    result = build_match_test(payload([atom("goal_kicks_short_0_15_m")]))
    assert result["base_event_family_counts"] == {"RESTART": 1}
    assert result["semantic_conflict_count"] == 0


def test_participation_with_shots_does_not_create_shot_event():
    result = build_match_test(payload([atom("involvement_in_attacks_with_shots")]))
    assert result["base_event_surface_candidate_count"] == 0


def test_goalkeeper_shots_are_opponent_action_reflections():
    result = build_match_test(payload([atom("shots_off_target", role="goalkeepers")]))
    assert result["base_event_surface_candidate_count"] == 0
    assert result["cross_role_reflection_relation_count"] == 1


def test_team_action_is_relation_not_duplicate_player_event():
    result = build_match_test(payload([atom("passes_accurate", role="teams")]))
    assert result["base_event_surface_candidate_count"] == 0
    assert result["cross_role_reflection_relation_count"] == 1


def test_tackle_can_be_duel_subtype_without_conflict():
    result = build_match_test(payload([atom("duels_won"), atom("tackles_won", event_id="2")]))
    assert result["semantic_conflict_count"] == 0
    assert result["base_event_family_counts"] == {"DUEL": 1}
    assert result["base_event_surface_candidates"][0]["event_subtype_signals"] == ["TACKLE"]


def test_action_group_requires_period_and_time():
    result = build_match_test(payload([atom("passes_accurate", start=None, end=None, period=None)]))
    assert result["identity_gate_blocker_count"] == 1
    assert result["decision_state"] == "REVIEW_REQUIRED_IDENTITY_GAPS"


def test_provider_definition_phrase_does_not_create_pass_or_interception():
    result = build_match_test(payload([atom("successful_cross_and_pass_interception_attempts")]))
    assert result["base_event_surface_candidate_count"] == 0
    assert "PROVIDER_DEFINITION_ROUTING_REQUIRED" in result["event_label_candidates"][0]["semantic_roles"]


def test_label_can_remain_review_required_while_base_event_is_candidate():
    result = build_match_test(payload([atom("progressive_passes_accurate")]))
    assert result["base_event_surface_candidates"][0]["surface_candidate_status"] == "BASE_EVENT_SURFACE_CANDIDATE"
    assert result["event_label_candidates"][0]["validation_status"] == "REVIEW_REQUIRED_DEFINITION_AUDIT"


def test_xlsx_is_aggregate_not_timeline():
    xlsx = atom("passes", fmt="xlsx")
    xlsx["atom_class"] = "AGGREGATE_OUTCOME_ATOM"
    result = build_match_test(payload([xlsx]))
    assert result["aggregate_outcome_atom_count"] == 1
    assert result["base_event_surface_candidate_count"] == 0


def test_canonical_event_count_stays_unknown():
    result = build_match_test(payload([atom("passes_accurate")]))
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["identity_bound_event_count"] == 0
    assert result["production_release"] is False


def test_nested_phone_output_rejected(tmp_path):
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(payload([])), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(source, tmp_path / "HPFA" / "nested")
