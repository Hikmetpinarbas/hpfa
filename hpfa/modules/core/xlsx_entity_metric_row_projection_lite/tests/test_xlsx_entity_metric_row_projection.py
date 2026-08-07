from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

SOURCE = Path(__file__).resolve().parents[1] / "src" / "xlsx_entity_metric_row_projection.py"
SPEC = importlib.util.spec_from_file_location("xlsx_projection_test_module", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_book(path: Path, *, hidden=False, duplicate=False, zero=False, dash=False, formula=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "Main statistics"
    headers = ["Player", "Team", "Minutes played", "Passes accurate", "Passes accurate, %"]
    if duplicate:
        headers.append("Passes accurate, %")
    ws.append(headers)
    ws.append(["Alpha", "Side A", 90, 29 if not zero else 0, 0.73 if not dash else "-"] + ([0.73] if duplicate else []))
    ws.append(["Beta", "Side B", 75, 21, 0.91] + ([0.91] if duplicate else []))
    if formula:
        ws.append(["Gamma", "Side C", 10, "=SUM(D2:D3)", 1.0] + ([1.0] if duplicate else []))
    if hidden:
        h = wb.create_sheet("Metadata")
        h.sheet_state = "hidden"
        h.append(["Key", "Value"])
        h.append(["provider", "candidate"])
    wb.save(path)


def artifacts(path: Path, *, duplicate=False, hidden=False):
    file_sha = sha(path)
    headers = ["Player", "Team", "Minutes played", "Passes accurate", "Passes accurate, %"]
    if duplicate:
        headers.append("Passes accurate, %")
    profiles = [
        {"raw_column": "Player", "normalized_column": "player", "identity_role_candidate": "player", "percent_header_candidate": False},
        {"raw_column": "Team", "normalized_column": "team", "identity_role_candidate": "team", "percent_header_candidate": False},
        {"raw_column": "Minutes played", "normalized_column": "minutes_played", "identity_role_candidate": "minutes", "percent_header_candidate": False},
        {"raw_column": "Passes accurate", "normalized_column": "passes_accurate", "identity_role_candidate": None, "percent_header_candidate": False},
        {"raw_column": "Passes accurate, %", "normalized_column": "passes_accurate_percent", "identity_role_candidate": None, "percent_header_candidate": True},
    ]
    if duplicate:
        profiles.append({"raw_column": "Passes accurate, %", "normalized_column": "passes_accurate_percent", "identity_role_candidate": None, "percent_header_candidate": True})
    inventory = {"files": [{
        "file_id": "file_a", "relative_path": path.name, "extension": ".xlsx",
        "sha256": file_sha, "source_role": "PLAYER_SURFACE_CANDIDATE"
    }]}
    sheets = [{
        "sheet_name": "Main statistics", "sheet_state": "visible", "status": "PASS",
        "header_row_index": 1, "visible_column_count": len(headers), "raw_columns": headers,
        "column_profiles": profiles,
    }]
    if hidden:
        sheets.append({
            "sheet_name": "Metadata", "sheet_state": "hidden", "status": "REVIEW_REQUIRED",
            "header_row_index": 1, "visible_column_count": 2, "raw_columns": ["Key", "Value"],
            "column_profiles": [
                {"raw_column": "Key", "normalized_column": "key", "identity_role_candidate": None, "percent_header_candidate": False},
                {"raw_column": "Value", "normalized_column": "value", "identity_role_candidate": None, "percent_header_candidate": False},
            ]
        })
    audit = {"module_id": "xlsx_surface_reader_lite_v1", "status": "REVIEW_REQUIRED" if hidden else "PASS", "files": [{
        "file_id": "file_a", "relative_path": path.name, "sha256": file_sha,
        "source_role": "PLAYER_SURFACE_CANDIDATE", "sheets": sheets
    }]}
    return inventory, audit


def test_row_alignment_and_candidate_only(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path)
    inv, audit = artifacts(path)
    p = MODULE.build_projection(tmp_path, inv, audit, match_surface_binding_id="msb_test")
    assert p["status"] == "PASS" and p["row_projection_count"] == 2
    row = p["files"][0]["sheets"][0]["rows"][0]
    assert row["identity_candidates"]["player_raw_candidate"] == "Alpha"
    assert row["metric_values"]["passes_accurate"]["raw_value"] == 29
    assert row["metric_values"]["passes_accurate_percent"]["raw_value"] == 0.73
    assert row["source_row_number"] == 2 and row["match_surface_binding_id"] == "msb_test"
    assert row["validated_identity"] is False
    assert p["aggregate_definition_truth"] is False and p["metric_truth"] is False


def test_hidden_sheet_not_projected(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path, hidden=True)
    inv, audit = artifacts(path, hidden=True)
    p = MODULE.build_projection(tmp_path, inv, audit)
    assert p["status"] == "REVIEW_REQUIRED"
    assert len(p["files"][0]["sheets"]) == 1
    assert "hidden_sheet_not_projected:Metadata" in p["files"][0]["review_hits"]


def test_duplicate_normalized_metric_column_blocks_row_projection(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path, duplicate=True)
    inv, audit = artifacts(path, duplicate=True)
    p = MODULE.build_projection(tmp_path, inv, audit)
    sheet = p["files"][0]["sheets"][0]
    assert p["status"] == "REVIEW_REQUIRED"
    assert sheet["projected_row_count"] == 0
    assert "duplicate_normalized_metric_column:passes_accurate_percent" in sheet["review_hits"]


def test_source_sha_binding_is_exact(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path)
    inv, audit = artifacts(path)
    inv["files"][0]["sha256"] = "0" * 64
    p = MODULE.build_projection(tmp_path, inv, audit)
    assert p["status"] == "FAIL_CLOSED"
    assert "xlsx_inventory_audit_sha256_mismatch" in p["hard_block_hits"]


def test_header_binding_mismatch_fails_closed(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path)
    inv, audit = artifacts(path)
    audit["files"][0]["sheets"][0]["raw_columns"][3] = "Wrong"
    p = MODULE.build_projection(tmp_path, inv, audit)
    assert p["status"] == "FAIL_CLOSED"
    assert "xlsx_header_binding_mismatch" in p["hard_block_hits"]


def test_numeric_zero_is_observed_not_missing(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path, zero=True)
    inv, audit = artifacts(path)
    p = MODULE.build_projection(tmp_path, inv, audit)
    m = p["files"][0]["sheets"][0]["rows"][0]["metric_values"]["passes_accurate"]
    assert m["raw_value"] == 0 and m["value_status"] == "OBSERVED" and m["value_kind"] == "number"


def test_dash_string_is_preserved(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path, dash=True)
    inv, audit = artifacts(path)
    p = MODULE.build_projection(tmp_path, inv, audit)
    m = p["files"][0]["sheets"][0]["rows"][0]["metric_values"]["passes_accurate_percent"]
    assert m["raw_value"] == "-" and m["value_kind"] == "string"


def test_formula_without_cached_value_is_not_admitted(tmp_path: Path):
    path = tmp_path / "players.xlsx"; make_book(path, formula=True)
    inv, audit = artifacts(path)
    p = MODULE.build_projection(tmp_path, inv, audit)
    row = p["files"][0]["sheets"][0]["rows"][2]
    m = row["metric_values"]["passes_accurate"]
    assert m["formula_present"] is True and m["value_admitted"] is False
    assert m["value_status"] == "NOT_ADMITTED_FORMULA_CACHE_MISSING"
    assert p["status"] == "REVIEW_REQUIRED"


def test_nested_phone_output_directory_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        MODULE.validate_out("/sdcard/Download/HPFA/xlsx-projection")


def test_active_match_runtime_self_description(tmp_path: Path):
    active = tmp_path / "runtime" / "active_single_match" / "current"; active.mkdir(parents=True)
    path = active / "players.xlsx"; make_book(path)
    inv, audit = artifacts(path)
    invp=active/"inventory.json"; audp=active/"audit.json"
    invp.write_text(json.dumps(inv), encoding="utf-8"); audp.write_text(json.dumps(audit), encoding="utf-8")
    out=tmp_path/"out"
    p=MODULE.write_outputs(active, invp, audp, out, runtime_authority=active, active_match_execution=True)
    assert p["runtime_evidence_status"] == "ACTIVE_MATCH_EXECUTION_COMPLETED_PASS"
    assert p["active_match_evidence_pass"] is True
    assert (out/MODULE.OUT["main"]).is_file() and (out/MODULE.OUT["analyst"]).is_file()


def test_no_sample_match_identity_leak():
    text = SOURCE.read_text(encoding="utf-8").casefold()
    forbidden = ["australia", "turkey", "galatasaray", "fenerbahce", "13.06.2026", "patrick beach", "ugurcan"]
    assert not any(token in text for token in forbidden)
