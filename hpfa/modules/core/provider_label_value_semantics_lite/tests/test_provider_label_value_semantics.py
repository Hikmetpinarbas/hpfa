from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "src"
REGISTRY = ROOT / "hpfa" / "modules" / "core" / "provider_label_value_semantics_lite" / "registry" / "sportsbase_label_semantics_seed_v1.json"
sys.path.insert(0, str(SRC))

from provider_label_value_semantics import (
    build_semantics,
    classify_label,
    load_registry,
    normalize_label,
    write_outputs,
)


def csv_payload(status: str = "PASS") -> dict:
    return {
        "module_id": "csv_surface_reader_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "production_release": False,
        "files": [
            {
                "relative_path": "raw/Players.csv",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "sha256": "a" * 64,
                "action_taxonomy": [
                    {"raw_type": "Passes accurate", "raw_subtype": "", "surface_row_volume": 10},
                    {"raw_type": "Passes forward accurate", "raw_subtype": "", "surface_row_volume": 4},
                    {"raw_type": "Playing in positional attacks", "raw_subtype": "", "surface_row_volume": 3},
                    {"raw_type": "Vendor mystery", "raw_subtype": "", "surface_row_volume": 2},
                ],
            }
        ],
    }


def xml_payload() -> dict:
    return {
        "module_id": "xml_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "production_release": False,
        "files": [
            {
                "relative_path": "raw/Players.xml",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "sha256": "b" * 64,
                "example_rows": [
                    {
                        "instance.label.group": ["Action", "Team", "Half"],
                        "instance.label.text": ["Passes accurate", "TEAM_A", "1"],
                    }
                ],
            }
        ],
    }


def xlsx_payload() -> dict:
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "production_release": False,
        "files": [
            {
                "relative_path": "raw/Players.xlsx",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "sha256": "c" * 64,
                "sheets": [
                    {
                        "source_role": "PLAYER_SURFACE_CANDIDATE",
                        "column_profiles": [
                            {"raw_column": "Player"},
                            {"raw_column": "Passes accurate, %"},
                        ],
                    }
                ],
            }
        ],
    }


def field_semantics_payload() -> dict:
    return {
        "module_id": "provider_alias_field_semantics_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "production_release": False,
        "required_anchor_audit": {
            "csv": {"ready_for_candidate_reconciliation": True},
            "xml": {"ready_for_candidate_reconciliation": True},
        },
    }


def registry() -> dict:
    return load_registry(REGISTRY)


def test_normalization_is_stable() -> None:
    assert normalize_label("  Passes accurate, % ") == "passes accurate percent"


def test_exact_pass_mapping_and_qualifiers() -> None:
    result = classify_label("Passes forward accurate", source_format="csv", registry=registry())
    assert result["semantic_role_candidate"] == "ACTION_ANCHOR"
    assert result["action_family_candidate"] == "PASS"
    assert result["outcome_candidate"] == "SUCCESS"
    assert result["direction_candidate"] == "FORWARD"


def test_context_and_participation_are_not_action_volume() -> None:
    context = classify_label("Playing in positional attacks", source_format="csv", registry=registry())
    participation = classify_label("Involvement in positional attacks", source_format="csv", registry=registry())
    assert context["semantic_role_candidate"] == "CONTEXT_INTERVAL"
    assert participation["semantic_role_candidate"] == "PARTICIPATION_INTERVAL"


def test_meta_is_excluded_from_action_family() -> None:
    result = classify_label("Start of first half", source_format="xml", registry=registry())
    assert result["semantic_role_candidate"] == "PERIOD_OR_META"
    assert result["action_family_candidate"] is None


def test_unknown_is_preserved_not_guessed() -> None:
    result = classify_label("Vendor mystery", source_format="csv", registry=registry())
    assert result["mapping_status"] == "UNKNOWN_PRESERVED"
    assert result["action_family_candidate"] == "UNKNOWN"


def test_xlsx_label_never_creates_event_action() -> None:
    result = classify_label("Passes accurate, %", source_format="xlsx", registry=registry())
    assert result["semantic_role_candidate"] == "AGGREGATE_METRIC_LABEL"
    assert result["action_family_candidate"] is None


def test_surface_volume_coverage_and_xml_support() -> None:
    result = build_semantics(
        csv_payload(),
        xlsx_payload(),
        xml_payload(),
        field_semantics_payload(),
        registry(),
    )
    assert result["coverage"]["csv_surface_row_volume"] == 19
    assert result["coverage"]["unknown_surface_row_volume"] == 2
    assert result["coverage"]["mapped_surface_row_volume"] == 17
    assert result["cross_format_consistency"]["comparable_label_count"] == 1
    assert result["cross_format_consistency"]["conflict_count"] == 0
    assert result["status"] == "REVIEW_REQUIRED"


def test_upstream_fail_closed_blocks() -> None:
    result = build_semantics(
        csv_payload("FAIL_CLOSED"),
        xlsx_payload(),
        xml_payload(),
        field_semantics_payload(),
        registry(),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("upstream_fail_closed") for value in result["hard_block_hits"])


def test_missing_field_semantics_blocks() -> None:
    payload = field_semantics_payload()
    payload["required_anchor_audit"]["xml"]["ready_for_candidate_reconciliation"] = False
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload(), payload, registry())
    assert result["status"] == "FAIL_CLOSED"
    assert "required_field_path_semantics_missing:xml" in result["hard_block_hits"]


def test_canonical_count_claim_blocks() -> None:
    payload = csv_payload()
    payload["canonical_event_count"] = 19
    result = build_semantics(payload, xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("canonical_event_count_claimed") for value in result["hard_block_hits"])


def test_registry_duplicate_conflict(tmp_path: Path) -> None:
    payload = registry()
    payload["exact_rules"].append(dict(payload["exact_rules"][0]))
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="registry_duplicate_conflict"):
        load_registry(path)


def test_exact_runtime_authority_equality_and_outputs(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime" / "active_single_match" / "current"
    runtime.mkdir(parents=True)
    clean_csv = csv_payload()
    clean_csv["files"][0]["action_taxonomy"] = clean_csv["files"][0]["action_taxonomy"][:-1]
    inputs = []
    for name, payload in (
        ("csv.json", clean_csv),
        ("xlsx.json", xlsx_payload()),
        ("xml.json", xml_payload()),
        ("fields.json", field_semantics_payload()),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        inputs.append(path)
    result = write_outputs(runtime, runtime, *inputs, REGISTRY, tmp_path / "HPFA")
    assert result["status"] == "PASS"
    assert result["active_match_evidence_pass"] is True
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_runtime_authority_suffix_is_not_enough(tmp_path: Path) -> None:
    runtime = tmp_path / "quarantine" / "runtime" / "active_single_match" / "current"
    expected = tmp_path / "runtime" / "active_single_match" / "current"
    runtime.mkdir(parents=True)
    expected.mkdir(parents=True)
    inputs = []
    for name, payload in (
        ("csv.json", csv_payload()),
        ("xlsx.json", xlsx_payload()),
        ("xml.json", xml_payload()),
        ("fields.json", field_semantics_payload()),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        inputs.append(path)
    result = write_outputs(runtime, expected, *inputs, REGISTRY, tmp_path / "HPFA")
    assert result["status"] == "FAIL_CLOSED"
    assert "runtime_authority_mismatch" in result["hard_block_hits"]
    assert result["active_match_evidence_pass"] is False


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime" / "active_single_match" / "current"
    runtime.mkdir(parents=True)
    inputs = []
    for name, payload in (
        ("csv.json", csv_payload()),
        ("xlsx.json", xlsx_payload()),
        ("xml.json", xml_payload()),
        ("fields.json", field_semantics_payload()),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        inputs.append(path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(runtime, runtime, *inputs, REGISTRY, tmp_path / "HPFA" / "nested")


def test_minimal_donor_scope_and_no_parallel_framework() -> None:
    source = (SRC / "provider_label_value_semantics.py").read_text(encoding="utf-8")
    forbidden = ["from hp_motor", "from hp_engine", "langchain", "openai", "pandas", "numpy"]
    assert not any(token in source.casefold() for token in forbidden)


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "provider_label_value_semantics.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source for token in forbidden)
