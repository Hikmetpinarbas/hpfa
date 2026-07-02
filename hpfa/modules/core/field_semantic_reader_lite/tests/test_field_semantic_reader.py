import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "field_semantic_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from field_semantic_reader import build_surface, infer_type, normalize_column


def test_every_visible_column_gets_semantic_status():
    rows = [{"Team Name": "A", "Minute": "12", "x": "42.5"}]
    surface = build_surface(rows)

    records = surface["field_semantic_records"]
    assert len(records) == 3
    assert all(record["semantic_family"] == "unknown" for record in records)
    assert all(record["mapping_status"] == "UNKNOWN" for record in records)


def test_unmapped_columns_are_preserved():
    rows = [{"unknown_vendor_col": "abc"}]
    surface = build_surface(rows)

    assert surface["unmapped_field_candidates"]
    assert surface["unmapped_field_candidates"][0]["source_column"] == "unknown_vendor_col"


def test_mapping_coverage_counts_mapped_and_unmapped():
    rows = [{"a": 1, "b": 2}]
    surface = build_surface(rows)

    coverage = surface["mapping_coverage"]
    assert coverage["mapped_fields"] == 0
    assert coverage["unmapped_fields"] == 2
    assert coverage["coverage_ratio"] == 0.0


def test_no_canonical_event_count_claim():
    rows = [{"event": "pass"}]
    surface = build_surface(rows)

    assert surface["surface_inventory"]["canonical_event_count"] == "UNKNOWN"


def test_infer_type_number_bool_string_unknown():
    assert infer_type(["1", "2.5"]) == "number"
    assert infer_type(["true", "false"]) == "bool"
    assert infer_type(["pass", "shot"]) == "string"
    assert infer_type(["", None]) == "unknown"


def test_normalize_column():
    assert normalize_column(" Team Name ") == "team_name"


def test_no_sample_match_identity_leak():
    src = (SRC / "field_semantic_reader.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
