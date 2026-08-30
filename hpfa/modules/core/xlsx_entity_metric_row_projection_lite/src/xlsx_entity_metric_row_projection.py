from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from hpfa.modules.core.xlsx_surface_reader_lite.src.xlsx_surface_reader import native_reader as xlsx

MODULE_ID = "xlsx_entity_metric_row_projection_lite_v1"
CLAIM_CEILING = "XLSX_ROW_ALIGNED_ENTITY_METRIC_SURFACE_ONLY"
IDENTITY_KEYS = {
    "player": "player_raw_candidate",
    "team": "team_raw_candidate",
    "position": "position_raw_candidate",
    "minutes": "minutes_raw_candidate",
    "shirt_number": "shirt_number_raw_candidate",
}


def _stable_id(source_sha: str, sheet: str, row: int) -> str:
    raw = f"{source_sha}|{sheet}|{row}".encode("utf-8")
    return "xrp_" + hashlib.sha256(raw).hexdigest()[:24]


def _inventory_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("file_id")): item
        for item in inventory.get("files", [])
        if item.get("file_id") is not None
    }


def _project_sheet(
    formula_ws: Any,
    value_ws: Any,
    sheet_audit: dict[str, Any],
    file_meta: dict[str, Any],
    match_surface_binding_id: str | None,
) -> dict[str, Any]:
    header_row = int(sheet_audit.get("header_row_index") or 0)
    profiles = list(sheet_audit.get("column_profiles") or [])
    raw_columns = list(sheet_audit.get("raw_columns") or [])
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if str(sheet_audit.get("sheet_state") or "visible") != "visible":
        return {
            "sheet_name": sheet_audit.get("sheet_name"),
            "status": "NOT_ADMITTED_HIDDEN_SHEET",
            "rows": [],
            "hard_block_hits": [],
            "review_hits": ["hidden_sheet_not_projected"],
        }
    if header_row <= 0 or not profiles or len(profiles) != len(raw_columns):
        hard_blocks.append("xlsx_audit_header_or_profile_invalid")
    if hard_blocks:
        return {
            "sheet_name": sheet_audit.get("sheet_name"),
            "status": "FAIL_CLOSED",
            "rows": [],
            "hard_block_hits": hard_blocks,
            "review_hits": [],
        }

    actual_headers = [
        "" if formula_ws.cell(row=header_row, column=index + 1).value is None
        else str(formula_ws.cell(row=header_row, column=index + 1).value).strip()
        for index in range(len(profiles))
    ]
    if actual_headers != raw_columns:
        return {
            "sheet_name": sheet_audit.get("sheet_name"),
            "status": "FAIL_CLOSED",
            "rows": [],
            "hard_block_hits": ["xlsx_header_binding_mismatch"],
            "review_hits": [],
        }

    normalized_metric_keys = [
        str(profile.get("normalized_column") or "")
        for profile in profiles
        if not profile.get("identity_role_candidate")
    ]
    duplicate_keys = sorted({key for key in normalized_metric_keys if key and normalized_metric_keys.count(key) > 1})
    if duplicate_keys:
        return {
            "sheet_name": sheet_audit.get("sheet_name"),
            "status": "REVIEW_REQUIRED",
            "rows": [],
            "hard_block_hits": [],
            "review_hits": [f"duplicate_normalized_metric_column:{key}" for key in duplicate_keys],
        }

    max_row = max(int(formula_ws.max_row or 0), int(value_ws.max_row or 0))
    rows: list[dict[str, Any]] = []
    for row_number in range(header_row + 1, max_row + 1):
        values = [value_ws.cell(row=row_number, column=index + 1).value for index in range(len(profiles))]
        formulas = [formula_ws.cell(row=row_number, column=index + 1) for index in range(len(profiles))]
        if not any(
            not xlsx.is_blank(value) or (cell.data_type == "f" and cell.value is not None)
            for value, cell in zip(values, formulas)
        ):
            continue

        identity = {value: None for value in IDENTITY_KEYS.values()}
        metrics: dict[str, dict[str, Any]] = {}
        row_reviews: list[str] = []
        for index, profile in enumerate(profiles):
            cached = values[index]
            formula_cell = formulas[index]
            role = profile.get("identity_role_candidate")
            if role in IDENTITY_KEYS:
                identity[IDENTITY_KEYS[str(role)]] = xlsx.jsonable(cached)
                continue
            key = str(profile.get("normalized_column") or "")
            formula_present = formula_cell.data_type == "f"
            cache_missing = formula_present and xlsx.is_blank(cached)
            if cache_missing:
                row_reviews.append(f"formula_without_cached_value:{key}")
            metrics[key] = {
                "raw_metric_label": str(profile.get("raw_column") or ""),
                "raw_value": None if cache_missing else xlsx.jsonable(cached),
                "value_kind": "blank" if cache_missing else xlsx.value_kind(cached),
                "number_format": str(
                    value_ws.cell(row=row_number, column=index + 1).number_format
                    or formula_cell.number_format
                    or ""
                ),
                "percent_header_candidate": bool(profile.get("percent_header_candidate")),
                "formula_present": formula_present,
                "cached_value_used": bool(formula_present and not cache_missing),
                "value_status": "NOT_ADMITTED_FORMULA_CACHE_MISSING" if cache_missing else ("MISSING" if xlsx.is_blank(cached) else "OBSERVED"),
                "metric_truth": False,
            }

        rows.append({
            "row_projection_id": _stable_id(str(file_meta["source_sha256"]), str(sheet_audit.get("sheet_name")), row_number),
            "file_id": file_meta["file_id"],
            "relative_path": file_meta["relative_path"],
            "source_sha256": file_meta["source_sha256"],
            "source_role": file_meta["source_role"],
            "sheet_name": sheet_audit.get("sheet_name"),
            "source_row_number": row_number,
            "match_surface_binding_id": match_surface_binding_id,
            "identity_candidates": identity,
            "metric_values": metrics,
            "review_hits": sorted(set(row_reviews)),
            "validated_identity": False,
            "row_projection_is_canonical_event": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if any(row.get("review_hits") for row in rows):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"
    return {
        "sheet_name": sheet_audit.get("sheet_name"),
        "status": status,
        "rows": rows,
        "projected_row_count": len(rows),
        "hard_block_hits": [],
        "review_hits": sorted({hit for row in rows for hit in row.get("review_hits", [])}),
    }


def build_projection(
    input_root: str | Path,
    inventory: dict[str, Any],
    xlsx_audit: dict[str, Any],
    *,
    match_surface_binding_id: str | None = None,
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    base = {
        "module_id": MODULE_ID,
        "claim_ceiling": CLAIM_CEILING,
        "match_surface_binding_id": match_surface_binding_id,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "validated_identity": False,
        "aggregate_definition_truth": False,
        "metric_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "production_release": False,
    }
    if not root.is_dir():
        return base | {"status": "FAIL_CLOSED", "files": [], "row_projection_count": 0, "hard_block_hits": ["input_root_missing"], "review_hits": []}
    if xlsx_audit.get("module_id") != "xlsx_surface_reader_lite_v1" or xlsx_audit.get("status") == "FAIL_CLOSED":
        return base | {"status": "FAIL_CLOSED", "files": [], "row_projection_count": 0, "hard_block_hits": ["xlsx_surface_audit_not_admitted"], "review_hits": []}

    by_id = _inventory_index(inventory)
    files: list[dict[str, Any]] = []
    hard_blocks: list[str] = []
    review_hits: list[str] = []
    for file_audit in xlsx_audit.get("files", []) or []:
        file_id = str(file_audit.get("file_id") or "")
        item = by_id.get(file_id)
        if item is None:
            hard_blocks.append(f"inventory_file_id_missing:{file_id}")
            continue
        relative = str(file_audit.get("relative_path") or "")
        source_sha = str(file_audit.get("sha256") or "")
        if relative != str(item.get("relative_path") or "") or source_sha != str(item.get("sha256") or ""):
            hard_blocks.append(f"inventory_audit_binding_mismatch:{file_id}")
            continue
        path = root / relative
        if not path.is_file() or xlsx.xlsx.sha256_file(path) if False else False:
            pass
        try:
            actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            hard_blocks.append(f"xlsx_source_unreadable:{file_id}")
            continue
        if actual_sha != source_sha:
            hard_blocks.append(f"xlsx_source_sha256_mismatch:{file_id}")
            continue
        try:
            formula_book = xlsx.load_workbook(path, read_only=False, data_only=False, keep_links=False)
            value_book = xlsx.load_workbook(path, read_only=False, data_only=True, keep_links=False)
        except Exception as exc:
            hard_blocks.append(f"xlsx_native_open_failed:{file_id}:{type(exc).__name__}")
            continue
        file_result = {
            "file_id": file_id,
            "relative_path": relative,
            "source_sha256": source_sha,
            "source_role": str(item.get("source_role") or "UNKNOWN"),
            "sheets": [],
            "hard_block_hits": [],
            "review_hits": [],
        }
        try:
            for sheet_audit in file_audit.get("sheets", []) or []:
                name = str(sheet_audit.get("sheet_name") or "")
                if name not in formula_book.sheetnames or name not in value_book.sheetnames:
                    file_result["hard_block_hits"].append(f"audited_sheet_missing:{name}")
                    continue
                sheet = _project_sheet(
                    formula_book[name], value_book[name], sheet_audit,
                    {
                        "file_id": file_id,
                        "relative_path": relative,
                        "source_sha256": source_sha,
                        "source_role": file_result["source_role"],
                    },
                    match_surface_binding_id,
                )
                file_result["sheets"].append(sheet)
                file_result["hard_block_hits"].extend(sheet.get("hard_block_hits") or [])
                file_result["review_hits"].extend(sheet.get("review_hits") or [])
        finally:
            formula_book.close()
            value_book.close()
        file_result["hard_block_hits"] = sorted(set(file_result["hard_block_hits"]))
        file_result["review_hits"] = sorted(set(file_result["review_hits"]))
        file_result["status"] = "FAIL_CLOSED" if file_result["hard_block_hits"] else ("REVIEW_REQUIRED" if file_result["review_hits"] else "PASS")
        files.append(file_result)
        hard_blocks.extend(file_result["hard_block_hits"])
        review_hits.extend(file_result["review_hits"])

    row_count = sum(len(sheet.get("rows") or []) for file_row in files for sheet in file_row.get("sheets", []))
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "PASS")
    return base | {
        "status": status,
        "xlsx_file_count": len(files),
        "row_projection_count": row_count,
        "files": files,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
    }
