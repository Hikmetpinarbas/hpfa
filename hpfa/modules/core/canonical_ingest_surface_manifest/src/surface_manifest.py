#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

EXPECTED = {
    ("players", "csv"),
    ("teams", "csv"),
    ("goalkeepers", "csv"),
    ("players", "xml"),
    ("teams", "xml"),
    ("goalkeepers", "xml"),
    ("players", "xlsx"),
    ("goalkeepers", "xlsx"),
}
ROLE_CANDIDATE_TO_SURFACE_ROLE = {
    "PLAYER_SURFACE_CANDIDATE": "players",
    "TEAM_SURFACE_CANDIDATE": "teams",
    "GOALKEEPER_SURFACE_CANDIDATE": "goalkeepers",
}
REFERENCE_MARKERS = (
    "archive",
    "sample",
    "reference",
    "match_tests",
    "match001",
    "quarantine",
)


def source_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return "xlsx" if suffix == "xlsm" else suffix


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return sum(1 for _ in csv.DictReader(handle, dialect=dialect))


def xml_instances(path: Path) -> int:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0
    return sum(
        1
        for element in root.iter()
        if str(element.tag).split("}")[-1].lower() in {"instance", "event"}
    )


def xlsx_rows(path: Path) -> int:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            ]
            if not names:
                return 0
            root = ET.fromstring(archive.read(names[0]))
    except Exception:
        return 0
    return sum(
        1
        for element in root.iter()
        if str(element.tag).endswith("}row") or str(element.tag) == "row"
    )


def visible_rows(path: Path, fmt: str) -> int | None:
    if fmt == "csv":
        return csv_rows(path)
    if fmt == "xml":
        return xml_instances(path)
    if fmt == "xlsx":
        return xlsx_rows(path)
    return None


def surface_family(role: str, fmt: str) -> str:
    if fmt == "csv":
        return f"{role}_csv_event_coordinate_action_surface"
    if fmt == "xml":
        return f"{role}_xml_action_time_conformance_surface"
    if fmt == "xlsx":
        return f"{role}_xlsx_aggregate_validation_surface"
    return f"{role}_{fmt}_surface"


def _base_fail_closed(root: Path, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "manifest_id": "canonical_ingest_surface_manifest_v1",
        "status": "FAIL_CLOSED",
        "reason": reason,
        "match_dir": str(root),
        "surfaces": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "claim_safety": "EVIDENCE_ONLY",
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "report_language_allowed": False,
        "production_binding_allowed": False,
        "production_release": False,
        **extra,
    }


def _candidate_role_evidence(
    role_report: dict[str, Any] | None,
    root: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(role_report, dict):
        return {}, ["source_role_candidate_evidence_required"]
    if role_report.get("status") != "PASS":
        return {}, [
            "source_role_candidate_evidence_not_pass:"
            f"{role_report.get('status', 'UNKNOWN')}"
        ]
    if role_report.get("claim_ceiling") != "SOURCE_ROLE_CANDIDATE_ONLY":
        return {}, ["source_role_candidate_claim_ceiling_invalid"]
    if role_report.get("canonical_event_count") != "UNKNOWN":
        return {}, ["source_role_candidate_canonical_event_count_promoted"]
    if role_report.get("production_release") is not False:
        return {}, ["source_role_candidate_production_release_promoted"]

    report_root = Path(str(role_report.get("input_root") or "")).expanduser().resolve(strict=False)
    if report_root != root:
        return {}, ["source_role_candidate_input_root_mismatch"]

    evidence: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for record in role_report.get("files", []) or []:
        if not record.get("role_resolution_applicable"):
            continue
        relative_path = str(record.get("relative_path") or "")
        resolution = record.get("resolution") or {}
        status = resolution.get("resolution_status")
        candidate = str(resolution.get("resolved_source_role") or "")
        role = ROLE_CANDIDATE_TO_SURFACE_ROLE.get(candidate)
        expected_sha256 = str(record.get("sha256") or "").strip().lower()
        if status != "ROLE_CANDIDATE_ADMITTED" or role is None:
            errors.append(f"source_role_candidate_unresolved_or_conflicting:{relative_path}")
            continue
        if relative_path in evidence:
            errors.append(f"source_role_candidate_duplicate_path:{relative_path}")
            continue
        if len(expected_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in expected_sha256
        ):
            errors.append(f"source_role_candidate_sha256_missing_or_invalid:{relative_path}")
            continue
        current_path = root / relative_path
        if not current_path.is_file():
            errors.append(f"source_role_candidate_surface_missing:{relative_path}")
            continue
        if file_sha256(current_path) != expected_sha256:
            errors.append(f"source_role_candidate_content_hash_mismatch:{relative_path}")
            continue
        evidence[relative_path] = {
            "source_file_role": role,
            "source_role_candidate": candidate,
            "source_role_resolution_status": status,
            "source_role_resolution_reasons": list(
                resolution.get("resolution_reasons") or []
            ),
            "source_role_evidence_sha256": expected_sha256,
            "filename_support_used_for_admission": False,
        }
    return evidence, sorted(set(errors))


def inventory(
    path: Path,
    root: Path,
    role_evidence: dict[str, Any],
) -> dict[str, Any]:
    fmt = source_format(path)
    role = str(role_evidence["source_file_role"])
    return {
        "source_file": path.name,
        "relative_path": str(path.relative_to(root)),
        "source_file_role": role,
        "source_role_candidate": role_evidence["source_role_candidate"],
        "source_role_resolution_status": role_evidence[
            "source_role_resolution_status"
        ],
        "source_role_resolution_reasons": role_evidence[
            "source_role_resolution_reasons"
        ],
        "source_role_evidence_sha256": role_evidence["source_role_evidence_sha256"],
        "filename_support_used_for_admission": False,
        "source_format": fmt,
        "surface_family": surface_family(role, fmt),
        "surface_row_count": visible_rows(path, fmt),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "aggregate_surface": fmt == "xlsx",
        "event_surface_candidate": fmt in {"csv", "xml"},
        "row_count_warning": "surface_row_count_is_not_canonical_event_count",
        "claim_safety": "EVIDENCE_ONLY",
    }


def build_manifest(
    match_dir: str,
    role_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(match_dir).expanduser().resolve()
    markers = [marker for marker in REFERENCE_MARKERS if marker in str(root).lower()]
    if markers:
        return _base_fail_closed(
            root,
            "reference_marker_in_path",
            markers=markers,
        )
    if not root.is_dir():
        return _base_fail_closed(root, "match_dir_missing")

    role_evidence, evidence_errors = _candidate_role_evidence(role_report, root)
    if evidence_errors:
        return _base_fail_closed(
            root,
            "source_role_candidate_evidence_rejected",
            source_role_candidate_evidence_errors=evidence_errors,
            source_role_candidate_evidence_status=(role_report or {}).get("status"),
        )

    files = [
        path
        for path in root.iterdir()
        if path.is_file() and source_format(path) in {"csv", "xml", "xlsx"}
    ]
    missing_evidence = sorted(
        str(path.relative_to(root))
        for path in files
        if str(path.relative_to(root)) not in role_evidence
    )
    if missing_evidence:
        return _base_fail_closed(
            root,
            "source_role_candidate_evidence_missing_for_surface",
            missing_role_evidence_surfaces=missing_evidence,
            source_role_candidate_evidence_status="PASS",
        )

    surfaces = [
        inventory(path, root, role_evidence[str(path.relative_to(root))])
        for path in sorted(files, key=lambda item: item.name.lower())
    ]
    found = {
        (surface["source_file_role"], surface["source_format"])
        for surface in surfaces
    }
    missing = sorted(f"{role}.{fmt}" for role, fmt in EXPECTED - found)
    unexpected = sorted(f"{role}.{fmt}" for role, fmt in found - EXPECTED)
    status = "FAIL_CLOSED" if missing else ("DEGRADED" if unexpected else "PASS")

    return {
        "manifest_id": "canonical_ingest_surface_manifest_v1",
        "status": status,
        "match_dir": str(root),
        "surface_file_count": len(surfaces),
        "expected_surface_count": len(EXPECTED),
        "missing_expected_surfaces": missing,
        "unexpected_surfaces": unexpected,
        "surfaces": surfaces,
        "source_role_candidate_evidence_status": "PASS",
        "source_role_candidate_admission_policy": "CONTENT_EVIDENCE_ONLY",
        "source_role_candidate_content_binding": "SHA256_EXACT",
        "filename_support_used_for_admission": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "event_count_policy": "canonical_event_count_requires_later_validation",
        "claim_safety": "EVIDENCE_ONLY",
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "report_language_allowed": False,
        "production_binding_allowed": False,
        "production_release": False,
    }


def write_manifest(
    match_dir: str,
    out: str,
    role_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = build_manifest(match_dir, role_report=role_report)
    out_path = Path(out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="HPFA ACTIVE_MATCH surface manifest v1")
    parser.add_argument("match_dir")
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--role-evidence",
        help="JSON output from content_source_role_resolver_lite; omission fails closed.",
    )
    args = parser.parse_args()
    role_report = None
    if args.role_evidence:
        role_report = json.loads(
            Path(args.role_evidence).expanduser().read_text(encoding="utf-8")
        )
    result = write_manifest(args.match_dir, args.out, role_report=role_report)
    print(
        json.dumps(
            {
                "status": result["status"],
                "out": args.out,
                "surface_file_count": result.get("surface_file_count", 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
