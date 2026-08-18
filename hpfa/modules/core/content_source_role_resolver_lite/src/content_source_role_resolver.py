from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from hpfa.modules.core.csv_surface_reader_lite.src import csv_surface_reader
from hpfa.modules.core.multiformat_file_inventory_lite.src import multiformat_file_inventory
from hpfa.modules.core.triangulated_event_reflection_resolver_lite.src import (
    triangulated_event_reflection_resolver as reflection,
)
from hpfa.modules.core.xlsx_surface_reader_lite.src import xlsx_surface_reader
from hpfa.modules.core.xml_surface_reader_lite.src import xml_surface_reader

MODULE_ID = "content_source_role_resolver_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "SOURCE_ROLE_CANDIDATE_ONLY"
ROLE_CANDIDATES = {
    "PLAYER": "PLAYER_SURFACE_CANDIDATE",
    "TEAM": "TEAM_SURFACE_CANDIDATE",
    "GOALKEEPER": "GOALKEEPER_SURFACE_CANDIDATE",
}
ALL_SHORT_ROLES = frozenset(ROLE_CANDIDATES)
ROLE_BEARING_SUFFIXES = frozenset({".csv", ".tsv", ".xml", ".xlsx"})
OUTPUT_JSON = "content_source_role_resolution_lite_v1.json"
OUTPUT_TXT = "content_source_role_resolution_lite_v1.txt"
OUTPUT_INVENTORY = "resolved_input_file_inventory_v1.json"
ANALYST_TXT = "content_source_role_resolution_analyst_audit_v1.txt"

_ENGLISH_EXACT_ROLE_TERMS = {
    "GOALKEEPER": {"goalkeeper", "goalkeepers", "keeper", "keepers"},
    "PLAYER": {"player", "players"},
    "TEAM": {"team", "teams"},
}
_TURKISH_ROLE_STEMS = {
    "GOALKEEPER": {"kaleci"},
    "PLAYER": {"oyuncu", "futbolcu"},
    "TEAM": {"takım", "takim", "ekip"},
}


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("%", " percent ")
    text = re.sub(r"\[\s*([^\]]+)\s*\]", r" \1 ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_token_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _role_terms(value: Any) -> set[str]:
    tokens = set(normalize_token_text(value).split())
    roles: set[str] = set()
    for role, exact_terms in _ENGLISH_EXACT_ROLE_TERMS.items():
        if tokens & exact_terms:
            roles.add(role)
    for role, stems in _TURKISH_ROLE_STEMS.items():
        if any(any(token.startswith(stem) for stem in stems) for token in tokens):
            roles.add(role)
    return roles


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def registry_path(root: Path | None = None) -> Path:
    base = root or repo_root_from_file()
    return (
        base
        / "hpfa"
        / "modules"
        / "core"
        / "provider_label_value_semantics_lite"
        / "registry"
        / "sportsbase_label_semantics_reviewed_v2.csv"
    )


def load_role_registry(path: str | Path) -> dict[str, list[set[str]]]:
    result: dict[str, list[set[str]]] = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            label = normalize_label(raw.get("label"))
            raw_roles = str(raw.get("source_roles") or "").strip()
            if not label or not raw_roles:
                continue
            candidates = {
                value
                for value in raw_roles.split("|")
                if value in ROLE_CANDIDATES.values()
            }
            short = {
                role
                for role, candidate in ROLE_CANDIDATES.items()
                if candidate in candidates
            }
            if short:
                result.setdefault(label, []).append(short)
    return result


def filename_support(path: Path) -> list[str]:
    return sorted(_role_terms(path.name))


def sheet_name_support(names: Iterable[str]) -> list[str]:
    support: set[str] = set()
    for raw in names:
        support.update(_role_terms(raw))
    return sorted(support)


def label_role_votes(
    labels: Iterable[str],
    registry: dict[str, list[set[str]]],
    structural_roles: set[str],
) -> dict[str, int]:
    votes = Counter({role: 0 for role in ALL_SHORT_ROLES})
    for raw in labels:
        rules = registry.get(normalize_label(raw), [])
        if not rules:
            continue
        allowed_union: set[str] = set()
        for roles in rules:
            allowed_union.update(roles)
        narrowed = allowed_union & structural_roles
        if len(narrowed) == 1:
            votes[next(iter(narrowed))] += 1
    return dict(votes)


def admit_from_evidence(
    *,
    structural_roles: set[str],
    structural_admission: str | None,
    semantic_votes: dict[str, int],
    content_support: Iterable[str],
) -> tuple[str, str, list[str]]:
    if structural_admission is not None:
        return structural_admission, "ROLE_CANDIDATE_ADMITTED", ["STRUCTURAL_ROLE_EVIDENCE"]

    content_roles = {role for role in content_support if role in structural_roles}
    vote_roles = {
        role
        for role, count in semantic_votes.items()
        if count > 0 and role in structural_roles
    }
    combined = content_roles | vote_roles
    if len(combined) == 1:
        role = next(iter(combined))
        reasons: list[str] = []
        if role in content_roles:
            reasons.append("CONTENT_SEMANTIC_ROLE_MARKER")
        if semantic_votes.get(role, 0) > 0:
            reasons.append("REVIEWED_PROVIDER_ROLE_SEMANTICS")
        return role, "ROLE_CANDIDATE_ADMITTED", reasons
    if len(combined) > 1:
        return "UNRESOLVED", "REVIEW_REQUIRED", ["CONTENT_ROLE_EVIDENCE_CONFLICT"]
    return "UNRESOLVED", "REVIEW_REQUIRED", ["CONTENT_ROLE_EVIDENCE_INSUFFICIENT"]


def roleless_row_fingerprint(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in reflection.FINGERPRINT_FIELDS)


def surface_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return reflection.read_csv_or_tsv(path)
    if suffix == ".tsv":
        return reflection.read_csv_or_tsv(path, "\t")
    if suffix == ".xml":
        return reflection.read_xml(path)
    return []


def embedded_team_candidate(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        code = str(row.get("code") or "").strip()
        action = str(row.get("action") or "").strip()
        suffix = f" - {action}"
        if code and action and code.casefold().endswith(suffix.casefold()):
            if code[: -len(suffix)].strip():
                return True
    return False


def base_resolution(path: Path) -> dict[str, Any]:
    return {
        "filename_role_support": filename_support(path),
        "filename_support_used_for_admission": False,
        "cross_format_support_candidates": [],
    }


def _resolve_row_surface(
    path: Path,
    registry: dict[str, list[set[str]]],
) -> dict[str, Any]:
    rows = surface_rows(path)
    direct_team = any(str(row.get("team") or "").strip() for row in rows)
    structural_roles = {"PLAYER", "GOALKEEPER"} if direct_team else set(ALL_SHORT_ROLES)
    structural_admission: str | None = None
    if not direct_team and embedded_team_candidate(rows):
        structural_roles = {"TEAM"}
        structural_admission = "TEAM"

    labels = [
        str(row.get("action") or "")
        for row in rows
        if str(row.get("action") or "")
    ]
    votes = label_role_votes(labels, registry, structural_roles)
    role, status, reasons = admit_from_evidence(
        structural_roles=structural_roles,
        structural_admission=structural_admission,
        semantic_votes=votes,
        content_support=[],
    )
    return {
        **base_resolution(path),
        "resolved_short_role": role,
        "resolved_source_role": ROLE_CANDIDATES.get(
            role, "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
        ),
        "resolution_status": status,
        "resolution_reasons": reasons,
        "structural_role_candidates": sorted(structural_roles),
        "reviewed_label_role_votes": votes,
        "content_role_support": [],
    }


def resolve_csv(
    path: Path,
    registry: dict[str, list[set[str]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = csv_surface_reader.inspect_csv_file(
        path, "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
    )
    return _resolve_row_surface(path, registry), audit


def resolve_xml(
    path: Path,
    registry: dict[str, list[set[str]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = xml_surface_reader.inspect_xml_file(
        path, "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
    )
    return _resolve_row_surface(path, registry), audit


def xlsx_metric_labels(audit: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for sheet in audit.get("sheets", []) or []:
        for item in sheet.get("metric_inventory", []) or []:
            raw = str(item.get("raw_metric_label") or "").strip()
            if raw:
                labels.append(raw)
    return labels


def resolve_xlsx(
    path: Path,
    registry: dict[str, list[set[str]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = xlsx_surface_reader.inspect_xlsx_file(
        path, "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
    )
    content_support = sheet_name_support(
        [str(value) for value in audit.get("sheet_names", []) or []]
    )
    structural_roles = set(ALL_SHORT_ROLES)
    player_binding = False
    team_binding = False
    for sheet in audit.get("sheets", []) or []:
        identity = sheet.get("identity_binding") or {}
        player_binding = player_binding or (
            (identity.get("player") or {}).get("binding_status") == "CANDIDATE_ONLY"
        )
        team_binding = team_binding or (
            (identity.get("team") or {}).get("binding_status") == "CANDIDATE_ONLY"
        )
    if team_binding and not player_binding:
        structural_roles = {"TEAM"}
    elif player_binding:
        structural_roles = {"PLAYER", "GOALKEEPER"}

    votes = label_role_votes(
        xlsx_metric_labels(audit), registry, structural_roles
    )
    role, status, reasons = admit_from_evidence(
        structural_roles=structural_roles,
        structural_admission=None,
        semantic_votes=votes,
        content_support=content_support,
    )
    return {
        **base_resolution(path),
        "resolved_short_role": role,
        "resolved_source_role": ROLE_CANDIDATES.get(
            role, "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
        ),
        "resolution_status": status,
        "resolution_reasons": reasons,
        "structural_role_candidates": sorted(structural_roles),
        "reviewed_label_role_votes": votes,
        "content_role_support": content_support,
    }, audit


def cross_format_support(records: list[dict[str, Any]], input_root: Path) -> None:
    admitted_csv = [
        record
        for record in records
        if record["extension"] in {".csv", ".tsv"}
        and record["resolution"]["resolution_status"] == "ROLE_CANDIDATE_ADMITTED"
    ]
    xml_records = [record for record in records if record["extension"] == ".xml"]
    if not admitted_csv or not xml_records:
        return

    csv_counters: dict[str, tuple[Counter[tuple[str, ...]], str]] = {}
    for record in admitted_csv:
        rows = surface_rows(input_root / record["relative_path"])
        csv_counters[record["relative_path"]] = (
            Counter(roleless_row_fingerprint(row) for row in rows),
            record["resolution"]["resolved_short_role"],
        )

    for record in xml_records:
        xml_counter = Counter(
            roleless_row_fingerprint(row)
            for row in surface_rows(input_root / record["relative_path"])
        )
        candidates: list[dict[str, Any]] = []
        for csv_path, (csv_counter, role) in csv_counters.items():
            keys = set(csv_counter) | set(xml_counter)
            matched = sum(
                min(csv_counter[key], xml_counter[key]) for key in keys
            )
            if matched > 0:
                candidates.append(
                    {
                        "csv_relative_path": csv_path,
                        "role": role,
                        "matched_visible_row_fingerprint_count": matched,
                    }
                )
        candidates.sort(
            key=lambda item: (
                -item["matched_visible_row_fingerprint_count"],
                item["csv_relative_path"],
            )
        )
        current = record["resolution"]
        current["cross_format_support_candidates"] = candidates
        if not candidates:
            continue
        top = candidates[0]
        tied = [
            item
            for item in candidates
            if item["matched_visible_row_fingerprint_count"]
            == top["matched_visible_row_fingerprint_count"]
        ]
        if len(tied) != 1:
            current["resolution_reasons"] = sorted(
                set(current["resolution_reasons"] + ["CROSS_FORMAT_ROLE_SUPPORT_TIE"])
            )
            continue
        if (
            current["resolution_status"] == "ROLE_CANDIDATE_ADMITTED"
            and current["resolved_short_role"] != top["role"]
        ):
            current["resolution_status"] = "REVIEW_REQUIRED"
            current["resolved_short_role"] = "UNRESOLVED"
            current["resolved_source_role"] = "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
            current["resolution_reasons"] = sorted(
                set(current["resolution_reasons"] + ["CROSS_FORMAT_ROLE_CONFLICT"])
            )
        elif current["resolution_status"] != "ROLE_CANDIDATE_ADMITTED":
            current["resolved_short_role"] = top["role"]
            current["resolved_source_role"] = ROLE_CANDIDATES[top["role"]]
            current["resolution_status"] = "ROLE_CANDIDATE_ADMITTED"
            current["resolution_reasons"] = sorted(
                set(
                    current["resolution_reasons"]
                    + ["CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT"]
                )
            )


def validate_output_root(path: str | Path) -> Path:
    out = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in out.parts and out.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return out


def build_report(
    input_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    if not input_root.is_dir():
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["input_root_missing"],
            "files": [],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    registry = load_role_registry(registry_path(repo_root))
    inventory = multiformat_file_inventory.build_inventory(input_root)
    records: list[dict[str, Any]] = []
    hard_blocks = list(inventory.get("hard_block_hits") or [])

    for item in inventory.get("files", []) or []:
        extension = str(item.get("extension") or "").casefold()
        relative_path = str(item.get("relative_path") or "")
        path = input_root / relative_path
        audit: dict[str, Any] | None = None
        if extension in {".csv", ".tsv"}:
            resolution, audit = resolve_csv(path, registry)
        elif extension == ".xml":
            resolution, audit = resolve_xml(path, registry)
        elif extension == ".xlsx":
            resolution, audit = resolve_xlsx(path, registry)
        else:
            resolution = {
                **base_resolution(path),
                "resolved_short_role": "NOT_APPLICABLE",
                "resolved_source_role": str(
                    item.get("source_role")
                    or "STRUCTURED_SUPPORT_SURFACE_CANDIDATE"
                ),
                "resolution_status": "NOT_APPLICABLE",
                "resolution_reasons": ["ROLE_RESOLUTION_NOT_APPLICABLE_TO_FORMAT"],
                "structural_role_candidates": [],
                "reviewed_label_role_votes": {},
                "content_role_support": [],
            }
        if audit and audit.get("status") == "FAIL_CLOSED":
            hard_blocks.extend(
                f"reader_fail_closed:{relative_path}:{value}"
                for value in audit.get("hard_block_hits", []) or ["unknown"]
            )
        records.append(
            {
                "file_id": item.get("file_id"),
                "file_name": item.get("file_name"),
                "relative_path": relative_path,
                "extension": extension,
                "sha256": item.get("sha256"),
                "inventory_source_role": item.get("source_role"),
                "role_resolution_applicable": extension in ROLE_BEARING_SUFFIXES,
                "resolution": resolution,
            }
        )

    cross_format_support(records, input_root)
    unresolved = [
        record
        for record in records
        if record["role_resolution_applicable"]
        and record["resolution"]["resolution_status"]
        != "ROLE_CANDIDATE_ADMITTED"
    ]
    role_counts = Counter(
        record["resolution"]["resolved_source_role"]
        for record in records
        if record["resolution"]["resolution_status"]
        == "ROLE_CANDIDATE_ADMITTED"
    )
    hard_blocks = sorted(set(hard_blocks))
    status = (
        "FAIL_CLOSED"
        if hard_blocks
        else ("REVIEW_REQUIRED" if unresolved else "PASS")
    )
    return {
        "module_id": MODULE_ID,
        "status": status,
        "input_root": str(input_root),
        "supported_file_count": len(records),
        "role_resolution_applicable_file_count": sum(
            bool(record["role_resolution_applicable"]) for record in records
        ),
        "role_candidate_admitted_file_count": sum(
            record["resolution"]["resolution_status"]
            == "ROLE_CANDIDATE_ADMITTED"
            for record in records
        ),
        "unresolved_role_file_count": len(unresolved),
        "resolved_role_counts": dict(sorted(role_counts.items())),
        "files": records,
        "hard_block_hits": hard_blocks,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "independent_source_vote_allowed": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "safe_statement": (
                "Visible supported surfaces were assigned candidate source roles only "
                "when content evidence admitted the role; filename evidence was never "
                "sufficient by itself."
            )
        },
    }


def resolved_inventory(
    report: dict[str, Any],
    raw_inventory: dict[str, Any],
) -> dict[str, Any]:
    by_path = {
        record["relative_path"]: record
        for record in report.get("files", []) or []
    }
    result = json.loads(json.dumps(raw_inventory))
    for item in result.get("files", []) or []:
        record = by_path.get(str(item.get("relative_path") or ""))
        if not record:
            continue
        resolution = record["resolution"]
        item["inventory_source_role"] = item.get("source_role")
        item["source_role_resolution_status"] = resolution.get(
            "resolution_status"
        )
        item["source_role_resolution_reasons"] = resolution.get(
            "resolution_reasons"
        )
        item["filename_support_used_for_role_admission"] = False
        if resolution.get("resolution_status") == "ROLE_CANDIDATE_ADMITTED":
            item["source_role"] = resolution.get("resolved_source_role")
        elif record.get("role_resolution_applicable"):
            item["source_role"] = "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
    result["source_role_resolution_module"] = MODULE_ID
    result["source_role_resolution_status"] = report.get("status")
    result["canonical_event_count"] = CANONICAL_EVENT_COUNT
    result["production_release"] = False
    return result


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    output_root = validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=root)
    raw_inventory = multiformat_file_inventory.build_inventory(input_dir)
    inventory = resolved_inventory(report, raw_inventory)
    report["outputs"] = {
        "json": str(output_root / OUTPUT_JSON),
        "txt": str(output_root / OUTPUT_TXT),
        "resolved_inventory": str(output_root / OUTPUT_INVENTORY),
        "analyst": str(output_root / ANALYST_TXT),
    }
    (output_root / OUTPUT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / OUTPUT_INVENTORY).write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = [
        "HPFA CONTENT SOURCE ROLE RESOLVER LITE V1",
        f"status={report.get('status')}",
        f"supported_file_count={report.get('supported_file_count')}",
        f"role_resolution_applicable_file_count={report.get('role_resolution_applicable_file_count')}",
        f"role_candidate_admitted_file_count={report.get('role_candidate_admitted_file_count')}",
        f"unresolved_role_file_count={report.get('unresolved_role_file_count')}",
        f"resolved_role_counts={report.get('resolved_role_counts')}",
        f"hard_block_hits={report.get('hard_block_hits')}",
        "filename_support_used_for_admission=false",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    (output_root / OUTPUT_TXT).write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )
    analyst = [
        "HPFA CONTENT SOURCE ROLE ANALYST AUDIT V1",
        f"status={report.get('status')}",
    ]
    for record in report.get("files", []) or []:
        resolution = record["resolution"]
        analyst.extend(
            [
                "",
                f"file={record.get('relative_path')}",
                f"format={record.get('extension')}",
                f"inventory_source_role={record.get('inventory_source_role')}",
                f"resolved_source_role={resolution.get('resolved_source_role')}",
                f"resolution_status={resolution.get('resolution_status')}",
                f"resolution_reasons={resolution.get('resolution_reasons')}",
                f"structural_role_candidates={resolution.get('structural_role_candidates')}",
                f"content_role_support={resolution.get('content_role_support')}",
                f"reviewed_label_role_votes={resolution.get('reviewed_label_role_votes')}",
                f"filename_role_support={resolution.get('filename_role_support')}",
                "filename_support_used_for_admission=false",
            ]
        )
    analyst.extend(
        ["", "canonical_event_count=UNKNOWN", "production_release=false"]
    )
    (output_root / ANALYST_TXT).write_text(
        "\n".join(analyst) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA content-based source role resolver lite v1"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    report = write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "supported_file_count": report.get("supported_file_count"),
                "role_candidate_admitted_file_count": report.get(
                    "role_candidate_admitted_file_count"
                ),
                "unresolved_role_file_count": report.get(
                    "unresolved_role_file_count"
                ),
                "resolved_role_counts": report.get("resolved_role_counts"),
                "hard_block_hits": report.get("hard_block_hits"),
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "production_release": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
