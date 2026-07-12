import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "triplex_source_alignment_adapter_lite" / "src"
sys.path.insert(0, str(SRC))

from triplex_source_alignment_adapter import build_alignment, write_outputs


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def valid_source(name: str, origin: str, group: str) -> dict:
    return {
        "source_file": name,
        "source_role": "teams",
        "source_format": name.rsplit(".", 1)[-1],
        "source_surface_kind": "event_like_or_review",
        "upstream_origin_id": origin,
        "independence_group": group,
        "lineage_role": "PRIMARY_SOURCE",
        "canonical_event_identity_compatible": True,
        "time_window_state": "ALIGNED",
        "unit_compatibility": "COMPATIBLE",
        "scope_compatibility": "COMPATIBLE",
        "denominator_compatibility": "COMPATIBLE",
    }


def test_missing_lineage_fields_require_review(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [{"source_file": "Teams.csv", "source_surface_kind": "event_like_or_review"}]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    payload = build_alignment(tmp_path, root=ROOT)

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["finding_class_counts"]["MISSING_UPSTREAM_ORIGIN_ID"] == 1
    assert payload["finding_class_counts"]["MISSING_INDEPENDENCE_GROUP"] == 1
    assert payload["fusion_admissible"] is False


def test_duplicate_upstream_origin_not_independent(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [
        valid_source("Teams.csv", "provider-export-1", "triplex-a"),
        valid_source("Teams.xml", "provider-export-1", "triplex-a"),
    ]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    payload = build_alignment(tmp_path, root=ROOT)

    assert payload["finding_class_counts"]["DUPLICATE_UPSTREAM_ORIGIN"] == 1
    assert payload["finding_class_counts"]["DEPENDENT_SOURCE_GROUP"] == 1
    assert payload["fusion_admissible"] is False


def test_derived_output_as_source_fails_closed(tmp_path):
    source = valid_source("derived.json", "derived-1", "triplex-a")
    source["lineage_role"] = "DERIVED_OUTPUT"
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [source]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    payload = build_alignment(tmp_path, root=ROOT)

    assert payload["status"] == "FAIL_CLOSED"
    assert payload["finding_class_counts"]["DERIVED_OUTPUT_AS_SOURCE"] == 1


def test_compatible_independent_sources_pass_alignment_only(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [
        valid_source("Teams.csv", "provider-export-1", "triplex-a"),
        valid_source("Teams.xml", "independent-export-2", "triplex-b"),
    ]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    payload = build_alignment(tmp_path, root=ROOT)

    assert payload["status"] == "PASS"
    assert payload["fusion_admissible"] is True
    assert payload["claim_capacity"] == "SOURCE_ALIGNMENT_ONLY"
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["production_binding_allowed"] is False


def test_existing_registry_conflicts_block_fusion(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [valid_source("Teams.csv", "provider-export-1", "triplex-a")]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 2})

    payload = build_alignment(tmp_path, root=ROOT)

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["inherited_conflict_count"] == 2
    assert payload["fusion_admissible"] is False


def test_flat_phone_outputs(tmp_path):
    input_dir = tmp_path / "input"
    out = tmp_path / "HPFA"
    input_dir.mkdir()
    out.mkdir()
    write_json(input_dir / "source_mapping_contract_v1.json", {"sources": [valid_source("Teams.csv", "provider-export-1", "triplex-a")]})
    write_json(input_dir / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    payload = write_outputs(input_dir, out, root=ROOT)

    assert payload["status"] == "PASS"
    assert (out / "triplex_source_alignment_adapter_lite_v1.json").exists()
    assert (out / "triplex_source_alignment_adapter_lite_v1.txt").exists()
    assert not any(path.is_dir() for path in out.iterdir())


def test_nested_phone_output_directory_rejected(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [valid_source("Teams.csv", "provider-export-1", "triplex-a")]})
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflict_count": 0})

    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path, "/sdcard/Download/HPFA/triplex", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "triplex_source_alignment_adapter.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "triplex_source_alignment_adapter_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "Galatasaray", "World Cup", "13.06.2026", "25.02.2026"]:
        assert token not in src
        assert token not in contract
