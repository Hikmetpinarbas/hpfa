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
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"])
        w.writerow(["1", "1", "2", "c", "A", "Passes accurate", "1", "20", "30"])


def write_xml(path: Path) -> None:
    path.write_text(
        "<root><instance><ID>1</ID><start>1</start><end>2</end></instance></root>",
        encoding="utf-8",
    )


def write_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "")
        zf.writestr(
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


def test_manifest_passes_expected_surface_family(tmp_path):
    manifest = build_manifest(str(make_surface_dir(tmp_path)))
    assert manifest["status"] == "PASS"
    assert manifest["surface_file_count"] == 8
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["claim_safety"] == "EVIDENCE_ONLY"

    roles = {(s["source_file_role"], s["source_format"]) for s in manifest["surfaces"]}
    assert ("players", "csv") in roles
    assert ("teams", "xml") in roles
    assert ("goalkeepers", "xlsx") in roles


def test_xlsx_is_aggregate_surface_not_event_surface(tmp_path):
    manifest = build_manifest(str(make_surface_dir(tmp_path)))
    xlsx = [s for s in manifest["surfaces"] if s["source_format"] == "xlsx"]

    assert xlsx
    assert all(s["aggregate_surface"] is True for s in xlsx)
    assert all(s["event_surface_candidate"] is False for s in xlsx)
    assert all(s["canonical_event_count"] == "UNKNOWN" for s in xlsx)


def test_missing_surface_fails_closed(tmp_path):
    write_csv(tmp_path / "Players.csv")
    manifest = build_manifest(str(tmp_path))

    assert manifest["status"] == "FAIL_CLOSED"
    assert "teams.csv" in manifest["missing_expected_surfaces"]
    assert "goalkeepers.xlsx" in manifest["missing_expected_surfaces"]


def test_write_manifest(tmp_path):
    root = make_surface_dir(tmp_path / "raw")
    out = tmp_path / "manifest.json"

    result = write_manifest(str(root), str(out))
    saved = json.loads(out.read_text(encoding="utf-8"))

    assert result["status"] == "PASS"
    assert saved["surface_file_count"] == 8
    assert saved["canonical_event_count"] == "UNKNOWN"
