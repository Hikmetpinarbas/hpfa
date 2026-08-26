import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_field_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_time_semantic_admission import (
    ABSOLUTE_SECONDS,
    ADMITTED,
    REVIEW_REQUIRED,
    build_minimum_context_report,
    build_time_admission,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ID",
                "start",
                "end",
                "team",
                "action",
                "half",
                "pos_x",
                "pos_y",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_xml(path: Path, rows: list[dict[str, str]]) -> None:
    root = ET.Element("file")
    all_instances = ET.SubElement(root, "ALL_INSTANCES")
    for row in rows:
        instance = ET.SubElement(all_instances, "instance")
        ET.SubElement(instance, "ID").text = row["ID"]
        ET.SubElement(instance, "start").text = row["start"]
        ET.SubElement(instance, "end").text = row["end"]
        ET.SubElement(instance, "code").text = row["action"]
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _absolute_rows() -> list[dict[str, str]]:
    return [
        {
            "ID": "1",
            "start": "10.0",
            "end": "12.0",
            "team": "A",
            "action": "pass",
            "half": "1",
            "pos_x": "20",
            "pos_y": "30",
        },
        {
            "ID": "2",
            "start": "2700.0",
            "end": "2702.0",
            "team": "A",
            "action": "shot",
            "half": "1",
            "pos_x": "80",
            "pos_y": "30",
        },
        {
            "ID": "3",
            "start": "2760.0",
            "end": "2761.0",
            "team": "B",
            "action": "pass",
            "half": "2",
            "pos_x": "40",
            "pos_y": "30",
        },
        {
            "ID": "4",
            "start": "5400.0",
            "end": "5401.0",
            "team": "B",
            "action": "shot",
            "half": "2",
            "pos_x": "85",
            "pos_y": "30",
        },
    ]


def _row_nucleus_payload(rows: list[dict[str, str]]) -> dict:
    nuclei = []
    for index, row in enumerate(rows):
        nuclei.append(
            {
                "row_nucleus_candidate_id": f"rn_{index + 1}",
                "status": "PASS",
                "source_role": "PLAYER",
                "serialization_relation_candidate": "REFLECTION_CANDIDATE_EXACT",
                "lineage_admission_status": "CANDIDATE_EXACT_VISIBLE_FIELDS",
                "lineage_review_reasons": [],
                "review_reasons": [],
                "source_refs": [
                    {
                        "source_file": "surface.csv",
                        "source_format": "csv",
                        "source_role": "PLAYER",
                        "source_row_index": index,
                    },
                    {
                        "source_file": "surface.xml",
                        "source_format": "xml",
                        "source_role": "PLAYER",
                        "source_row_index": index,
                    },
                ],
                "resolved_visible_fields": {
                    "start": row["start"],
                    "end": row["end"],
                    "code": row["action"],
                    "team": row["team"],
                    "action": row["action"],
                    "half": row["half"],
                    "pos_x": row["pos_x"],
                    "pos_y": row["pos_y"],
                },
            }
        )
    return {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "PASS",
        "content_source_role_bridge_status": "PASS",
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_review_required_count": 0,
        "row_nuclei": nuclei,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_admits_cross_format_absolute_match_seconds_from_reviewed_contract(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == ADMITTED
    assert result["unit_candidate"] == "SECOND"
    assert result["unit_authority_basis"] == "CURRENT_PROVIDER_TIME_CONTRACT"
    assert result["time_basis_candidate"] == ABSOLUTE_SECONDS
    assert result["runtime_checks"]["provider_time_contract_authority_admitted"] is True
    assert result["runtime_checks"]["generic_numeric_time_unit_inference_allowed"] is False
    assert result["runtime_checks"]["absolute_continuation_across_halves"] is True
    assert result["source_row_order_is_temporal_truth"] is False


def test_rejects_half_local_reset(tmp_path: Path) -> None:
    rows = _absolute_rows()
    rows[2]["start"] = "20.0"
    rows[2]["end"] = "21.0"
    rows[3]["start"] = "2600.0"
    rows[3]["end"] = "2601.0"
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == REVIEW_REQUIRED
    assert "absolute_match_time_basis_not_demonstrated" in result["review_reasons"]


def test_rejects_cross_format_time_mismatch(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    xml_rows = [dict(row) for row in rows]
    xml_rows[-1]["start"] = "5410.0"
    _write_xml(tmp_path / "surface.xml", xml_rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == REVIEW_REQUIRED
    assert "csv_xml_start_surface_mismatch" in result["review_reasons"]


def test_rejects_malformed_temporal_rows_instead_of_skipping_them(tmp_path: Path) -> None:
    rows = _absolute_rows()
    malformed = dict(rows[0])
    malformed["ID"] = "bad"
    malformed["start"] = ""
    malformed["end"] = ""
    rows.append(malformed)
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    result = build_time_admission(tmp_path)
    assert result["status"] == REVIEW_REQUIRED
    assert "start_end_pair_invalid" in result["review_reasons"]
    assert result["runtime_checks"]["malformed_temporal_row_count"] == 2
    assert result["runtime_checks"]["csv_pair_audit"]["invalid_pair_count"] == 1
    assert result["runtime_checks"]["xml_pair_audit"]["invalid_pair_count"] == 1


def test_primary_csv_surface_prevents_csv_xml_context_multiplication_without_nucleus(
    tmp_path: Path,
) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    report = build_minimum_context_report(tmp_path, ROOT)
    assert report["time_admission_status"] == "ADMITTED"
    assert report["context_candidate_count"] == 4
    assert report["context_summary"]["time_unit_status_counts"] == {"SECOND": 4}
    assert report["context_input_scope"] == "provider_time_admitted_primary_csv_surface"
    assert report["context_occurrence_basis"] == "PRIMARY_CSV_SERIALIZATION_CANDIDATE_NOT_EVENT_COUNT"
    assert report["reflection_inflation_prevented"] is True
    assert report["serialization_context_binding"]["selected_context_surface"] == "CSV_PRIMARY"
    assert report["serialization_context_binding"]["xml_conformance_adds_context_candidate"] is False
    assert report["serialization_context_binding"]["csv_xml_conformance_is_independent_corroboration"] is False
    assert report["source_row_order_is_temporal_truth"] is False
    assert report["sequence_truth"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_row_nucleus_binding_prevents_csv_xml_context_multiplication(
    tmp_path: Path,
) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    nucleus_path = tmp_path / "row_nucleus_inventory_lite_v1.json"
    nucleus_path.write_text(
        json.dumps(_row_nucleus_payload(rows), ensure_ascii=False),
        encoding="utf-8",
    )

    report = build_minimum_context_report(
        tmp_path,
        ROOT,
        row_nucleus_path=nucleus_path,
    )

    assert report["time_admission_status"] == "ADMITTED"
    assert report["context_candidate_count"] == 4
    assert report["context_summary"]["time_unit_status_counts"] == {"SECOND": 4}
    assert report["context_input_scope"] == "provider_time_admitted_row_nucleus_surface"
    assert report["context_occurrence_basis"] == "ROW_NUCLEUS_CANDIDATE_NOT_EVENT_COUNT"
    assert report["reflection_inflation_prevented"] is True
    assert report["serialization_context_binding"]["selected_context_surface"] == "ROW_NUCLEUS"
    assert report["row_nucleus_context_binding"]["row_nucleus_candidate_count"] == 4
    assert (
        report["row_nucleus_context_binding"][
            "dependent_reflection_adds_context_candidate"
        ]
        is False
    )
    preserved = report["context_candidates"][0]["_preserved_unmapped"]
    assert preserved["row_nucleus_candidate_id"] == "rn_1"
    assert preserved["independent_source_vote_allowed"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_missing_row_nucleus_resolved_fields_fails_closed(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    nucleus_path = tmp_path / "row_nucleus_inventory_lite_v1.json"
    payload = _row_nucleus_payload(rows)
    payload["row_nuclei"][0].pop("resolved_visible_fields")
    nucleus_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row_nucleus_resolved_fields_invalid:0"):
        build_minimum_context_report(tmp_path, ROOT, row_nucleus_path=nucleus_path)


def test_empty_row_nucleus_resolved_fields_fails_closed(tmp_path: Path) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    nucleus_path = tmp_path / "row_nucleus_inventory_lite_v1.json"
    payload = _row_nucleus_payload(rows)
    payload["row_nuclei"][0]["resolved_visible_fields"] = {}
    nucleus_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row_nucleus_resolved_fields_invalid:0"):
        build_minimum_context_report(tmp_path, ROOT, row_nucleus_path=nucleus_path)


def test_row_nucleus_scope_is_not_labeled_admitted_when_time_is_review_required(
    tmp_path: Path,
) -> None:
    rows = _absolute_rows()
    rows[2]["start"] = "20.0"
    rows[2]["end"] = "21.0"
    rows[3]["start"] = "2600.0"
    rows[3]["end"] = "2601.0"
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    nucleus_path = tmp_path / "row_nucleus_inventory_lite_v1.json"
    nucleus_path.write_text(json.dumps(_row_nucleus_payload(rows)), encoding="utf-8")
    report = build_minimum_context_report(tmp_path, ROOT, row_nucleus_path=nucleus_path)
    assert report["provider_time_semantic_admission"]["status"] == REVIEW_REQUIRED
    assert report["time_admission_status"] == REVIEW_REQUIRED
    assert report["context_input_scope"] == "provider_time_review_required_row_nucleus_surface"
    assert report["reflection_inflation_prevented"] is True


def test_explicit_invalid_row_nucleus_binding_fails_closed_without_raw_fallback(
    tmp_path: Path,
) -> None:
    rows = _absolute_rows()
    _write_csv(tmp_path / "surface.csv", rows)
    _write_xml(tmp_path / "surface.xml", rows)
    nucleus_path = tmp_path / "row_nucleus_inventory_lite_v1.json"
    payload = _row_nucleus_payload(rows)
    payload["module_id"] = "wrong_module"
    nucleus_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="row_nucleus_binding_module_mismatch"):
        build_minimum_context_report(
            tmp_path,
            ROOT,
            row_nucleus_path=nucleus_path,
        )


def test_no_sample_match_identity_leak() -> None:
    src = (SRC / "provider_time_semantic_admission.py").read_text(encoding="utf-8")
    for token in [
        "Turkey",
        "Australia",
        "World Cup",
        "Fenerbahce",
        "Galatasaray",
        "25.06.2026",
    ]:
        assert token not in src
