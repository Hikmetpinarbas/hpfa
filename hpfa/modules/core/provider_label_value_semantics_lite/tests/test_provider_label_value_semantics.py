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

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


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
                "sha256": SHA_A,
                "action_taxonomy": [
                    {"raw_type": "Passes accurate", "raw_subtype": "", "surface_row_volume": 10},
                    {"raw_type": "Passes forward accurate", "raw_subtype": "", "surface_row_volume": 4},
                    {"raw_type": "Involvement in positional attacks", "raw_subtype": "", "surface_row_volume": 3},
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
                "sha256": SHA_B,
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
                "sha256": SHA_C,
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


def classify(label: str, role: str = "PLAYER_SURFACE_CANDIDATE") -> dict:
    return classify_label(label, source_format="csv", source_role=role, registry=registry())


def test_normalization_is_stable() -> None:
    assert normalize_label("  Passes accurate, % ") == "passes accurate percent"


def test_exact_pass_mapping_and_qualifiers() -> None:
    result = classify("Passes forward accurate")
    assert result["mapping_status"] == "EXACT_REVIEWED_CANDIDATE"
    assert result["semantic_role_candidate"] == "ACTION_ANCHOR"
    assert result["action_family_candidate"] == "PASS"
    assert result["outcome_candidate"] == "SUCCESS"
    assert result["direction_candidate"] == "FORWARD"


def test_incomplete_pass_is_failure_not_unqualified_pass() -> None:
    result = classify("Incomplete progressive passes")
    assert result["action_family_candidate"] == "PASS"
    assert result["outcome_candidate"] == "FAILURE"
    assert result["progression_candidate"] == "PROGRESSIVE_CANDIDATE"


def test_context_and_participation_are_not_action_volume() -> None:
    context = classify("Positional attacks with shots", "TEAM_SURFACE_CANDIDATE")
    participation = classify("Involvement in positional attacks with shots")
    assert context["semantic_role_candidate"] == "CONTEXT_INTERVAL"
    assert participation["semantic_role_candidate"] == "PARTICIPATION_INTERVAL"
    assert context["action_family_candidate"] is None
    assert participation["action_family_candidate"] is None
    assert context["terminal_outcome_candidate"] == "SHOT_PRESENT_CANDIDATE"


def test_meta_variants_are_excluded_from_action_family() -> None:
    for label in ("Start of the 1st half", "Start of the 2nd half", "Halftime", "End of the match"):
        result = classify(label)
        assert result["semantic_role_candidate"] == "PERIOD_OR_META"
        assert result["action_family_candidate"] is None


def test_goal_kicks_are_restart_anchors_with_distance() -> None:
    result = classify("Goal kicks long (40+ m)", "TEAM_SURFACE_CANDIDATE")
    assert result["action_family_candidate"] == "RESTART"
    assert result["restart_type_candidate"] == "GOAL_KICK"
    assert result["distance_candidate"] == "LONG"


def test_opponent_shot_is_reference_not_own_action() -> None:
    result = classify("Opponent's long-range shots on target", "GOALKEEPER_SURFACE_CANDIDATE")
    assert result["semantic_role_candidate"] == "OPPONENT_ACTION_REFERENCE"
    assert result["action_family_candidate"] == "SHOT"
    assert result["relation_candidate"] == "FACED_BY_GOALKEEPER"
    assert result["shot_result_candidate"] == "ON_TARGET"


def test_shot_label_is_source_role_specific() -> None:
    goalkeeper = classify("Shots on target", "GOALKEEPER_SURFACE_CANDIDATE")
    team = classify("Shots on target", "TEAM_SURFACE_CANDIDATE")
    assert goalkeeper["semantic_role_candidate"] == "OPPONENT_ACTION_REFERENCE"
    assert team["semantic_role_candidate"] == "ACTION_ANCHOR"


def test_shots_saved_is_goalkeeper_save_action() -> None:
    result = classify("Shots saved", "GOALKEEPER_SURFACE_CANDIDATE")
    assert result["action_family_candidate"] == "GOALKEEPER_ACTION"
    assert result["action_subtype_candidate"] == "SAVE"
    assert result["object_action_family_candidate"] == "SHOT"
    assert result["shot_result_candidate"] == "SAVED"


def test_compound_interception_is_not_misclassified_as_pass() -> None:
    result = classify("Successful cross and pass interception attempts", "GOALKEEPER_SURFACE_CANDIDATE")
    assert result["action_family_candidate"] == "INTERCEPTION"
    assert result["outcome_candidate"] == "SUCCESS"
    assert result["object_action_family_candidate"] == "PASS_OR_CROSS"


def test_foul_relation_direction_is_preserved() -> None:
    suffered = classify("Fouls suffered")
    opponent = classify("Opponent fouls", "TEAM_SURFACE_CANDIDATE")
    own = classify("Fouls")
    assert suffered["semantic_role_candidate"] == "RECEIVED_ACTION_REFERENCE"
    assert opponent["semantic_role_candidate"] == "OPPONENT_ACTION_REFERENCE"
    assert own["semantic_role_candidate"] == "ACTION_ANCHOR"


def test_xlsx_label_never_creates_event_action() -> None:
    result = classify_label("Passes accurate, %", source_format="xlsx", source_role="PLAYER_SURFACE_CANDIDATE", registry=registry())
    assert result["semantic_role_candidate"] == "AGGREGATE_METRIC_LABEL"
    assert result["action_family_candidate"] is None
    assert result["downstream_eligibility"] == "AGGREGATE_ONLY"


def test_unknown_is_preserved_and_token_fallback_never_auto_accepted() -> None:
    unknown = classify("Vendor mystery")
    fallback = classify("Novel passes successful")
    assert unknown["mapping_status"] == "UNKNOWN_UNREVIEWED"
    assert unknown["action_family_candidate"] == "UNKNOWN"
    assert fallback["mapping_status"] == "TOKEN_FALLBACK_REVIEW_REQUIRED"
    assert fallback["downstream_eligibility"] == "BLOCKED_PENDING_REVIEW"


def test_multiple_anchor_tokens_create_conflict() -> None:
    result = classify("Shot pass interception")
    assert result["mapping_status"] == "CONFLICT_REVIEW_REQUIRED"
    assert result["action_family_candidate"] == "UNKNOWN"


def test_surface_volume_coverage_and_xml_support() -> None:
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["coverage"]["csv_surface_row_volume"] == 17
    assert result["coverage"]["reviewed_semantic_surface_row_volume"] == 17
    assert result["coverage"]["review_required_surface_row_volume"] == 0
    assert result["coverage"]["action_anchor_candidate_surface_row_volume"] == 14
    assert result["coverage"]["context_or_participation_surface_row_volume"] == 3
    assert result["cross_format_consistency"]["comparable_label_count"] == 1
    assert result["cross_format_consistency"]["conflict_count"] == 0
    assert result["status"] == "PASS"


def test_token_fallback_forces_review_required() -> None:
    payload = csv_payload()
    payload["files"][0]["action_taxonomy"].append(
        {"raw_type": "Novel passes successful", "raw_subtype": "", "surface_row_volume": 2}
    )
    result = build_semantics(payload, xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["coverage"]["token_fallback_review_surface_row_volume"] == 2
    assert "token_fallback_semantics_review_required" in result["review_hits"]


def test_upstream_fail_closed_blocks() -> None:
    result = build_semantics(csv_payload("FAIL_CLOSED"), xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("upstream_fail_closed") for value in result["hard_block_hits"])


def test_missing_field_semantics_blocks() -> None:
    payload = field_semantics_payload()
    payload["required_anchor_audit"]["xml"]["ready_for_candidate_reconciliation"] = False
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload(), payload, registry())
    assert result["status"] == "FAIL_CLOSED"
    assert "required_field_path_semantics_missing:xml" in result["hard_block_hits"]


def test_source_hash_reference_guard_blocks_missing_sha() -> None:
    payload = csv_payload()
    payload["files"][0]["sha256"] = None
    result = build_semantics(payload, xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("source_hash_missing_or_invalid") for value in result["hard_block_hits"])


def test_duplicate_reflection_is_not_recounted() -> None:
    payload = csv_payload()
    reflected = json.loads(json.dumps(payload["files"][0]))
    reflected["relative_path"] = "mirror/Players.csv"
    payload["files"].append(reflected)
    result = build_semantics(payload, xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["coverage"]["csv_surface_row_volume"] == 17


def test_canonical_count_claim_blocks() -> None:
    payload = csv_payload()
    payload["canonical_event_count"] = 17
    result = build_semantics(payload, xlsx_payload(), xml_payload(), field_semantics_payload(), registry())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("canonical_event_count_claimed") for value in result["hard_block_hits"])


def test_registry_overlapping_role_conflict(tmp_path: Path) -> None:
    payload = registry()
    payload.pop("exact_rules_file", None)
    duplicate = dict(payload["exact_rules"][0])
    duplicate["rule_id"] = "duplicate"
    duplicate["source_roles"] = ["PLAYER_SURFACE_CANDIDATE"]
    payload["exact_rules"].append(duplicate)
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="registry_duplicate_conflict"):
        load_registry(path)


def test_exact_runtime_authority_equality_and_outputs(tmp_path: Path) -> None:
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
    result = write_outputs(runtime, runtime, *inputs, REGISTRY, tmp_path / "out")
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
    result = write_outputs(runtime, expected, *inputs, REGISTRY, tmp_path / "out")
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
    source = (SRC / "provider_label_value_semantics.py").read_text(encoding="utf-8").casefold()
    forbidden = ["from hp_motor", "from hp_engine", "langchain", "openai", "pandas", "numpy"]
    assert not any(token in source for token in forbidden)


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "provider_label_value_semantics.py").read_text(encoding="utf-8")
    registry_text = REGISTRY.read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source or token in registry_text for token in forbidden)
