from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from base_event_label_semantic_classifier import build_match_test, write_outputs


def atom(label, *, fmt="csv", event_id="1", start=1.0, end=2.0, x=10.0, y=20.0, code=None, role="players"):
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
        "start_seconds_candidate": start,
        "end_seconds_candidate": end,
        "x_meters": x,
        "y_meters": y,
        "team_raw": "TEAM_A (1)",
        "player_raw": "",
        "code_raw": code or f"9. Player One (1001) - {label}",
    }


def test_base_pass_can_be_event_candidate():
    result = build_match_test({"evidence_atoms": [atom("passes_accurate")]})
    assert result["base_event_surface_candidate_count"] == 1
    assert result["base_event_family_counts"] == {"PASS": 1}


def test_shot_recovery_duel_are_base_event_families():
    atoms = [
        atom("shots_on_target", event_id="1", start=1),
        atom("ball_recoveries", event_id="2", start=2),
        atom("aerial_challenges_won", event_id="3", start=3),
    ]
    result = build_match_test({"evidence_atoms": atoms})
    assert result["base_event_family_counts"] == {"DUEL": 1, "RECOVERY": 1, "SHOT": 1}


def test_qualifier_label_does_not_create_second_event():
    atoms = [
        atom("passes_accurate", event_id="1"),
        atom("passes_forward_accurate", event_id="2"),
        atom("progressive_passes_accurate", event_id="3"),
    ]
    result = build_match_test({"evidence_atoms": atoms})
    assert result["base_event_surface_candidate_count"] == 1
    assert result["attached_event_label_count"] == 3


def test_csv_xml_mirror_is_one_trace_unit():
    atoms = [
        atom("passes_accurate", fmt="csv", event_id="9"),
        atom("passes_accurate", fmt="xml", event_id="9"),
    ]
    result = build_match_test({"evidence_atoms": atoms})
    assert result["surface_trace_unit_count"] == 1
    assert result["csv_xml_conformant_trace_unit_count"] == 1
    assert result["base_event_surface_candidate_count"] == 1


def test_label_can_remain_review_required_while_base_event_is_candidate():
    result = build_match_test({"evidence_atoms": [atom("progressive_passes_accurate")]})
    base = result["base_event_surface_candidates"][0]
    label = result["event_label_candidates"][0]
    assert base["surface_candidate_status"] == "BASE_EVENT_SURFACE_CANDIDATE"
    assert label["validation_status"] == "REVIEW_REQUIRED_DEFINITION_AUDIT"


def test_participation_label_is_not_forced_into_ball_action():
    result = build_match_test({"evidence_atoms": [atom("involvement_in_positional_attacks")]})
    assert result["base_event_surface_candidate_count"] == 0
    assert result["label_only_action_group_count"] == 1
    assert result["event_label_role_counts"]["EVENT_PARTICIPATION_LABEL"] == 1


def test_provider_defined_label_requires_definition_audit():
    result = build_match_test({"evidence_atoms": [atom("successful_pressure")]})
    label = result["event_label_candidates"][0]
    assert "DERIVED_EVENT_CLASS" in label["semantic_roles"]
    assert label["definition_version"] == "UNKNOWN"
    assert label["validation_status"] == "REVIEW_REQUIRED_DEFINITION_AUDIT"


def test_multiple_base_families_fail_to_review():
    atoms = [
        atom("passes_accurate", event_id="1"),
        atom("shots_on_target", event_id="2"),
    ]
    result = build_match_test({"evidence_atoms": atoms})
    assert result["decision_state"] == "REVIEW_REQUIRED_SEMANTIC_CONFLICTS"
    assert result["semantic_conflict_count"] == 1
    assert result["base_event_surface_candidate_count"] == 0


def test_xlsx_is_aggregate_not_timeline():
    xlsx = atom("passes", fmt="xlsx")
    xlsx["atom_class"] = "AGGREGATE_OUTCOME_ATOM"
    result = build_match_test({"evidence_atoms": [xlsx]})
    assert result["aggregate_outcome_atom_count"] == 1
    assert result["base_event_surface_candidate_count"] == 0


def test_canonical_event_count_stays_unknown():
    result = build_match_test({"evidence_atoms": [atom("passes_accurate")]})
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["identity_bound_event_count"] == 0
    assert result["production_release"] is False


def test_nested_phone_output_rejected(tmp_path):
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps({"evidence_atoms": []}), encoding="utf-8")
    try:
        write_outputs(source, tmp_path / "HPFA" / "nested")
    except ValueError as exc:
        assert "nested_phone_output_directory_rejected" in str(exc)
    else:
        raise AssertionError("nested output accepted")


def test_no_sample_match_identity_leak():
    source = (ROOT / "base_event_label_semantic_classifier.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source for token in forbidden)
