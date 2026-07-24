from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "cross_format_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from cross_format_reconciliation import build_reconciliation, write_outputs

ROLE = "PLAYER_SURFACE_CANDIDATE"
REGISTRY_PATH = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "cross_format_reconciliation_lite"
    / "registry"
    / "sportsbase_xml_group_semantics_v1.json"
)


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_audit(relative: str = "players.csv", sha: str | None = None) -> dict:
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


def xml_audit(relative: str = "players.xml", sha: str | None = None) -> dict:
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
        "files": [],
    }


def inventory(root: Path) -> dict:
    files = []
    for relative, source_role in (
        ("players.csv", ROLE),
        ("players.xml", ROLE),
    ):
        path = root / relative
        if path.is_file():
            files.append(
                {
                    "relative_path": relative,
                    "source_role": source_role,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "module_id": "multiformat_file_inventory_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "files": files,
        "duplicate_report": {"exact_duplicate_reflection_count": 0},
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


def label_semantics(root: Path) -> dict:
    return {
        "module_id": "provider_label_value_semantics_lite_v1",
        "status": "PASS",
        "registry_version": "sportsbase_label_semantics_reviewed_v2",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "provider_label_records": [
            {
                "record_id": "csv:player:passes-accurate",
                "source_relative_path": "players.csv",
                "source_sha256": sha256_file(root / "players.csv"),
                "rule_id": "passes_accurate_exact",
                "provenance_refs": ["players.csv"],
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "downstream_eligibility": "ACTION_CANDIDATE_ONLY",
                "review_status": "REVIEWED_CANDIDATE",
            }
        ],
    }


def xml_group_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def reconcile(
    root: Path,
    *,
    inventory_payload: dict | None = None,
    csv_payload: dict | None = None,
    xlsx_payload: dict | None = None,
    xml_payload: dict | None = None,
    field_payload: dict | None = None,
    label_payload: dict | None = None,
    registry_payload: dict | None = None,
) -> dict:
    csv_payload = csv_payload or csv_audit(
        sha=sha256_file(root / "players.csv")
    )
    xml_payload = xml_payload or xml_audit(
        sha=sha256_file(root / "players.xml")
    )
    return build_reconciliation(
        root,
        inventory_payload or inventory(root),
        csv_payload,
        xlsx_payload or xlsx_audit(),
        xml_payload,
        field_payload or semantics(),
        label_payload or label_semantics(root),
        registry_payload or xml_group_registry(),
    )


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
    result = reconcile(tmp_path)
    assert result["status"] == "PASS"
    pair = result["pair_reports"][0]
    assert pair["decision"] == "PASS_ALIGNMENT_CANDIDATE"
    assert pair["exact_surface_alignment_candidate_count"] == 1
    assert pair["validated_cross_format_equivalence"] is False
    assert result["canonical_event_count"] == "UNKNOWN"


def test_equal_row_count_does_not_prove_alignment(tmp_path: Path) -> None:
    make_surfaces(tmp_path, xml_action="Inaccurate passes")
    result = reconcile(tmp_path)
    pair = result["pair_reports"][0]
    assert pair["row_count_equal_signal"] is True
    assert pair["required_field_mismatch_candidate_count"] == 1
    assert "equal_row_count_does_not_prove_alignment" in pair["parse_warnings"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_unmatched_ids_are_preserved(tmp_path: Path) -> None:
    make_surfaces(tmp_path, xml_id="2")
    result = reconcile(tmp_path)
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
    result = reconcile(tmp_path)
    assert result["status"] == "FAIL_CLOSED"
    assert any("duplicate_surface_row_id_candidate" in value for value in result["hard_block_hits"])


def test_xlsx_is_not_independent_confirmation(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    result = reconcile(tmp_path)
    support = result["pair_reports"][0]["xlsx_support"]
    assert support["source_dependency_status"] == "DERIVATION_DEPENDENCY_UNRESOLVED"
    assert support["independent_confirmation_allowed"] is False
    assert support["aggregate_definition_truth"] is False


def test_derived_xlsx_cannot_claim_independent_confirmation(
    tmp_path: Path,
) -> None:
    make_surfaces(tmp_path)
    payload = xlsx_audit()
    payload["independent_confirmation_allowed"] = True
    result = reconcile(tmp_path, xlsx_payload=payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "derived_xlsx_surface_used_as_independent_confirmation" in result["hard_block_hits"]


def test_exact_duplicate_reflections_are_not_recounted(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    csv_payload = csv_audit(sha=sha256_file(tmp_path / "players.csv"))
    csv_payload["files"].append(dict(csv_payload["files"][0]))
    result = reconcile(tmp_path, csv_payload=csv_payload)
    assert result["duplicate_reflection_audit"]["csv_duplicate_reflections_not_recounted"] == 1
    assert result["role_pair_count"] == 1


def test_upstream_canonical_event_count_claim_blocks(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    bad = csv_audit(sha=sha256_file(tmp_path / "players.csv"))
    bad["canonical_event_count"] = 1
    result = reconcile(tmp_path, csv_payload=bad)
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("canonical_event_count_claimed") for value in result["hard_block_hits"])


def test_runtime_file_sha_matches_inventory_sha(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    bad_csv = csv_audit(sha="0" * 64)
    result = reconcile(tmp_path, csv_payload=bad_csv)
    assert result["status"] == "FAIL_CLOSED"
    assert "runtime_sha_mismatch:csv:players.csv" in result["hard_block_hits"]
    assert result["source_binding_audit"][0]["audit_sha_match"] is False


def test_semantic_record_requires_source_sha(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    payload = label_semantics(tmp_path)
    payload["provider_label_records"][0]["source_sha256"] = None
    result = reconcile(tmp_path, label_payload=payload)
    assert result["status"] == "FAIL_CLOSED"
    assert "source_sha_missing:label_semantics:players.csv" in result["hard_block_hits"]


def test_provider_semantic_provenance_contract_is_materialized(
    tmp_path: Path,
) -> None:
    make_surfaces(tmp_path)
    result = reconcile(tmp_path)
    record = result["provider_semantic_provenance_records"][0]
    required = {
        "source_file_id",
        "source_sha256",
        "source_role",
        "provider_candidate",
        "raw_field_path",
        "raw_label",
        "normalized_label",
        "exact_label_rule_id",
        "fallback_rule_id",
        "semantic_role_candidate",
        "action_family_candidate",
        "context_family_candidate",
        "derivation_dependency",
        "independence_group",
        "mapping_confidence",
        "ambiguity_reasons",
        "conflicting_rule_ids",
        "source_row_refs",
        "claim_ceiling",
        "status",
        "decision",
    }
    assert required <= set(record)
    assert record["provider_candidate"] == "SPORTSBASE_PROVIDER_CANDIDATE"
    assert record["raw_field_path"] is None
    assert "raw_field_path_not_proven_by_label_value_record" in record["ambiguity_reasons"]


@pytest.mark.parametrize(
    ("mapping_status", "block_prefix"),
    [
        ("TOKEN_FALLBACK_REVIEW_REQUIRED", "token_fallback_promoted_without_review"),
        ("CONFLICT_REVIEW_REQUIRED", "multi_anchor_conflict_resolved_fail_open"),
    ],
)
def test_review_only_semantics_cannot_be_promoted(
    tmp_path: Path,
    mapping_status: str,
    block_prefix: str,
) -> None:
    make_surfaces(tmp_path)
    payload = label_semantics(tmp_path)
    record = payload["provider_label_records"][0]
    record["mapping_status"] = mapping_status
    record["downstream_eligibility"] = "ACTION_CANDIDATE_ONLY"
    record["review_status"] = "REVIEW_REQUIRED"
    result = reconcile(tmp_path, label_payload=payload)
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith(block_prefix) for value in result["hard_block_hits"])


def test_field_mapping_coverage_is_not_value_semantics_coverage(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    result = reconcile(tmp_path, label_payload=semantics())
    assert result["status"] == "FAIL_CLOSED"
    assert "field_path_semantics_used_as_value_semantics" in result["hard_block_hits"]


def test_cross_id_signature_excludes_identity_and_detects_collision(
    tmp_path: Path,
) -> None:
    csv_rows = [
        ["1", "5", "6", "A - Pass", "T", "Pass", "1", "10", "20"],
        ["2", "5", "6", "A - Pass", "T", "Pass", "1", "10", "20"],
    ]
    xml_rows = [
        {
            "ID": row_id,
            "start": "5",
            "end": "6",
            "code": "A - Pass",
            "Team": "T",
            "Action": "Pass",
            "Half": "1",
            "pos_x": "10",
            "pos_y": "20",
        }
        for row_id in ("1", "2")
    ]
    write_csv(tmp_path / "players.csv", csv_rows)
    write_xml(tmp_path / "players.xml", xml_rows)
    result = reconcile(tmp_path)
    pair = result["pair_reports"][0]
    assert "id" not in pair["candidate_signature_without_id"]["fields"]
    assert "id" in pair["candidate_signature_with_id"]["fields"]
    assert pair["cross_id_collision_count"] == 1
    assert result["status"] == "REVIEW_REQUIRED"


def test_present_present_support_is_separated_from_both_missing(
    tmp_path: Path,
) -> None:
    write_csv(
        tmp_path / "players.csv",
        [["1", "5", "6", "", "", "Pass", "1", "", ""]],
    )
    write_xml(
        tmp_path / "players.xml",
        [{
            "ID": "1",
            "start": "5",
            "end": "6",
            "code": "",
            "Team": "",
            "Action": "Pass",
            "Half": "1",
            "pos_x": "",
            "pos_y": "",
        }],
    )
    result = reconcile(tmp_path)
    pair = result["pair_reports"][0]
    assert pair["present_present_support_count"] == 0
    assert pair["both_missing_support_count"] == len(("code", "team", "pos_x", "pos_y"))
    assert pair["exact_surface_alignment_candidate_count"] == 0


def test_xml_label_group_requires_explicit_candidate_contract(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    registry = xml_group_registry()
    registry["source_refs"] = []
    result = reconcile(tmp_path, registry_payload=registry)
    assert result["status"] == "FAIL_CLOSED"
    assert "semantic_rule_without_source_ref:xml_group_registry" in result["hard_block_hits"]


def test_upstream_and_local_duplicate_counts_are_separate(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    inv = inventory(tmp_path)
    inv["duplicate_report"]["exact_duplicate_reflection_count"] = 8
    result = reconcile(tmp_path, inventory_payload=inv)
    audit = result["duplicate_reflection_audit"]
    assert audit["upstream_duplicate_reflection_count"] == 8
    assert audit["local_duplicate_candidate_count"] == 0


def test_upstream_duplicate_lineage_is_required(tmp_path: Path) -> None:
    make_surfaces(tmp_path)
    inv = inventory(tmp_path)
    inv.pop("duplicate_report")
    result = reconcile(tmp_path, inventory_payload=inv)
    assert result["status"] == "FAIL_CLOSED"
    assert "upstream_duplicate_lineage_lost" in result["hard_block_hits"]


def test_active_match_execution_and_flat_outputs(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    make_surfaces(root)
    payloads = {
        "inventory.json": inventory(root),
        "csv.json": csv_audit(sha=sha256_file(root / "players.csv")),
        "xlsx.json": xlsx_audit(),
        "xml.json": xml_audit(sha=sha256_file(root / "players.xml")),
        "semantics.json": semantics(),
        "label_semantics.json": label_semantics(root),
        "xml_registry.json": xml_group_registry(),
    }
    for name, payload in payloads.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    result = write_outputs(
        root,
        root,
        tmp_path / "inventory.json",
        tmp_path / "csv.json",
        tmp_path / "xlsx.json",
        tmp_path / "xml.json",
        tmp_path / "semantics.json",
        tmp_path / "label_semantics.json",
        tmp_path / "xml_registry.json",
        tmp_path / "HPFA",
    )
    assert result["active_match_evidence_pass"] is True
    assert result["module_status"] == "PASS"
    assert result["runtime_evidence_status"] == "ACTIVE_MATCH_EVIDENCE_PASS"
    assert result["release_status"] == "NOT_PRODUCTION"
    assert result["production_release"] is False
    assert (tmp_path / "HPFA" / "cross_format_reconciliation_lite_v1.json").is_file()


def test_review_required_cannot_set_active_match_evidence_pass(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    make_surfaces(root, xml_action="Inaccurate passes")
    payloads = {
        "inventory.json": inventory(root),
        "csv.json": csv_audit(sha=sha256_file(root / "players.csv")),
        "xlsx.json": xlsx_audit(),
        "xml.json": xml_audit(sha=sha256_file(root / "players.xml")),
        "semantics.json": semantics(),
        "label_semantics.json": label_semantics(root),
        "xml_registry.json": xml_group_registry(),
    }
    for name, payload in payloads.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    result = write_outputs(
        root,
        root,
        tmp_path / "inventory.json",
        tmp_path / "csv.json",
        tmp_path / "xlsx.json",
        tmp_path / "xml.json",
        tmp_path / "semantics.json",
        tmp_path / "label_semantics.json",
        tmp_path / "xml_registry.json",
        tmp_path / "HPFA",
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["module_status"] == "REVIEW_REQUIRED"
    assert result["active_match_evidence_pass"] is False
    assert result["runtime_evidence_status"] == "ACTIVE_MATCH_EVIDENCE_NOT_GRANTED"
    assert result["release_status"] == "NOT_PRODUCTION"


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    make_surfaces(root)
    payloads = {
        "i": inventory(root),
        "c": csv_audit(sha=sha256_file(root / "players.csv")),
        "x": xlsx_audit(),
        "m": xml_audit(sha=sha256_file(root / "players.xml")),
        "s": semantics(),
        "l": label_semantics(root),
        "r": xml_group_registry(),
    }
    for name, payload in payloads.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(
            root,
            root,
            tmp_path / "i",
            tmp_path / "c",
            tmp_path / "x",
            tmp_path / "m",
            tmp_path / "s",
            tmp_path / "l",
            tmp_path / "r",
            tmp_path / "HPFA" / "nested",
        )


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "cross_format_reconciliation.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798", "Juventus", "Galatasaray"]
    assert not any(token in source for token in forbidden)
