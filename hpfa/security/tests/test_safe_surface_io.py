from pathlib import Path
import zipfile

from hpfa.security.safe_surface_io import (
    SurfaceSecurityError,
    reject_unsafe_xml_declarations,
    validate_regular_surface_file,
    validate_xlsx_archive,
)


def test_symlink_surface_is_rejected(tmp_path):
    target = tmp_path / "target.csv"
    target.write_text("a\n1\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    link.symlink_to(target)
    try:
        validate_regular_surface_file(link)
    except SurfaceSecurityError as exc:
        assert str(exc) == "surface_symlink_rejected"
    else:
        raise AssertionError("symlink surface was accepted")


def test_xml_doctype_is_rejected(tmp_path):
    path = tmp_path / "events.xml"
    path.write_text("<!DOCTYPE events><events/>", encoding="utf-8")
    try:
        reject_unsafe_xml_declarations(path)
    except SurfaceSecurityError as exc:
        assert str(exc) == "xml_doctype_rejected"
    else:
        raise AssertionError("DOCTYPE was accepted")


def test_invalid_xlsx_zip_is_rejected(tmp_path):
    path = tmp_path / "stats.xlsx"
    path.write_text("not a zip", encoding="utf-8")
    try:
        validate_xlsx_archive(path)
    except SurfaceSecurityError as exc:
        assert str(exc) == "xlsx_invalid_zip"
    else:
        raise AssertionError("invalid XLSX archive was accepted")


def test_small_xlsx_archive_is_accepted(tmp_path):
    path = tmp_path / "stats.xlsx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet><row/></worksheet>")
    validate_xlsx_archive(path)
