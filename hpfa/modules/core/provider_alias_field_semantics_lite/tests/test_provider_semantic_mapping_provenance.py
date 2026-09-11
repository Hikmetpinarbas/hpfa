from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_field_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_alias_field_semantics import build_semantics
from provider_semantic_mapping_provenance import enrich_mapping_provenance


def _csv() -> dict:
    return {
        "module_id": "csv_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{
            "relative_path": "events.csv",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "column_profiles": [
                {"raw_column": "start", "inferred_type": "number"},
                {"raw_column": "vendor_blob", "inferred_type": "string"},
            ],
        }],
    }


def _xlsx() -> dict:
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{
            "relative_path": "players.xlsx",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "sheets": [{
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "column_profiles": [{
                    "raw_column": "Passes accurate, %",
                    "identity_role_candidate": None,
                    "percent_header_candidate": True,
                    "inferred_type": "number",
                }],
            }],
        }],
    }


def _xml() -> dict:
    return {
        "module_id": "xml_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{
            "relative_path": "events.xml",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "field_inventory": [{"raw_field_path": "instance.start", "row_coverage_ratio": 1.0}],
        }],
    }


def _result() -> dict:
    csv, xlsx, xml = _csv(), _xlsx(), _xml()
    base = build_semantics(csv, xlsx, xml)
    return enrich_mapping_provenance(base, csv_payload=csv, xlsx_payload=xlsx, xml_payload=xml)


def test_exact_field_rule_does_not_validate_definition_equivalence() -> None:
    result = _result()
    row = next(r for r in result["field_semantic_records"] if r["raw_field"] == "start")
    assert row["mapping_type"] == "RENAMED_ONLY"
    assert row["mapping_validation_state"] == "NOT_VALIDATED"
    assert row["semantic_equivalence_state"] == "NOT_VALIDATED"
    assert "field_name_rule_only" in row["introduced_assumptions"]
    assert row["canonicalization_creates_new_observation_truth"] is False


def test_xlsx_generic_metric_mapping_is_explicitly_lossy_many_to_one() -> None:
    result = _result()
    row = next(r for r in result["field_semantic_records"] if r["raw_field"] == "Passes accurate, %")
    assert row["mapping_type"] == "MANY_TO_ONE"
    assert row["mapping_cardinality"] == "MANY_TO_ONE"
    assert row["mapping_loss_state"] == "LOSSY"
    assert "metric_specific_definition" in row["lost_information"]
    assert row["semantic_equivalence_state"] == "NOT_VALIDATED"


def test_unknown_field_remains_unverified_without_truth_creation() -> None:
    result = _result()
    row = next(r for r in result["field_semantic_records"] if r["raw_field"] == "vendor_blob")
    assert row["mapping_type"] == "UNVERIFIED"
    assert row["mapping_loss_state"] == "UNRESOLVED"
    assert row["canonical_key_candidate"] is None
    assert row["mapping_creates_evidence_independence"] is False


def test_unknown_schema_version_is_visible_and_requires_revalidation_on_change() -> None:
    result = _result()
    assert result["provider_semantic_mapping_provenance"]["schema_version_unknown_record_count"] > 0
    for row in result["field_semantic_records"]:
        assert row["provider_schema_version"] == "UNKNOWN"
        assert row["schema_version_binding_state"] == "SCHEMA_VERSION_UNKNOWN"
        assert row["schema_change_requires_revalidation"] is True


def test_candidate_equivalence_group_does_not_become_empirical_equivalence_or_vote_count() -> None:
    result = _result()
    for group in result["candidate_equivalence_groups"]:
        assert group["semantic_equivalence_state"] == "NOT_VALIDATED"
        assert group["member_count_is_independent_evidence_count"] is False
        assert group["canonical_key_match_is_definition_match"] is False
        assert group["cross_format_candidate_is_empirical_equivalence"] is False


def test_contract_keeps_semantic_mapping_fail_safe() -> None:
    contract = json.loads((ROOT / "hpfa/modules/core/provider_alias_field_semantics_lite/contract/provider_alias_field_semantics_lite_v1.json").read_text(encoding="utf-8"))
    mapping = contract["provider_semantic_mapping_provenance"]
    assert mapping["field_name_match_is_definition_match"] is False
    assert mapping["format_normalization_is_semantic_normalization"] is False
    assert mapping["ontology_alignment_is_construct_validity"] is False
    assert mapping["lossy_mapping_is_equivalence"] is False
    assert mapping["canonicalization_creates_evidence_independence"] is False
    assert mapping["schema_change_action"] == "REVALIDATION_REQUIRED"
    assert mapping["semantic_equivalence_default"] == "NOT_VALIDATED"


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "provider_semantic_mapping_provenance.py").read_text(encoding="utf-8")
    forbidden = ("Fenerbahce", "Genclerbirligi", "Galatasaray", "Besiktas", "15.08.2026")
    assert not any(token in text for token in forbidden)
