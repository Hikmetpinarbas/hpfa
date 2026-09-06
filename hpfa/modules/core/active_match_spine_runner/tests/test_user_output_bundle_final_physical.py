import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import user_output_bundle
from user_output_bundle import BUNDLE_MANIFEST, BUNDLE_ZIP, write_standard_user_outputs


def _full_spine(current_artifacts):
    return {
        "status": "REVIEW_REQUIRED",
        "decision": "TEST",
        "active_match_authority": "runtime/active_single_match/current",
        "current_invocation_artifacts": list(current_artifacts),
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": False,
            "current_c4_producers_reused": False,
        },
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_final_bundle_is_physically_reopened_and_verified_after_atomic_publish(tmp_path: Path):
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}\n", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED\n", encoding="utf-8")

    result = write_standard_user_outputs(
        tmp_path,
        _full_spine([str(full_json), str(full_txt)]),
    )

    final_zip = tmp_path / BUNDLE_ZIP
    assert final_zip.is_file()
    assert final_zip.stat().st_size > 0
    assert result["bundle_physical_verified"] is True
    assert result["bundle_size_bytes"] == final_zip.stat().st_size
    assert result["bundle_sha256"] == user_output_bundle._sha256(final_zip)

    with zipfile.ZipFile(final_zip, "r") as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())

    assert BUNDLE_MANIFEST in names
    assert result["bundle_member_count"] == len(names)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_final_bundle_manifest_is_current_and_inside_verified_archive(tmp_path: Path):
    marker = tmp_path / "current_marker.json"
    marker.write_text('{"current": true}\n', encoding="utf-8")
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}\n", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED\n", encoding="utf-8")

    result = write_standard_user_outputs(
        tmp_path,
        _full_spine([str(marker), str(full_json), str(full_txt)]),
    )

    with zipfile.ZipFile(result["bundle_zip"], "r") as archive:
        manifest = json.loads(archive.read(BUNDLE_MANIFEST))
        names = set(archive.namelist())

    assert "current_marker.json" in names
    assert manifest["selection_basis"] == "PRODUCER_WRITE_LEDGER_NOT_MTIME_OR_CONTENT_CHANGE_HEURISTIC"
    assert manifest["production_release"] is False
