from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
SOURCE = SRC / "xml_surface_reader.py"
SPEC = importlib.util.spec_from_file_location("xml_surface_reader_test_module", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_xml(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.write_text(text, encoding=encoding)


def inventory_for(
    path: Path,
    *,
    duplicate: bool = False,
    relative_path: str | None = None,
) -> dict:
    item = {
        "file_id": "file_a",
        "relative_path": relative_path or path.name,
        "extension": ".xml",
        "sha256": "same_sha",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "xml_root_tag": "file",
        "xml_namespace_map": {},
        "surface_row_count": 2,
        "visible_column_count": 4,
    }
    files = [item]
    if duplicate:
        files.append(
            item
            | {
                "file_id": "file_b",
                "relative_path": f"copy/{path.name}",
            }
        )
    return {"files": files}


def basic_xml() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
<file>
  <instance id='1'>
    <player>Alpha</player><team>Side A</team><event_type>Pass</event_type><x>10</x>
  </instance>
  <instance id='2'>
    <player>Beta</player><team>Side B</team><event_type>Shot</event_type><x>20</x>
  </instance>
</file>
"""


def test_repeated_instance_rows_are_profiled_candidate_only(tmp_path: Path) -> None:
    path = tmp_path / "players.xml"
    write_xml(path, basic_xml())
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "PASS"
    assert payload["xml_file_count"] == 1
    audit = payload["files"][0]
    assert audit["selected_row_tag_candidate"] == "instance"
    assert audit["row_candidate_count"] == 2
    assert audit["field_path_count"] == 5
    assert audit["identity_binding"]["player"]["binding_status"] == "CANDIDATE_ONLY"
    assert audit["identity_binding"]["player"]["validated_identity"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_namespaces_and_local_names_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "namespaced.xml"
    write_xml(
        path,
        """<ns:file xmlns:ns='urn:test'>
        <ns:event ns:id='1'><ns:type>Pass</ns:type></ns:event>
        <ns:event ns:id='2'><ns:type>Carry</ns:type></ns:event>
        </ns:file>""",
    )
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    audit = payload["files"][0]
    assert audit["status"] == "PASS"
    assert audit["xml_structure"]["root_tag"] == "file"
    assert audit["xml_structure"]["namespace_map"] == {"ns": "urn:test"}
    assert audit["selected_row_tag_candidate"] == "event"
    assert audit["row_candidate_count"] == 2


def test_nested_duplicate_field_paths_preserve_values(tmp_path: Path) -> None:
    path = tmp_path / "nested.xml"
    write_xml(
        path,
        """<file><event><tags><label>A</label><label>B</label></tags></event>
        <event><tags><label>C</label></tags></event></file>""",
    )
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    example = payload["files"][0]["example_rows"][0]
    assert example["event.tags.label"] == ["A", "B"]


def test_duplicate_inventory_reflection_is_consumed_once(tmp_path: Path) -> None:
    path = tmp_path / "players.xml"
    write_xml(path, basic_xml())
    copy_dir = tmp_path / "copy"
    copy_dir.mkdir()
    (copy_dir / path.name).write_bytes(path.read_bytes())
    payload = MODULE.build_xml_surface_audit(
        tmp_path,
        inventory_for(path, duplicate=True),
    )
    assert payload["xml_file_count"] == 1


def test_dtd_and_entity_are_blocked_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.xml"
    declaration = "<!" + "DOCTYPE file [<!" + "ENTITY xxe SYSTEM 'blocked'>]>"
    write_xml(
        path,
        declaration + "<file><event>&xxe;</event><event>safe</event></file>",
    )
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "FAIL_CLOSED"
    assert "external_entity_resolution_attempted" in payload["hard_block_hits"]


def test_utf16_dtd_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "unsafe_utf16.xml"
    declaration = "<!" + "DOCTYPE file [<!" + "ENTITY x 'bad'>]>"
    write_xml(
        path,
        "<?xml version='1.0' encoding='UTF-16'?>"
        + declaration
        + "<file><event>&x;</event><event>safe</event></file>",
        encoding="utf-16",
    )
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "FAIL_CLOSED"
    assert "external_entity_resolution_attempted" in payload["hard_block_hits"]


def test_malformed_xml_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "broken.xml"
    write_xml(path, "<file><event></file>")
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "FAIL_CLOSED"
    assert "malformed_xml" in payload["hard_block_hits"]


def test_inventory_path_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.xml"
    write_xml(outside, basic_xml())
    payload = MODULE.build_xml_surface_audit(
        tmp_path,
        inventory_for(outside, relative_path="../outside.xml"),
    )
    assert payload["status"] == "FAIL_CLOSED"
    assert "inventory_relative_path_outside_input_root" in payload["hard_block_hits"]


def test_unresolved_row_container_requires_review(tmp_path: Path) -> None:
    path = tmp_path / "scalar.xml"
    write_xml(path, "<file><title>A</title><description>B</description></file>")
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "REVIEW_REQUIRED"
    assert "xml_row_container_candidate_unresolved" in payload["files"][0]["parse_warnings"]


def test_element_budget_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import xml_structure

    path = tmp_path / "players.xml"
    write_xml(path, basic_xml())
    monkeypatch.setattr(xml_structure, "MAX_XML_ELEMENTS", 3)
    payload = MODULE.build_xml_surface_audit(tmp_path, inventory_for(path))
    assert payload["status"] == "FAIL_CLOSED"
    assert "xml_element_budget_exceeded" in payload["hard_block_hits"]


def test_nested_phone_output_directory_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        MODULE.validate_out("/sdcard/Download/HPFA/xml-run")


def test_write_outputs_and_active_match_evidence(tmp_path: Path) -> None:
    active = tmp_path / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)
    path = active / "players.xml"
    write_xml(path, basic_xml())
    inventory = active / "inventory.json"
    inventory.write_text(json.dumps(inventory_for(path)), encoding="utf-8")
    out = tmp_path / "out"
    payload = MODULE.write_outputs(active, inventory, out)
    assert payload["status"] == "PASS"
    assert payload["active_match_evidence_pass"] is True
    assert (out / "xml_surface_audit_lite_v1.json").is_file()
    assert (out / "xml_surface_audit_lite_v1.txt").is_file()
    assert (out / "xml_surface_analyst_audit_lite_v1.txt").is_file()


def test_malformed_inventory_fails_closed_and_writes_outputs(tmp_path: Path) -> None:
    active = tmp_path / "runtime" / "active_single_match" / "current"
    active.mkdir(parents=True)
    inventory = active / "inventory.json"
    inventory.write_text("{not-json", encoding="utf-8")
    out = tmp_path / "out"
    payload = MODULE.write_outputs(active, inventory, out)
    assert payload["status"] == "FAIL_CLOSED"
    assert payload["active_match_evidence_pass"] is False
    assert "inventory_json_malformed" in payload["hard_block_hits"]
    assert (out / "xml_surface_audit_lite_v1.json").is_file()


def test_no_sample_match_identity_leak() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SRC.glob("*.py")
    ).casefold()
    forbidden = [
        "australia",
        "turkey",
        "galatasaray",
        "fenerbahce",
        "13.06.2026",
        "surface_row_count=1355",
        "surface_row_count=24301",
        "surface_row_count=24418",
    ]
    assert not any(token in text for token in forbidden)
