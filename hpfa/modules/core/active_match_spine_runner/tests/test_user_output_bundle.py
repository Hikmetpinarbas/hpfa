import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import user_output_bundle
from user_output_bundle import (
    ANALYST_REPORT,
    BUNDLE_MANIFEST,
    BUNDLE_ZIP,
    build_analyst_report,
    snapshot_output_state,
    write_standard_user_outputs,
)


def _feature_payload():
    return {
        "module_id": "episode_feature_vector_lite_v1",
        "status": "REVIEW_REQUIRED",
        "episode_feature_vector_count": 2,
        "total_eligible_action_candidate_count": 30,
        "eligible_action_family_candidate_counts": {"PASS": 20, "SHOT": 4, "TURNOVER": 3, "RECOVERY": 3},
        "review_debt_feature_vector_count": 1,
        "total_unresolved_semantics_context_count": 2,
        "episode_feature_vectors": [
            {
                "start_second_candidate": 60,
                "end_second_candidate": 120,
                "eligible_action_candidate_count": 10,
                "shot_candidate_count": 1,
                "turnover_candidate_count": 1,
                "recovery_candidate_count": 1,
                "eligible_action_count_by_team_candidate": {"Team A": 7},
                "unknown_team_eligible_action_count": 3,
                "eligible_action_zone_counts": {"MIDDLE_THIRD": 6, "FINAL_THIRD": 4},
                "eligible_action_channel_counts": {"LEFT": 5, "CENTRE": 5},
                "action_family_counts": {"PASS": 7, "SHOT": 1, "TURNOVER": 1, "RECOVERY": 1},
            },
            {
                "start_second_candidate": 300,
                "end_second_candidate": 360,
                "eligible_action_candidate_count": 20,
                "shot_candidate_count": 3,
                "turnover_candidate_count": 2,
                "recovery_candidate_count": 2,
                "eligible_action_count_by_team_candidate": {"Team A": 5, "Team B": 10},
                "unknown_team_eligible_action_count": 5,
                "eligible_action_zone_counts": {"FINAL_THIRD": 12, "MIDDLE_THIRD": 8},
                "eligible_action_channel_counts": {"RIGHT": 12, "CENTRE": 8},
                "action_family_counts": {"PASS": 13, "SHOT": 3, "TURNOVER": 2, "RECOVERY": 2},
            },
        ],
    }


def _full_spine(*, feature_current=True, c4_current=True, status="REVIEW_REQUIRED"):
    return {
        "status": status,
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED" if status != "FAIL_CLOSED" else "BLOCK_FULL_SPINE",
        "episode_candidate_count": 2 if feature_current else None,
        "episode_feature_vector_count": 2 if feature_current else None,
        "temporal_episode_signature_count": 2 if feature_current else None,
        "intelligence_chain_count": 1 if c4_current else 0,
        "hard_block_hits": [] if status != "FAIL_CLOSED" else ["synthetic_failure"],
        "review_hits": ["synthetic_review"] if status != "FAIL_CLOSED" else [],
        "active_match_authority": "/runtime/active_single_match/current",
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": feature_current,
            "current_c4_producers_reused": c4_current,
        },
        "intelligence_chains": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "Gorunur kanit grafigi aday okumayi destekler."
                }
            }
        ] if c4_current else [],
    }


def test_analyst_report_uses_current_episode_surface(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(tmp_path, _full_spine())
    assert "eligible_action_candidate_total=30" in text
    assert "05:00-06:00 shots=3" in text
    assert '"Team A": 12' in text
    assert '"Team B": 10' in text
    assert "SAFE_ARGUMENT_CANDIDATES" in text
    assert "feature_surface_current_invocation=true" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_fail_closed_report_does_not_consume_stale_feature_artifact(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(
        tmp_path,
        _full_spine(feature_current=False, c4_current=False, status="FAIL_CLOSED"),
    )
    assert "feature_surface_current_invocation=false" in text
    assert "eligible_action_candidate_total=UNAVAILABLE_CURRENT_INVOCATION" in text
    assert "05:00-06:00 shots=3" not in text
    assert "onceki run artifact'i kullanilmadi" in text
    assert "Current invocation Episode Feature yuzeyi tamamlanmadi" in text


def test_bundle_uses_pre_run_fingerprints_not_mtime(tmp_path):
    stale = tmp_path / "stale_previous_run.txt"
    stale.write_text("stale", encoding="utf-8")
    unchanged = tmp_path / "unchanged_previous_run.json"
    unchanged.write_text("same", encoding="utf-8")
    before = snapshot_output_state(tmp_path)

    current = tmp_path / "current_run.json"
    current.write_text("{}", encoding="utf-8")
    unchanged.write_text("same", encoding="utf-8")
    (tmp_path / "active_match_full_spine_v1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "active_match_full_spine_v1.txt").write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )

    result = write_standard_user_outputs(tmp_path, _full_spine(), before_state=before)
    assert Path(result["analyst_report"]).name == ANALYST_REPORT
    assert Path(result["bundle_zip"]).name == BUNDLE_ZIP
    assert Path(result["bundle_manifest"]).name == BUNDLE_MANIFEST

    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
    assert "current_run.json" in names
    assert "episode_feature_vector_lite_v1.json" in names
    assert "active_match_full_spine_v1.json" in names
    assert "active_match_full_spine_v1.txt" in names
    assert ANALYST_REPORT in names
    assert BUNDLE_MANIFEST in names
    assert "stale_previous_run.txt" not in names
    assert "unchanged_previous_run.json" not in names

    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["bundle_scope"] == "CURRENT_INVOCATION_CORE_PLUS_NEW_OR_CONTENT_CHANGED_ARTIFACTS"
    assert manifest["selection_basis"] == "PRE_RUN_NAME_AND_SHA256_SNAPSHOT_PLUS_EXPLICIT_CURRENT_CORE_OUTPUTS"
    assert manifest["feature_surface_current_invocation"] is True
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["production_release"] is False


def test_atomic_zip_publication_never_exposes_partial_new_bundle(tmp_path, monkeypatch):
    old_zip = tmp_path / BUNDLE_ZIP
    with zipfile.ZipFile(old_zip, "w") as archive:
        archive.writestr("old.txt", "old-valid-bundle")
    before_old = old_zip.read_bytes()

    (tmp_path / "active_match_full_spine_v1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "active_match_full_spine_v1.txt").write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    before = snapshot_output_state(tmp_path)
    (tmp_path / "current_run.json").write_text("new", encoding="utf-8")

    real_zipfile = user_output_bundle.zipfile.ZipFile

    class BrokenZipFile:
        def __init__(self, *args, **kwargs):
            self._inner = real_zipfile(*args, **kwargs)
        def __enter__(self):
            self._inner.__enter__()
            return self
        def __exit__(self, *args):
            return self._inner.__exit__(*args)
        def write(self, *args, **kwargs):
            self._inner.write(*args, **kwargs)
            raise OSError("synthetic archive failure")

    monkeypatch.setattr(user_output_bundle.zipfile, "ZipFile", BrokenZipFile)
    with pytest.raises(OSError):
        write_standard_user_outputs(tmp_path, _full_spine(feature_current=False), before_state=before)

    assert old_zip.read_bytes() == before_old
    assert not (tmp_path / f".{BUNDLE_ZIP}.tmp").exists()
