from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from hpfa.modules.core.row_nucleus_inventory_lite.src.row_nucleus_inventory import (
    build_inventory,
    validate_out,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _xml(instances: list[dict[str, str]]) -> str:
    rows = []
    for row in instances:
        labels = "".join(
            f"<label><group>{group}</group><text>{value}</text></label>"
            for group, value in (
                ("Half", row["half"]),
                ("Action", row["action"]),
                ("Team", row.get("team", "")),
                ("pos_x", row.get("pos_x", "")),
                ("pos_y", row.get("pos_y", "")),
            )
            if value != ""
        )
        rows.append(
            "<instance>"
            f"<ID>{row['id']}</ID><start>{row['start']}</start><end>{row['end']}</end>"
            f"<code>{row['code']}</code>{labels}</instance>"
        )
    return "<file><ALL_INSTANCES>" + "".join(rows) + "</ALL_INSTANCES></file>"


def _payloads(
    root: Path,
    rows: list[dict[str, str]],
    role: str = "PLAYER_SURFACE_CANDIDATE",
):
    csv_path = root / "Players.csv"
    xml_path = root / "Players.xml"
    csv_path.write_text(
        "ID;start;end;code;team;action;half;pos_x;pos_y\n"
        + "\n".join(
            ";".join(
                [
                    row["id"],
                    row["start"],
                    row["end"],
                    row["code"],
                    row.get("team", ""),
                    row["action"],
                    row["half"],
                    row.get("pos_x", ""),
                    row.get("pos_y", ""),
                ]
            )
            for row in rows
        )
        + "\n",
        encoding="utf-8",
    )
    xml_path.write_text(_xml(rows), encoding="utf-8")
    csv_sha = _sha(csv_path)
    xml_sha = _sha(xml_path)
    csv_file = {
        "relative_path": "Players.csv",
        "file_name": "Players.csv",
        "source_role": role,
        "sha256": csv_sha,
        "encoding_candidate": "utf-8",
        "delimiter_candidate": ";",
        "raw_columns": [
            "ID",
            "start",
            "end",
            "code",
            "team",
            "action",
            "half",
            "pos_x",
            "pos_y",
        ],
        "field_bundle": {
            "start": "start",
            "end": "end",
            "period": "half",
            "action": "action",
            "team": "team",
            "start_x": "pos_x",
            "start_y": "pos_y",
        },
        "status": "PASS",
    }
    xml_file = {
        "relative_path": "Players.xml",
        "file_name": "Players.xml",
        "source_role": role,
        "sha256": xml_sha,
        "selected_row_tag_candidate": "instance",
        "security_guard": {
            "status": "PASS",
            "dtd_or_entity_declaration_present": False,
        },
        "status": "PASS",
    }
    base = {
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    inventory = base | {
        "files": [
            {
                "relative_path": "Players.csv",
                "sha256": csv_sha,
                "source_role": role,
            },
            {
                "relative_path": "Players.xml",
                "sha256": xml_sha,
                "source_role": role,
            },
        ],
        "duplicate_report": {"exact_duplicate_reflection_count": 0},
    }
    csv_payload = base | {
        "module_id": "csv_surface_reader_lite_v1",
        "files": [csv_file],
    }
    xml_payload = base | {
        "module_id": "xml_surface_reader_lite_v1",
        "files": [xml_file],
    }
    field = base | {"module_id": "provider_alias_field_semantics_lite_v1"}
    label = base | {
        "module_id": "provider_label_value_semantics_lite_v1",
        "provider_label_records": [
            {
                "source_role": role,
                "raw_label": "Passes accurate",
                "mapping_status": "EXACT_REVIEWED_CANDIDATE",
                "semantic_role_candidate": "ACTION_ANCHOR",
                "action_family_candidate": "PASS",
                "outcome_candidate": "SUCCESS",
                "downstream_eligibility": "CANDIDATE_ONLY",
                "rule_id": "pass_accurate_v1",
            }
        ],
    }
    reconciliation = base | {"module_id": "cross_format_reconciliation_lite_v1"}
    aggregate = base | {
        "module_id": "aggregate_definition_alignment_lite_v1",
        "definition_alignment_cleared": False,
    }
    metric = base | {"module_id": "provider_metric_dictionary_lite_v1"}
    registry = {
        "candidate_only": True,
        "validated_semantics": False,
        "exact_group_rules": [
            {
                "raw_group_label": raw,
                "field_key_candidate": key,
                "rule_id": f"r_{key}",
                "source_ref": "test",
            }
            for raw, key in (
                ("Action", "action"),
                ("Half", "period"),
                ("Team", "team"),
                ("pos_x", "pos_x"),
                ("pos_y", "pos_y"),
            )
        ],
    }
    return (
        inventory,
        csv_payload,
        xml_payload,
        field,
        label,
        reconciliation,
        aggregate,
        metric,
        registry,
    )


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    return root


def _row(id_: str = "1", **overrides: str) -> dict[str, str]:
    row = {
        "id": id_,
        "start": "10",
        "end": "11",
        "code": "Player - Passes accurate",
        "team": "TEAM_A",
        "action": "Passes accurate",
        "half": "1",
        "pos_x": "20",
        "pos_y": "30",
    }
    row.update(overrides)
    return row


def test_builds_sha_bound_same_role_nucleus_without_event_claim(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(root, *_payloads(root, [_row()]))
    assert result["row_nucleus_candidate_count"] == 1
    assert result["source_binding_audit"][0]["audit_sha_match"] is True
    assert result["row_nuclei"][0]["runtime_rehashed_sha256"]["csv"]
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["row_nucleus_is_canonical_event"] is False
    assert result["production_release"] is False


def test_same_timestamp_is_not_automatic_same_nucleus(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(
        root,
        *_payloads(root, [_row("1"), _row("2", code="Other - Passes accurate")]),
    )
    assert {
        row["provider_row_id_candidate"] for row in result["row_nuclei"]
    } == {"1", "2"}


def test_cross_id_signature_collision_is_review_not_merge(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(root, *_payloads(root, [_row("1"), _row("2")]))
    assert result["row_nucleus_candidate_count"] == 2
    assert result["cross_id_collision_nucleus_count"] == 2
    assert all(
        row["nucleus_status"] == "REVIEW_REQUIRED"
        for row in result["row_nuclei"]
    )


def test_unknown_label_blocks_nucleus_clearance(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(
        root,
        *_payloads(root, [_row(action="Mystery", code="Player - Mystery")]),
    )
    assert result["semantic_review_nucleus_count"] == 1
    assert "semantic_mapping_not_cleared" in result["row_nuclei"][0]["review_hits"]


def test_token_fallback_blocks_clearance(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payloads = list(_payloads(root, [_row()]))
    payloads[4]["provider_label_records"][0][
        "mapping_status"
    ] = "TOKEN_FALLBACK_REVIEW_REQUIRED"
    result = build_inventory(root, *payloads)
    assert result["row_nuclei"][0]["nucleus_status"] == "REVIEW_REQUIRED"


def test_runtime_authority_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "not_active"
    root.mkdir()
    result = build_inventory(root, *_payloads(root, [_row()]))
    assert result["status"] == "FAIL_CLOSED"
    assert "runtime_authority_path_invalid" in result["hard_block_hits"]


def test_runtime_sha_mismatch_fails_closed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payloads = list(_payloads(root, [_row()]))
    payloads[1]["files"][0]["sha256"] = "0" * 64
    result = build_inventory(root, *payloads)
    assert result["status"] == "FAIL_CLOSED"
    assert any(
        item.startswith("runtime_sha_mismatch:csv")
        for item in result["hard_block_hits"]
    )
    gates = {
        row["gate_id"]: row["status"]
        for row in result["g01_g18_rollup"]["gates"]
    }
    assert gates["G02"] == "FAIL_CLOSED"


def test_reference_source_role_is_rejected(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(
        root,
        *_payloads(root, [_row()], role="REFERENCE_ONLY"),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert (
        "reference_or_unknown_source_role_rejected:REFERENCE_ONLY"
        in result["hard_block_hits"]
    )


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(tmp_path / "HPFA" / "nested")


def test_zero_is_preserved_not_missing(tmp_path: Path) -> None:
    root = _root(tmp_path)
    nucleus = build_inventory(
        root,
        *_payloads(root, [_row(start="0", end="0", pos_x="0", pos_y="0")]),
    )["row_nuclei"][0]
    assert nucleus["start_candidate"] == "0"
    assert nucleus["end_candidate"] == "0"
    assert nucleus["pos_x_candidate"] == "0"
    assert nucleus["pos_y_candidate"] == "0"


def test_duplicate_reflection_is_not_double_counted(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payloads = list(_payloads(root, [_row()]))
    payloads[1]["files"].append(
        dict(payloads[1]["files"][0], relative_path="Players-copy.csv")
    )
    payloads[2]["files"].append(
        dict(payloads[2]["files"][0], relative_path="Players-copy.xml")
    )
    payloads[0]["duplicate_report"]["exact_duplicate_reflection_count"] = 2
    result = build_inventory(root, *payloads)
    assert result["row_nucleus_candidate_count"] == 1
    assert result["duplicate_reflection_count"] == 2


def test_aggregate_dependency_keeps_rollup_review_required(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(root, *_payloads(root, [_row()]))
    gates = {
        row["gate_id"]: row["status"]
        for row in result["g01_g18_rollup"]["gates"]
    }
    assert gates["G16"] == "REVIEW_REQUIRED"
    assert result["g01_g18_rollup"]["status"] == "REVIEW_REQUIRED"


def test_claim_and_metric_layers_remain_closed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = build_inventory(root, *_payloads(root, [_row()]))
    for key in (
        "metric_value_output_allowed",
        "comparison_allowed",
        "claim_allowed",
        "sequence_truth",
        "possession_truth",
        "phase_truth",
        "tactical_truth",
    ):
        assert result[key] is False


def test_upstream_canonical_event_claim_fails_closed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    payloads = list(_payloads(root, [_row()]))
    payloads[0]["canonical_event_count"] = 1
    result = build_inventory(root, *payloads)
    assert result["status"] == "FAIL_CLOSED"
    assert "canonical_event_count_claimed:inventory" in result["hard_block_hits"]


def test_no_sample_match_identity_leak() -> None:
    source = Path(__file__).parents[1] / "src" / "row_nucleus_inventory_hardened.py"
    text = source.read_text(encoding="utf-8")
    for token in (
        "Australia",
        "Turkey",
        "World Cup",
        "Juventus",
        "Galatasaray",
        "6935",
        "77798",
    ):
        assert token not in text
