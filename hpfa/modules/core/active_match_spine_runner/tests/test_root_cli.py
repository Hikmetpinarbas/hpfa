import json
import subprocess
import sys
import zipfile
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[5]
CLI = PRODUCT_ROOT / "active_match_spine_runner.py"


def _write_csv(path: Path) -> None:
    path.write_text("id,x,y\n1,10,20\n", encoding="utf-8")


def _write_xml(path: Path) -> None:
    path.write_text("<root><instance/><instance/></root>", encoding="utf-8")


def _write_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            "<worksheet><sheetData><row/><row/></sheetData></worksheet>",
        )


def _make_active_match(execution_root: Path) -> Path:
    match = execution_root / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    _write_csv(match / "Players.csv")
    _write_csv(match / "Teams.csv")
    _write_csv(match / "Goalkeepers.csv")
    _write_xml(match / "Players.xml")
    _write_xml(match / "Teams.xml")
    _write_xml(match / "Goalkeepers.xml")
    _write_xlsx(match / "Players.xlsx")
    _write_xlsx(match / "Goalkeepers.xlsx")
    return match


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=PRODUCT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_cli_accepts_explicit_execution_root_separate_from_product_root(tmp_path):
    execution_root = tmp_path / "selected_runtime_root"
    active_match = _make_active_match(execution_root)
    out_dir = tmp_path / "HPFA"

    assert execution_root.resolve() != PRODUCT_ROOT.resolve()

    completed = _run_cli(
        str(active_match),
        "--out-dir",
        str(out_dir),
        "--execution-root",
        str(execution_root),
    )

    assert completed.returncode == 0, completed.stderr
    cli_payload = json.loads(completed.stdout)
    assert cli_payload["status"] == "PASS"

    result = json.loads(
        (out_dir / "active_match_spine_check_v1.json").read_text(encoding="utf-8")
    )
    assert result["active_match_authority_validated"] is True
    assert result["execution_root"] == str(execution_root.resolve())
    assert result["active_match_dir"] == str(active_match.resolve())
    assert result["production_binding_allowed"] is False


def test_root_cli_rejects_wrong_execution_root_for_valid_same_suffix_candidate(tmp_path):
    selected_execution_root = tmp_path / "selected_runtime_root"
    wrong_execution_root = tmp_path / "reflection_runtime_root"
    active_match = _make_active_match(selected_execution_root)
    _make_active_match(wrong_execution_root)
    out_dir = tmp_path / "HPFA"

    completed = _run_cli(
        str(active_match),
        "--out-dir",
        str(out_dir),
        "--execution-root",
        str(wrong_execution_root),
    )

    assert completed.returncode != 0
    assert "runtime_authority_root_binding_mismatch" in completed.stderr
    assert not (out_dir / "active_match_spine_check_v1.json").exists()


def test_root_cli_omitted_execution_root_defaults_to_product_root_without_discovery(tmp_path):
    external_execution_root = tmp_path / "external_runtime_root"
    active_match = _make_active_match(external_execution_root)
    out_dir = tmp_path / "HPFA"

    completed = _run_cli(
        str(active_match),
        "--out-dir",
        str(out_dir),
    )

    assert completed.returncode != 0
    assert "runtime_authority_root_binding_mismatch" in completed.stderr
    assert str((PRODUCT_ROOT / "runtime" / "active_single_match" / "current").resolve()) in completed.stderr
    assert not (out_dir / "active_match_spine_check_v1.json").exists()
