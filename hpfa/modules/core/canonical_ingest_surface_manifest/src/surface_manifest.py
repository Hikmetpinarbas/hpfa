#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, zipfile, xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED = {
    ("players", "csv"), ("teams", "csv"), ("goalkeepers", "csv"),
    ("players", "xml"), ("teams", "xml"), ("goalkeepers", "xml"),
    ("players", "xlsx"), ("goalkeepers", "xlsx"),
}
REFERENCE_MARKERS = ("archive", "sample", "reference", "match_tests", "match001", "quarantine")


def source_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return "xlsx" if suffix == "xlsm" else suffix


def source_role(path: Path) -> str:
    name = path.name.lower()
    if "goalkeeper" in name:
        return "goalkeepers"
    if "player" in name:
        return "players"
    if "team" in name:
        return "teams"
    return "unknown"


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return sum(1 for _ in csv.DictReader(f, dialect=dialect))


def xml_instances(path: Path) -> int:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0
    return sum(
        1 for e in root.iter()
        if str(e.tag).split("}")[-1].lower() in {"instance", "event"}
    )


def xlsx_rows(path: Path) -> int:
    try:
        with zipfile.ZipFile(path) as zf:
            names = [
                n for n in zf.namelist()
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            ]
            if not names:
                return 0
            root = ET.fromstring(zf.read(names[0]))
    except Exception:
        return 0
    return sum(
        1 for e in root.iter()
        if str(e.tag).endswith("}row") or str(e.tag) == "row"
    )


def visible_rows(path: Path, fmt: str):
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


def inventory(path: Path, root: Path):
    fmt = source_format(path)
    role = source_role(path)
    return {
        "source_file": path.name,
        "relative_path": str(path.relative_to(root)),
        "source_file_role": role,
        "source_format": fmt,
        "surface_family": surface_family(role, fmt),
        "surface_row_count": visible_rows(path, fmt),
        "canonical_event_count": "UNKNOWN",
        "aggregate_surface": fmt == "xlsx",
        "event_surface_candidate": fmt in {"csv", "xml"},
        "row_count_warning": "surface_row_count_is_not_canonical_event_count",
        "claim_safety": "EVIDENCE_ONLY",
    }


def build_manifest(match_dir: str):
    root = Path(match_dir).expanduser().resolve()
    markers = [m for m in REFERENCE_MARKERS if m in str(root).lower()]
    if markers:
        return {
            "manifest_id": "canonical_ingest_surface_manifest_v1",
            "status": "FAIL_CLOSED",
            "reason": "reference_marker_in_path",
            "markers": markers,
            "match_dir": str(root),
            "surfaces": [],
            "canonical_event_count": "UNKNOWN",
            "claim_safety": "EVIDENCE_ONLY",
        }

    files = [
        p for p in root.iterdir()
        if p.is_file() and source_format(p) in {"csv", "xml", "xlsx"}
    ]
    surfaces = [inventory(p, root) for p in sorted(files, key=lambda x: x.name.lower())]
    found = {(s["source_file_role"], s["source_format"]) for s in surfaces}
    missing = sorted([f"{r}.{f}" for r, f in EXPECTED - found])
    unexpected = sorted([f"{r}.{f}" for r, f in found - EXPECTED])
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
        "canonical_event_count": "UNKNOWN",
        "event_count_policy": "canonical_event_count_requires_later_validation",
        "claim_safety": "EVIDENCE_ONLY",
        "report_language_allowed": False,
        "production_binding_allowed": False,
    }


def write_manifest(match_dir: str, out: str):
    manifest = build_manifest(match_dir)
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
    args = parser.parse_args()
    result = write_manifest(args.match_dir, args.out)
    print(json.dumps({
        "status": result["status"],
        "out": args.out,
        "surface_file_count": result.get("surface_file_count", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
