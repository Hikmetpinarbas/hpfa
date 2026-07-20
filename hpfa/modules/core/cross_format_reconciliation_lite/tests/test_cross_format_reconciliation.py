from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from cross_format_reconciliation import build_reconciliation, write_outputs

ROLE = "PLAYER_SURFACE_CANDIDATE"


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"])
        writer.writerows(rows)


def write_xml(path: Path, rows: list[dict[str, str]]) -> None:
    parts = ["<file><ALL_INSTANCES>"]
    for row in rows:
        parts.append("<instance>")
        for key in ("ID", "start", "end", "code"):
            parts.append(f"<{key}>{row[key]}</{key}>")
        for group in ("Team", "Action", "Half", "pos_x", "pos_y"):
            parts.append(f"<label><group>{group}</group><text>{row[group]}</text></label>")
        parts.append("</instance>")
    parts.append("</ALL_INSTANCES></file>")
    path.write_text("".join(parts), encoding="utf-8")


def csv_audit(relative: str = "players.csv", sha: str = "csv-sha") -> dict:
    return {
        "module_id": "csv_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "files": [{
            "relative_path": relative,
            "source_role": ROLE,
            "sha256": sha,
            "encoding_candidate": "utf-8",
            "delimiter_candidate": ",",
            "raw_columns": ["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"],
            "field_bundle": {"start": "start", "end": "end", "period": "half", "action": "action", "team": "team", "start_x": "pos_x", "start_y": "pos_y"},
        }],
    }


def xml_audit(relative: str = "players.xml", sha: str = "xml-sha") -> dict:
    return {
        "module_id": "xml_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "files": [{
            "relative_path": relative,
            "source_role": ROLE,
            "sha256": sha,
            "selected_row_tag_candidate": "instance",
            "security_guard": {"status": "PASS", "dtd_or_entity_declaration_present": False},
        }],
    }


def xlsx_audit() -> dict:
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "files": [{
            "relative_path": "players.xlsx",
            "source_role": ROLE,
            "sha256": "xlsx-sha",
            "sheets": [{"profiled_row_count": 2, "formula_audit": {"formula_cell_count": 0}}],
        }],
    }


def inventory() -> dict:
    return {
        "module_id": "multiformat_file_inventory_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "files": [],
    }


def semantics() -> dict:
    return {
        "module_id": "provider_alias_field_semantics_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "required_anchor_audit": {
            "csv": {"ready_for_candidate_reconciliation": True},
            "xml": {"ready_for_candidate_reconciliation": True},
        },
        "candidate_equivalence_groups": [{"validated_equivalence": False}],
    }


def make_surfaces(root: Path, *, xml_action: str = "Passes accurate", xml_id: str = "1") -> None:
    write_csv(root / "players.csv", [["1", "5.21", "11.21", "7. Player (10) - Passes accurate", "Team A (1)", "Passes accurate", "1", "52.5", "34.0"]])
    write_xml(root / "players.xml", [{
        "ID": xml_id,
        "start": "5.210",
        "end": "11.210",
        "code": f"7. Player (10) - {xml_action}",
        "Team": "Team A (1)",
        "Action": xml_action,
        "Half": "1.0",
        "pos_x": "52.50",
        "pos_y": "34",
    }])


def test_exact_csv_xml_surface_alignment_candidate(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    result = build_reconciliation(tmp_path, inventory(), csv_audit(), xlsx_audit(), xml_audit(), semantics())
    assert result["status"] == "PASS"
    pair = result["pair_reports"][0]
    assert pair["decision"] == "PASS_ALIGNMENT_CANDIDATE"
    assert pair["exact_surface_alignment_candidate_count"] == 1
    assert pair["validated_cross_format_equivalence"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_equal_row_count_does_not_prove_alignment(tmp_path: Path) -> None:
    make_surfaces(tmp_path, xml_action="Inaccurate passes")
    result = build_reconciliation(tmp_path, inventory(), csv_audit(), xlsx_audit(), xml_audit(), semantics())
    pair = result["pair_reports"][0]
    assert pair["row_count_equal_signal"] is True
    assert pair["required_field_mismatch_candidate_count"] == 1
    assert "equal_row_count_does_not_prove_alignment" in pair["parse_warnings"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_unmatched_ids_are_preserved(tmp_path: Path) -> None:
    make_surfaces(tmp_path, xml_id="2")
    result = build_reconciliation(tmp_path, inventory(), csv_audit(), xlsx_audit(), xml_audit(), semantics())
    pair = result["pair_reports"][0]
    assert pair["csv_only_id_candidate_count"] == 1
    assert pair["xml_only_id_candidate_count"] == 1
    assert result["status"] == "REVIEW_REQUIRED"


def test_duplicate_id_candidate_blocks_fusion(tmp_path: Path) -> None:
    write_csv(tmp_path / "players.csv", [
        ["1", "1", "2", "A - Pass", "T", "Pass", "1", "1", "1"],
        ["1", "2", "3", "A - Shot", "T", "Shot", "1", "2", "2"],
    ])
    write_xml(tmp_path / "players.xml", [{"ID": "1", "start": "1", "end": "2", "code": "A - Pass", "Team": "T", "Action": "Pass", "Half": "1", "pos_x": "1", "pos_y": "1"}])
    result = build_reconciliation(tmp_path, inventory(), csv_audit(), xlsx_audit(), xml_audit(), semantics())
    assert result["status"] == "FAIL_CLOSED"
    assert any("duplicate_surface_row_id_candidate" in value for value in result["hard_block_hits"])


def test_xlsx_is_not_independent_confirmation(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    result = build_reconciliation(tmp_path, inventory(), csv_audit(), xlsx_audit(), xml_audit(), semantics())
    support = result["pair_reports"][0]["xlsx_support"]
    assert support["source_dependency_status"] == "DERIVATION_DEPENDENCY_UNRESOLVED"
    assert support["independent_confirmation_allowed"] is False
    assert support["aggregate_definition_truth"] is False


def test_exact_duplicate_reflections_are_not_recounted(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    csv_payload = csv_audit()
    csv_payload["files"].append(dict(csv_payload["files"][0]))
    result = build_reconciliation(tmp_path, inventory(), csv_payload, xlsx_audit(), xml_audit(), semantics())
    assert result["duplicate_reflection_audit"]["csv_duplicate_reflections_not_recounted"] == 1
    assert result["role_pair_count"] == 1


def test_upstream_canonical_event_count_claim_blocks(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    bad = csv_audit()
    bad["canonical_event_count"] = 1
    result = build_reconciliation(tmp_path, inventory(), bad, xlsx_audit(), xml_audit(), semantics())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("canonical_event_count_claimed") for value in result["hard_block_hits"])


def test_active_match_execution_and_flat_outputs(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    make_surfaces(root)
    payloads = {
        "inventory.json": inventory(),
        "csv.json": csv_audit(),
        "xlsx.json": xlsx_audit(),
        "xml.json": xml_audit(),
        "semantics.json": semantics(),
    }
    for name, payload in payloads.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    result = write_outputs(root, tmp_path / "inventory.json", tmp_path / "csv.json", tmp_path / "xlsx.json", tmp_path / "xml.json", tmp_path / "semantics.json", tmp_path / "HPFA")
    assert result["active_match_evidence_pass"] is True
    assert result["production_release"] is False
    assert (tmp_path / "HPFA" / "cross_format_reconciliation_lite_v1.json").is_file()


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    make_surfaces(root)
    for name, payload in {"i": inventory(), "c": csv_audit(), "x": xlsx_audit(), "m": xml_audit(), "s": semantics()}.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(root, tmp_path / "i", tmp_path / "c", tmp_path / "x", tmp_path / "m", tmp_path / "s", tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "cross_format_reconciliation.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798", "Juventus", "Galatasaray"]
    assert not any(token in source for token in forbidden)
