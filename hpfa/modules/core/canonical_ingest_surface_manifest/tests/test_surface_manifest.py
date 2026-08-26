from pathlib import Path
import csv
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
sys.path.insert(0, str(SRC))

from surface_manifest import build_manifest, write_manifest


def write_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"])
        writer.writerow(["1", "1", "2", "c", "A", "Passes accurate", "1", "20", "30"])


def write_xml(path: Path) -> None:
    path.write_text(
        "<root><instance><ID>1</ID><start>1</start><end>2</end></instance></root>",
        encoding="utf-8",
    )


def write_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "")
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            "<worksheet><sheetData><row r='1'/><row r='2'/></sheetData></worksheet>",
        )


def make_surface_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for stem in ("Players", "Teams", "Goalkeepers"):
        write_csv(root / f"{stem}.csv")
        write_xml(root / f"{stem}.xml")
    write_xlsx(root / "Players.xlsx")
    write_xlsx(root / "Goalkeepers.xlsx")
    return root


def role_report(root: Path, *, unresolved: str | None = None) -> dict:
    roles = {
        "Players.csv": "PLAYER_SURFACE_CANDIDATE",
        "Players.xml": "PLAYER_SURFACE_CANDIDATE",
        "Players.xlsx": "PLAYER_SURFACE_CANDIDATE",
        "Teams.csv": "TEAM_SURFACE_CANDIDATE",
        "Teams.xml": "TEAM_SURFACE_CANDIDATE",
        "Goalkeepers.csv": "GOALKEEPER_SURFACE_CANDIDATE",
        "Goalkeepers.xml": "GOALKEEPER_SURFACE_CANDIDATE",
        "Goalkeepers.xlsx": "GOALKEEPER_SURFACE_CANDIDATE",
    }
    files = []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() not in {".csv", ".xml", ".xlsx"}:
            continue
        candidate = roles[path.name]
        status = "ROLE_CANDIDATE_ADMITTED"
        reasons = ["CONTENT_SEMANTIC_ROLE_MARKER"]
        if path.name == unresolved:
            candidate = "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
            status = "REVIEW_REQUIRED"
            reasons = ["CONTENT_ROLE_EVIDENCE_CONFLICT"]
        files.append(
            {
                "relative_path": path.name,
                "role_resolution_applicable": True,
                "resolution": {
                    "resolution_status": status,
                    "resolved_source_role": candidate,
                    "resolution_reasons": reasons,
                },
            }
        )
    unresolved_count = 1 if unresolved else 0
    return {
        "status": "REVIEW_REQUIRED" if unresolved else "PASS",
        "input_root": str(root.resolve()),
        "claim_ceiling": "SOURCE_ROLE_CANDIDATE_ONLY",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "unresolved_role_file_count": unresolved_count,
        "files": files,
    }


def test_manifest_passes_expected_surface_family_from_candidate_evidence(tmp_path):
    root = make_surface_dir(tmp_path)
    manifest = build_manifest(str(root), role_report=role_report(root))
    assert manifest["status"] == "PASS"
    assert manifest["surface_file_count"] == 8
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["true_action_count"] == "UNKNOWN"
    assert manifest["claim_safety"] == "EVIDENCE_ONLY"
    assert manifest["source_role_candidate_admission_policy"] == "CONTENT_EVIDENCE_ONLY"
    assert manifest["filename_support_used_for_admission"] is False
    assert manifest["production_release"] is False

    roles = {(surface["source_file_role"], surface["source_format"]) for surface in manifest["surfaces"]}
    assert ("players", "csv") in roles
    assert ("teams", "xml") in roles
    assert ("goalkeepers", "xlsx") in roles
    assert all(surface["filename_support_used_for_admission"] is False for surface in manifest["surfaces"])


def test_manifest_without_role_evidence_fails_closed(tmp_path):
    root = make_surface_dir(tmp_path)
    manifest = build_manifest(str(root))
    assert manifest["status"] == "FAIL_CLOSED"
    assert manifest["reason"] == "source_role_candidate_evidence_rejected"
    assert "source_role_candidate_evidence_required" in manifest["source_role_candidate_evidence_errors"]


def test_unresolved_or_conflicting_role_evidence_fails_closed(tmp_path):
    root = make_surface_dir(tmp_path)
    report = role_report(root, unresolved="Players.csv")
    manifest = build_manifest(str(root), role_report=report)
    assert manifest["status"] == "FAIL_CLOSED"
    assert manifest["reason"] == "source_role_candidate_evidence_rejected"
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["true_action_count"] == "UNKNOWN"
    assert manifest["production_release"] is False


def test_xlsx_is_aggregate_surface_not_event_surface(tmp_path):
    root = make_surface_dir(tmp_path)
    manifest = build_manifest(str(root), role_report=role_report(root))
    xlsx = [surface for surface in manifest["surfaces"] if surface["source_format"] == "xlsx"]
    assert xlsx
    assert all(surface["aggregate_surface"] is True for surface in xlsx)
    assert all(surface["event_surface_candidate"] is False for surface in xlsx)
    assert all(surface["canonical_event_count"] == "UNKNOWN" for surface in xlsx)


def test_missing_surface_fails_closed(tmp_path):
    write_csv(tmp_path / "Players.csv")
    report = role_report(tmp_path)
    manifest = build_manifest(str(tmp_path), role_report=report)
    assert manifest["status"] == "FAIL_CLOSED"
    assert "teams.csv" in manifest["missing_expected_surfaces"]
    assert "goalkeepers.xlsx" in manifest["missing_expected_surfaces"]


def test_write_manifest(tmp_path):
    root = make_surface_dir(tmp_path / "raw")
    out = tmp_path / "manifest.json"
    result = write_manifest(str(root), str(out), role_report=role_report(root))
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert saved["surface_file_count"] == 8
    assert saved["canonical_event_count"] == "UNKNOWN"
    assert saved["true_action_count"] == "UNKNOWN"
    assert saved["production_release"] is False
