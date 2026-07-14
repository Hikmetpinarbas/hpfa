from __future__ import annotations

import json
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from evidence_atom_contract import build_evidence_atom_contract, write_outputs


def _row(**overrides):
    row = {
        "source_file": "Players.csv",
        "source_format": "csv",
        "source_role": "CSV_PRIMARY_CANONICAL_ACTION_SURFACE",
        "source_row_index": 1,
        "source_event_id_raw": "1",
        "event_type_raw": "Passes accurate",
        "period_candidate": "FIRST_HALF",
        "start_seconds_candidate": 5.2,
        "end_seconds_candidate": 6.0,
        "team_raw": "Team A",
        "player_raw": "Player A",
    }
    row.update(overrides)
    return row


def test_visible_rows_are_not_auto_events():
    result = build_evidence_atom_contract({"rows": [_row(), _row(source_row_index=2)]})
    assert result["evidence_atom_count"] == 2
    assert result["event_instance_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert all(atom["event_instance_allowed"] is False for atom in result["evidence_atoms"])


def test_evidence_atom_preserves_source_provenance():
    result = build_evidence_atom_contract({"rows": [_row(source_file="Players.xml", source_format="xml", source_row_index=7)]})
    atom = result["evidence_atoms"][0]
    assert atom["source_file"] == "Players.xml"
    assert atom["source_format"] == "xml"
    assert atom["source_row_index"] == 7
    assert result["source_provenance_complete"] is True


def test_xlsx_total_maps_to_aggregate_atom_not_timeline():
    result = build_evidence_atom_contract({"rows": [_row(source_file="Players.xlsx", source_format="xlsx", row_surface_class="AGGREGATE_VALIDATION")]})
    assert result["evidence_atoms"][0]["atom_class"] == "AGGREGATE_OUTCOME_ATOM"
    assert result["event_instance_count"] == 0


def test_boundary_marker_is_not_ball_action():
    result = build_evidence_atom_contract({"rows": [_row(event_type_raw="Halftime")]})
    assert result["evidence_atoms"][0]["atom_class"] == "MATCH_BOUNDARY_ATOM"


def test_derived_output_is_quarantined():
    result = build_evidence_atom_contract({"rows": [_row(source_format="json", source_role="DERIVED_RUNTIME_OUTPUT")]})
    assert result["evidence_atoms"][0]["atom_class"] == "QUARANTINED_DERIVED_OUTPUT_ATOM"


def test_missing_provenance_requires_review():
    row = _row()
    row.pop("source_row_index")
    result = build_evidence_atom_contract({"rows": [row]})
    assert result["decision_state"] == "REVIEW_REQUIRED_PROVENANCE_GAP"
    assert result["source_provenance_complete"] is False


def test_nested_phone_output_directory_rejected(tmp_path):
    canonical = tmp_path / "canonical.json"
    canonical.write_text(json.dumps({"rows": [_row()]}), encoding="utf-8")
    try:
        write_outputs(canonical, tmp_path / "HPFA" / "nested")
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested output was not rejected")


def test_flat_phone_outputs(tmp_path):
    canonical = tmp_path / "canonical.json"
    canonical.write_text(json.dumps({"rows": [_row()]}), encoding="utf-8")
    out = tmp_path / "HPFA"
    result = write_outputs(canonical, out)
    assert result["decision_state"] == "PASS_EVIDENCE_ATOM_CONTRACT"
    assert (out / "evidence_atom_contract_lite_v1.json").exists()
    assert (out / "evidence_atom_contract_lite_v1.txt").exists()


def test_no_sample_match_identity_leak():
    source = (SRC / "evidence_atom_contract.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "13.06.2026", "6935", "77798"]
    assert not any(token in source for token in forbidden)


def test_canonical_event_count_remains_unknown_until_bundle_admission():
    result = build_evidence_atom_contract({"rows": [_row()]})
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["action_bundle_candidate_count"] == 0
    assert result["production_release"] is False
