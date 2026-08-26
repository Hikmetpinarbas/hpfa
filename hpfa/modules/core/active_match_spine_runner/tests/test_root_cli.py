import json
import subprocess
import sys
from pathlib import Path

from hpfa.modules.core.xlsx_surface_reader_lite.tests.ooxml_fixture import (
    write_xlsx as write_ooxml_xlsx,
)


PRODUCT_ROOT = Path(__file__).resolve().parents[5]
CLI = PRODUCT_ROOT / "active_match_spine_runner.py"


def _write_role_csv(path: Path, role: str) -> None:
    if role == "TEAM":
        path.write_text(
            "ID,start,end,code,action,half,pos_x,pos_y\n"
            "1,0.0,1.0,Club - Shots,Shots,1,10.0,20.0\n",
            encoding="utf-8",
        )
        return
    action = "Shots saved" if role == "GOALKEEPER" else "Passes accurate"
    path.write_text(
        "ID,start,end,code,team,action,half,pos_x,pos_y\n"
        f"1,0.0,1.0,Subject - {action},Club,{action},1,10.0,20.0\n",
        encoding="utf-8",
    )


def _write_role_xml(path: Path, role: str) -> None:
    if role == "TEAM":
        action = "Shots"
        code = "Club - Shots"
        team_label = ""
    else:
        action = "Shots saved" if role == "GOALKEEPER" else "Passes accurate"
        code = f"Subject - {action}"
        team_label = "<label><group>Team</group><text>Club</text></label>"
    path.write_text(
        "<root><instance>"
        "<ID>1</ID><start>0</start><end>1</end>"
        f"<code>{code}</code>"
        f"<label><group>Action</group><text>{action}</text></label>"
        "<label><group>Half</group><text>1</text></label>"
        f"{team_label}"
        "<label><group>pos_x</group><text>10</text></label>"
        "<label><group>pos_y</group><text>20</text></label>"
        "</instance></root>",
        encoding="utf-8",
    )


def _write_role_xlsx(path: Path, role: str) -> None:
    if role == "GOALKEEPER":
        name = "Kaleci verileri"
        rows = [
            ["Player", "Team", "Shots saved", "Goal kicks"],
            ["Alpha", "Club", 4, 8],
        ]
    else:
        name = "Oyuncuların verileri"
        rows = [
            ["Player", "Team", "Passes accurate", "Dribbles successful"],
            ["Alpha", "Club", 40, 2],
        ]
    write_ooxml_xlsx(path, sheets=[{"name": name, "rows": rows}])


def _make_active_match(execution_root: Path) -> Path:
    match = execution_root / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    _write_role_csv(match / "surface_a.csv", "PLAYER")
    _write_role_xml(match / "surface_b.xml", "PLAYER")
    _write_role_xlsx(match / "surface_c.xlsx", "PLAYER")
    _write_role_csv(match / "surface_d.csv", "TEAM")
    _write_role_xml(match / "surface_e.xml", "TEAM")
    _write_role_csv(match / "surface_f.csv", "GOALKEEPER")
    _write_role_xml(match / "surface_g.xml", "GOALKEEPER")
    _write_role_xlsx(match / "surface_h.xlsx", "GOALKEEPER")
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
    assert all(
        not any(token in path.name.casefold() for token in ("players", "teams", "goalkeepers"))
        for path in active_match.iterdir()
    )

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
    assert result["source_role_resolution"]["resolved_role_counts"] == {
        "GOALKEEPER_SURFACE_CANDIDATE": 3,
        "PLAYER_SURFACE_CANDIDATE": 3,
        "TEAM_SURFACE_CANDIDATE": 2,
    }
    assert result["source_role_resolution"]["filename_support_used_for_admission"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
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
