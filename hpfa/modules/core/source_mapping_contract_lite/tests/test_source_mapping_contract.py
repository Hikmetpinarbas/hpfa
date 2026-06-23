import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "source_mapping_contract_lite" / "src"
sys.path.insert(0, str(SRC))

from source_mapping_contract import build_contract, write_outputs


def write_csv(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_unmapped_columns_preserved(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    write_csv(active / "Players.csv", "action,team,pos_x,pos_y,custom_note\nPass,A,10,20,keep-me\n")

    contract = build_contract(active, root=ROOT)

    source = contract["sources"][0]
    assert source["extras_preserved"] is True
    assert "custom_note" in source["unmapped_columns"]
    assert source["extras_sample"][0]["extras"]["custom_note"] == "keep-me"
    unmapped = [row for row in contract["mappings"] if row["source_field"] == "custom_note"][0]
    assert unmapped["mapped"] is False
    assert unmapped["unmapped_policy"] == "preserve_in_extras"


def test_required_columns_fail_closed(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    write_csv(active / "Players.csv", "team,custom_note\nA,missing-event-and-coords\n")

    contract = build_contract(active, strict_required=True, root=ROOT)

    assert contract["status"] == "FAIL_CLOSED"
    source = contract["sources"][0]
    assert source["decision"] == "FAIL_CLOSED_MISSING_REQUIRED"
    assert source["missing_required_fields"] == ["event_type", "x", "y"]


def test_zero_supported_surfaces_fail_closed(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    (active / "notes.txt").write_text("not a supported surface", encoding="utf-8")

    contract = build_contract(active, root=ROOT)

    assert contract["status"] == "FAIL_CLOSED"
    assert contract["overall_decision"] == "NO_SUPPORTED_SURFACES"
    assert contract["source_count"] == 0
    assert contract["mapping_record_count"] == 0


def test_aggregate_xlsx_skips_event_required_policy(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    # Minimal XLSX is expensive to generate here; assert via extension-level classifier using a copied CSV-like xlsx path.
    # The lightweight reader will return no rows/headers for invalid xlsx, so test the policy with a monkeypatched reader surface.
    xlsx = active / "Players.xlsx"
    xlsx.write_bytes(b"not-a-real-xlsx")

    contract = build_contract(active, strict_required=True, root=ROOT)

    assert contract["status"] == "REVIEW_REQUIRED"
    source = contract["sources"][0]
    assert source["source_format"] == "xlsx"
    assert source["source_surface_kind"] == "aggregate_support"
    assert source["missing_required_fields"] == []
    assert source["required_field_policy"] == "not_applicable_aggregate_support_surface"
    assert source["decision"] == "NO_ROWS_OR_NO_HEADERS"


def test_row_lineage_preserved_in_contract(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    write_csv(active / "Teams.csv", "event_type,x,y,extra\nShot,80,30,lineage\n")

    contract = build_contract(active, root=ROOT)

    assert contract["sources"][0]["source_file"] == "Teams.csv"
    assert contract["sources"][0]["source_format"] == "csv"
    assert contract["sources"][0]["source_role"] == "teams"
    for row in contract["mappings"]:
        assert row["source_file"] == "Teams.csv"
        assert row["source_format"] == "csv"
        assert row["source_role"] == "teams"


def test_active_match_contract_outputs_are_flat(tmp_path):
    active = tmp_path / "active"
    out = tmp_path / "HPFA"
    active.mkdir()
    out.mkdir()
    write_csv(active / "Players.csv", "action,team,pos_x,pos_y,custom_note\nPass,A,10,20,keep-me\n")

    audit = write_outputs(active, out, root=ROOT)

    assert audit["status"] == "PASS"
    assert (out / "source_mapping_contract_v1.json").exists()
    assert (out / "source_mapping_audit_v1.json").exists()
    assert (out / "source_mapping_audit_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())
    contract = json.loads((out / "source_mapping_contract_v1.json").read_text(encoding="utf-8"))
    assert contract["event_count_claim_allowed"] is False


def test_nested_phone_output_directory_rejected(tmp_path):
    active = tmp_path / "active"
    active.mkdir()
    write_csv(active / "Players.csv", "action,team,pos_x,pos_y\nPass,A,10,20\n")

    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(active, "/sdcard/Download/HPFA/source-mapping", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "source_mapping_contract.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "source_mapping_contract_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "Galatasaray", "World Cup", "13.06.2026", "25.02.2026"]:
        assert token not in src
        assert token not in contract
