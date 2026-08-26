from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from xml_common import (
    CANONICAL_EVENT_COUNT,
    CLAIM_CEILING,
    MODULE_ID,
    OUT,
    XmlSurfaceError,
    is_active,
    representatives,
    resolve_inventory_path,
    security_guard,
    validate_out,
)
from xml_rows import profile_rows
from xml_structure import scan_structure


def _transitive_binding_error() -> str | None:
    bindings = (
        ("xml_common", "security_guard"),
        ("xml_rows", "profile_rows"),
        ("xml_structure", "scan_structure"),
        ("xml_common", "XmlSurfaceError"),
    )
    for module_name, attribute in bindings:
        module = sys.modules.get(module_name)
        if module is None:
            return f"runtime_transitive_module_missing:{module_name}"
        if globals().get(attribute) is not getattr(module, attribute, None):
            return (
                "runtime_transitive_callable_binding_mismatch:"
                f"xml_surface_reader.{attribute}"
            )
    return None


def inspect_xml_file(path: str | Path, source_role: str) -> dict[str, Any]:
    xml_path = Path(path)
    base = {
        "file_name": xml_path.name,
        "path": str(xml_path),
        "source_role": source_role,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    if xml_path.suffix.casefold() != ".xml":
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["non_xml_surface_rejected"],
            "parse_warnings": [],
        }
    if not xml_path.is_file():
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["xml_file_missing"],
            "parse_warnings": [],
        }

    binding_error = _transitive_binding_error()
    if binding_error is not None:
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": [binding_error],
            "parse_warnings": [],
        }

    try:
        guard = security_guard(xml_path)
        structure = scan_structure(xml_path)
        selected = structure.get("selected_row_tag_candidate")
        warnings: list[str] = []
        rows = {
            "row_candidate_count": 0,
            "field_path_count": 0,
            "field_inventory": [],
            "row_shape_count": 0,
            "row_shape_inventory": [],
            "exact_duplicate_row_candidate_count": 0,
            "example_rows": [],
            "identity_binding": {},
        }
        if selected:
            rows = profile_rows(xml_path, str(selected))
        else:
            warnings.append("xml_row_container_candidate_unresolved")
        if structure.get("row_candidate_ambiguous"):
            warnings.append("xml_row_container_candidate_ambiguous")
        return base | {
            "status": "REVIEW_REQUIRED" if warnings else "PASS",
            "security_guard": guard,
            "xml_structure": structure,
            "selected_row_tag_candidate": selected,
            **rows,
            "hard_block_hits": [],
            "parse_warnings": warnings,
            "does_not_measure": [
                "canonical_event_truth",
                "validated_event_identity",
                "validated_team_identity",
                "validated_player_identity",
                "provider_semantics_truth",
                "cross_format_reconciliation_truth",
                "sequence_truth",
                "phase_truth",
                "tactical_truth",
            ],
        }
    except XmlSurfaceError as exc:
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": [str(exc)],
            "parse_warnings": [],
        }
    except (ET.ParseError, OSError):
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["malformed_xml"],
            "parse_warnings": [],
        }


def build_xml_surface_audit(
    input_root: str | Path,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["input_root_missing"],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "active_match_evidence_pass": False,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }
    if not isinstance(inventory, dict):
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["inventory_payload_not_object"],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "active_match_evidence_pass": False,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    files: list[dict[str, Any]] = []
    for item in representatives(inventory):
        try:
            result = inspect_xml_file(
                resolve_inventory_path(root, item.get("relative_path")),
                str(item.get("source_role") or "UNKNOWN"),
            )
        except XmlSurfaceError as exc:
            result = {
                "file_name": str(item.get("file_name") or ""),
                "path": str(item.get("relative_path") or ""),
                "source_role": str(item.get("source_role") or "UNKNOWN"),
                "status": "FAIL_CLOSED",
                "hard_block_hits": [str(exc)],
                "parse_warnings": [],
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "production_release": False,
                "claim_ceiling": CLAIM_CEILING,
            }
        result.update(
            {
                "file_id": item.get("file_id"),
                "relative_path": item.get("relative_path"),
                "sha256": item.get("sha256"),
                "inventory_xml_root_tag": item.get("xml_root_tag"),
                "inventory_xml_namespace_map": item.get("xml_namespace_map") or {},
                "inventory_surface_row_count": item.get("surface_row_count"),
                "inventory_visible_column_count": item.get("visible_column_count"),
            }
        )
        files.append(result)

    hard_blocks = sorted(
        {
            block
            for result in files
            for block in result.get("hard_block_hits", [])
        }
    )
    if not files:
        status = "FAIL_CLOSED"
        hard_blocks = ["xml_surface_missing"]
    elif hard_blocks or any(result.get("status") == "FAIL_CLOSED" for result in files):
        status = "FAIL_CLOSED"
    elif any(result.get("status") == "REVIEW_REQUIRED" for result in files):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "input_root": str(root),
        "xml_file_count": len(files),
        "files": files,
        "hard_block_hits": hard_blocks,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "active_match_evidence_pass": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "visible_xml_surfaces": len(files),
            "row_candidate_count": sum(
                int(result.get("row_candidate_count") or 0)
                for result in files
            ),
            "safe_statement": (
                "Visible XML surfaces were structurally profiled; row containers, "
                "fields and identity/action values remain candidates rather than "
                "canonical truth."
            ),
        },
    }


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA XML SURFACE READER LITE V1",
            f"status={payload.get('status')}",
            f"xml_file_count={payload.get('xml_file_count')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            f"active_match_evidence_pass={payload.get('active_match_evidence_pass')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "claim_ceiling=XML_SURFACE_AUDIT_ONLY",
            "",
        ]
    )


def render_analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA XML SURFACE ANALYST AUDIT LITE V1",
        f"status={payload.get('status')}",
        f"visible_xml_surfaces={payload.get('xml_file_count')}",
    ]
    for result in payload.get("files", []):
        structure = result.get("xml_structure") or {}
        lines += [
            "",
            f"file={result.get('relative_path')}",
            f"source_role={result.get('source_role')}",
            f"status={result.get('status')}",
            f"root_tag={structure.get('root_tag')}",
            f"namespace_map={structure.get('namespace_map')}",
            f"selected_row_tag_candidate={result.get('selected_row_tag_candidate')}",
            f"row_candidate_count={result.get('row_candidate_count')}",
            f"field_path_count={result.get('field_path_count')}",
            f"row_shape_count={result.get('row_shape_count')}",
            (
                "exact_duplicate_row_candidate_count="
                f"{result.get('exact_duplicate_row_candidate_count')}"
            ),
            f"identity_binding={result.get('identity_binding')}",
            f"hard_block_hits={result.get('hard_block_hits')}",
            f"parse_warnings={result.get('parse_warnings')}",
        ]
    lines += [
        "",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        (
            "safe_statement=visible XML row-level surfaces were profiled; row, "
            "field, identity and action semantics remain candidate-only."
        ),
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    input_root: str | Path,
    inventory_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    output_root = validate_out(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
        payload = build_xml_surface_audit(input_root, inventory)
    except OSError:
        payload = {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["inventory_file_unreadable"],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "active_match_evidence_pass": False,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }
    except json.JSONDecodeError:
        payload = {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["inventory_json_malformed"],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "active_match_evidence_pass": False,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    payload["active_match_evidence_pass"] = (
        payload.get("status") == "PASS"
        and not payload.get("hard_block_hits")
        and is_active(Path(input_root).resolve(strict=False))
    )
    paths = {key: output_root / name for key, name in OUT.items()}
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    paths["main"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = write_outputs(args.input_root, args.inventory, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "xml_file_count",
                    "hard_block_hits",
                    "active_match_evidence_pass",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())