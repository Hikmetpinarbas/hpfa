import json
import sys
import types
from pathlib import Path

import pytest

from hpfa.modules.core.xlsx_surface_reader_lite.tests.ooxml_fixture import (
    write_xlsx as write_ooxml_xlsx,
)

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
sys.path.insert(0, str(SRC))

import spine_runner as spine_runner_module  # noqa: E402
from spine_runner import (  # noqa: E402
    _boundary_scorer_module,
    _content_source_role_resolver_module,
    _surface_manifest_module,
    run_spine_check,
    validate_active_match_authority,
    validate_output_root,
    validate_runtime_surface,
)


def write_role_csv(path: Path, role: str) -> None:
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


def write_role_xml(path: Path, role: str) -> None:
    if role == "TEAM":
        team_label = ""
        action = "Shots"
        code = "Club - Shots"
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


def write_role_xlsx(path: Path, role: str) -> None:
    if role == "GOALKEEPER":
        sheet_name = "Kaleci verileri"
        rows = [
            ["Player", "Team", "Shots saved", "Goal kicks"],
            ["Alpha", "Club", 4, 8],
        ]
    else:
        sheet_name = "Oyuncuların verileri"
        rows = [
            ["Player", "Team", "Passes accurate", "Dribbles successful"],
            ["Alpha", "Club", 40, 2],
        ]
    write_ooxml_xlsx(path, sheets=[{"name": sheet_name, "rows": rows}])


def make_active_match(execution_root: Path) -> Path:
    match = execution_root / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    write_role_csv(match / "surface_a.csv", "PLAYER")
    write_role_xml(match / "surface_b.xml", "PLAYER")
    write_role_xlsx(match / "surface_c.xlsx", "PLAYER")
    write_role_csv(match / "surface_d.csv", "TEAM")
    write_role_xml(match / "surface_e.xml", "TEAM")
    write_role_csv(match / "surface_f.csv", "GOALKEEPER")
    write_role_xml(match / "surface_g.xml", "GOALKEEPER")
    write_role_xlsx(match / "surface_h.xlsx", "GOALKEEPER")
    return match


def make_registry(tmp_path: Path) -> Path:
    registry = tmp_path / "composite_registry.json"
    registry.write_text(json.dumps([
        {
            "composite_id": "COMP-SPINE-RUNNER",
            "dominant_capability": "canonical_ingest",
            "source_count": 4,
            "sources": ["TERMUX", "GITHUB"],
            "active_match_validation_required": True,
            "members": [
                {
                    "file_name": "canonical_ingest.py",
                    "normalized_name": "canonical_ingest",
                    "source_path": "/tmp/canonical_ingest.py",
                    "symbols": ["def:run"],
                    "dependency_flags": [],
                }
            ],
        }
    ]), encoding="utf-8")
    return registry


def test_spine_runner_writes_flat_json_and_txt_outputs(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    match = make_active_match(execution_root)
    registry = make_registry(tmp_path)
    out = tmp_path / "HPFA"

    result = run_spine_check(
        match,
        out,
        composite_registry=registry,
        root=ROOT,
        execution_root=execution_root,
    )

    assert result["status"] == "PASS"
    assert result["active_match_authority_validated"] is True
    assert result["execution_root"] == str(execution_root.resolve())
    assert result["active_match_root_binding_policy"] == "DIRECT_EXECUTION_ROOT_RUNTIME_ACTIVE_SINGLE_MATCH_CURRENT"
    assert result["source_role_resolution"]["status"] == "PASS"
    assert result["source_role_resolution"]["supported_file_count"] == 8
    assert result["source_role_resolution"]["role_candidate_admitted_file_count"] == 8
    assert result["source_role_resolution"]["unresolved_role_file_count"] == 0
    assert result["source_role_resolution"]["resolved_role_counts"] == {
        "GOALKEEPER_SURFACE_CANDIDATE": 3,
        "PLAYER_SURFACE_CANDIDATE": 3,
        "TEAM_SURFACE_CANDIDATE": 2,
    }
    assert result["source_role_resolution"]["filename_support_used_for_admission"] is False
    assert result["source_role_resolution"]["validated_team_identity"] is False
    assert result["source_role_resolution"]["validated_player_identity"] is False
    assert result["source_role_resolution"]["validated_event_identity"] is False
    assert result["surface_manifest"]["status"] == "PASS"
    assert result["surface_manifest"]["surface_file_count"] == 8
    assert result["surface_manifest"]["source_role_candidate_evidence_status"] == "PASS"
    assert result["surface_manifest"]["source_role_candidate_admission_policy"] == "CONTENT_EVIDENCE_ONLY"
    assert result["surface_manifest"]["filename_support_used_for_admission"] is False
    assert result["surface_manifest"]["report_language_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["production_binding_allowed"] is False
    assert result["boundary_scores"]["score_count"] == 1
    assert result["runtime_surface_policy"]["executed_runtime_surfaces"] == [
        "hpfa/modules/core/content_source_role_resolver_lite",
        "hpfa/modules/core/canonical_ingest_surface_manifest",
        "hpfa/modules/core/composite_integration_office",
    ]
    assert result["runtime_surface_policy"]["authority_symlinks_allowed"] is False
    assert result["runtime_surface_policy"]["resolved_authority_must_remain_within_execution_root"] is True
    assert result["runtime_surface_policy"]["reflection_authority_allowed"] is False
    assert result["runtime_surface_policy"]["unregistered_runtime_surface_allowed"] is False
    assert result["runtime_surface_policy"]["donor_runtime_binding_allowed"] is False

    assert (out / "active_match_surface_manifest_v1.json").exists()
    assert (out / "boundary_analysis_score_registry_v1.json").exists()
    assert (out / "active_match_spine_check_v1.json").exists()
    assert (out / "active_match_spine_check_v1.txt").exists()
    assert not any(path.is_dir() for path in out.iterdir())


def test_neutral_filenames_are_admitted_only_by_content_role_candidates(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    match = make_active_match(execution_root)
    out = tmp_path / "HPFA"
    forbidden_filename_terms = ("players", "teams", "goalkeepers")
    assert len(list(match.iterdir())) == 8
    assert all(
        not any(term in path.name.casefold() for term in forbidden_filename_terms)
        for path in match.iterdir()
    )

    result = run_spine_check(match, out, root=ROOT, execution_root=execution_root)
    assert result["status"] == "PASS"
    assert result["source_role_resolution"]["resolved_role_counts"] == {
        "GOALKEEPER_SURFACE_CANDIDATE": 3,
        "PLAYER_SURFACE_CANDIDATE": 3,
        "TEAM_SURFACE_CANDIDATE": 2,
    }
    manifest = json.loads(
        (out / "active_match_surface_manifest_v1.json").read_text(encoding="utf-8")
    )
    assert manifest["filename_support_used_for_admission"] is False
    assert all(surface["filename_support_used_for_admission"] is False for surface in manifest["surfaces"])
    assert all(surface["source_role_resolution_status"] == "ROLE_CANDIDATE_ADMITTED" for surface in manifest["surfaces"])
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["true_action_count"] == "UNKNOWN"
    assert manifest["validated_team_identity"] is False
    assert manifest["validated_player_identity"] is False
    assert manifest["validated_event_identity"] is False
    assert manifest["production_release"] is False


def test_spine_runner_can_skip_boundary_scores(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    match = make_active_match(execution_root)
    out = tmp_path / "HPFA"

    result = run_spine_check(
        match,
        out,
        root=ROOT,
        execution_root=execution_root,
    )

    assert result["status"] == "PASS"
    assert result["boundary_scores"] is None
    assert result["runtime_surface_policy"]["executed_runtime_surfaces"] == [
        "hpfa/modules/core/content_source_role_resolver_lite",
        "hpfa/modules/core/canonical_ingest_surface_manifest",
    ]
    summary = (out / "active_match_spine_check_v1.txt").read_text(encoding="utf-8")
    assert "execution_root=" in summary
    assert "active_match_root_binding_policy=DIRECT_EXECUTION_ROOT_RUNTIME_ACTIVE_SINGLE_MATCH_CURRENT" in summary
    assert "[source_role_resolution]" in summary
    assert "filename_support_used_for_admission=False" in summary
    assert "canonical_event_count=UNKNOWN" in summary
    assert "true_action_count=UNKNOWN" in summary
    assert "production_release=False" in summary
    assert "[runtime_surface_policy]" in summary
    assert "[boundary_scores]" in summary
    assert "status=SKIPPED" in summary


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_output_root("/sdcard/Download/HPFA/spine-run")


def test_phone_output_root_is_allowed():
    assert str(validate_output_root("/sdcard/Download/HPFA")).endswith("/Download/HPFA")


def test_active_match_authority_is_directly_bound_to_selected_execution_root(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    match = make_active_match(execution_root)
    assert validate_active_match_authority(match, execution_root) == match.resolve()

    wrong = execution_root / "runtime" / "some_other_match" / "current"
    wrong.mkdir(parents=True)
    with pytest.raises(ValueError, match="runtime_authority_path_invalid"):
        validate_active_match_authority(wrong, execution_root)


def test_runtime_symlink_to_other_checkout_is_rejected(tmp_path):
    selected_root = tmp_path / "selected_checkout"
    other_root = tmp_path / "other_checkout"
    make_active_match(other_root)
    selected_root.mkdir()
    (selected_root / "runtime").symlink_to(other_root / "runtime", target_is_directory=True)

    candidate = selected_root / "runtime" / "active_single_match" / "current"
    with pytest.raises(ValueError, match="runtime_authority_symlink_rejected"):
        validate_active_match_authority(candidate, selected_root)


def test_active_single_match_symlink_to_external_reflection_is_rejected(tmp_path):
    selected_root = tmp_path / "selected_checkout"
    other_root = tmp_path / "other_checkout"
    make_active_match(other_root)
    (selected_root / "runtime").mkdir(parents=True)
    (selected_root / "runtime" / "active_single_match").symlink_to(
        other_root / "runtime" / "active_single_match",
        target_is_directory=True,
    )

    candidate = selected_root / "runtime" / "active_single_match" / "current"
    with pytest.raises(ValueError, match="runtime_authority_symlink_rejected"):
        validate_active_match_authority(candidate, selected_root)


def test_current_symlink_to_external_reflection_is_rejected(tmp_path):
    selected_root = tmp_path / "selected_checkout"
    other_root = tmp_path / "other_checkout"
    external_current = make_active_match(other_root)
    (selected_root / "runtime" / "active_single_match").mkdir(parents=True)
    (selected_root / "runtime" / "active_single_match" / "current").symlink_to(
        external_current,
        target_is_directory=True,
    )

    candidate = selected_root / "runtime" / "active_single_match" / "current"
    with pytest.raises(ValueError, match="runtime_authority_symlink_rejected"):
        validate_active_match_authority(candidate, selected_root)


def test_resolved_authority_escape_is_rejected_even_if_symlink_precheck_is_bypassed(
    monkeypatch,
    tmp_path,
):
    selected_root = tmp_path / "selected_checkout"
    other_root = tmp_path / "other_checkout"
    make_active_match(other_root)
    selected_root.mkdir()
    (selected_root / "runtime").symlink_to(other_root / "runtime", target_is_directory=True)
    candidate = selected_root / "runtime" / "active_single_match" / "current"

    monkeypatch.setattr(spine_runner_module, "_authority_symlink_component", lambda _root: None)
    with pytest.raises(ValueError, match="runtime_authority_resolved_outside_execution_root"):
        validate_active_match_authority(candidate, selected_root)


def test_quarantine_reflection_with_valid_suffix_is_rejected(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    direct = make_active_match(execution_root)
    assert validate_active_match_authority(direct, execution_root) == direct.resolve()

    quarantine_reflection = (
        execution_root
        / "runtime"
        / "quarantine"
        / "active_match_cleanup_20260618_014726"
        / "runtime"
        / "active_single_match"
        / "current"
    )
    quarantine_reflection.mkdir(parents=True)

    with pytest.raises(ValueError, match="runtime_authority_forbidden_ancestry:quarantine"):
        validate_active_match_authority(quarantine_reflection, execution_root)


def test_same_suffix_in_another_checkout_cannot_become_selected_truth(tmp_path):
    selected_root = tmp_path / "selected_checkout"
    reflection_root = tmp_path / "other_checkout"
    selected = make_active_match(selected_root)
    reflected = make_active_match(reflection_root)

    assert validate_active_match_authority(selected, selected_root) == selected.resolve()
    with pytest.raises(ValueError, match="runtime_authority_root_binding_mismatch"):
        validate_active_match_authority(reflected, selected_root)


def test_forbidden_authority_ancestry_rejects_direct_candidate_even_if_root_selected(tmp_path):
    for token in [
        "quarantine",
        "archive",
        "archives",
        "donor",
        "donors",
        "reference_only",
        "fixtures",
    ]:
        contaminated_root = tmp_path / token / "checkout"
        candidate = make_active_match(contaminated_root)
        with pytest.raises(ValueError, match=f"runtime_authority_forbidden_ancestry:{token}"):
            validate_active_match_authority(candidate, contaminated_root)


def test_case_variant_active_match_authority_suffix_is_rejected(tmp_path):
    execution_root = tmp_path / "selected_checkout"
    case_variant = execution_root / "RUNTIME" / "ACTIVE_SINGLE_MATCH" / "CURRENT"
    case_variant.mkdir(parents=True)
    with pytest.raises(ValueError, match="runtime_authority_path_invalid"):
        validate_active_match_authority(case_variant, execution_root)


def test_only_registered_product_runtime_surfaces_are_executable():
    allowed = ROOT / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
    resolver = ROOT / "hpfa" / "modules" / "core" / "content_source_role_resolver_lite" / "src"
    assert validate_runtime_surface(ROOT, allowed) == allowed.resolve()
    assert validate_runtime_surface(ROOT, resolver) == resolver.resolve()

    with pytest.raises(ValueError, match="unregistered_runtime_surface"):
        validate_runtime_surface(ROOT, ROOT / "docs" / "contracts")


def test_archive_donor_reference_and_fixture_runtime_surfaces_fail_closed(tmp_path):
    for relative, error_code in [
        ("archive/legacy.py", "archive_surface_import_attempted"),
        ("donor/engine.py", "donor_surface_runtime_bound"),
        ("reference_only/note.py", "reference_only_surface_executed"),
        ("fixtures/sample.py", "fixture_surface_used_as_active_match"),
    ]:
        candidate = tmp_path / relative
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("pass\n", encoding="utf-8")
        with pytest.raises(ValueError, match=error_code):
            validate_runtime_surface(tmp_path, candidate)


def test_runtime_surface_outside_product_repo_is_rejected(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="runtime_surface_outside_product_repo"):
        validate_runtime_surface(ROOT, outside)


def test_cached_content_role_resolver_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(__file__=str(tmp_path / "content_source_role_resolver.py"))
    monkeypatch.setitem(sys.modules, "content_source_role_resolver", fake)
    with pytest.raises(ValueError, match="runtime_module_origin_mismatch:content_source_role_resolver"):
        _content_source_role_resolver_module(ROOT)


def test_cached_surface_manifest_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(__file__=str(tmp_path / "surface_manifest.py"))
    monkeypatch.setitem(sys.modules, "surface_manifest", fake)
    with pytest.raises(ValueError, match="runtime_module_origin_mismatch:surface_manifest"):
        _surface_manifest_module(ROOT)


def test_cached_boundary_scorer_from_wrong_origin_fails_closed(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(__file__=str(tmp_path / "boundary_analysis_scorer.py"))
    monkeypatch.setitem(sys.modules, "boundary_analysis_scorer", fake)
    with pytest.raises(ValueError, match="runtime_module_origin_mismatch:boundary_analysis_scorer"):
        _boundary_scorer_module(ROOT)
