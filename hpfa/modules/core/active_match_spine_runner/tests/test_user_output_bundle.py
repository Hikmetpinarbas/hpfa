import json
import os
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import (
    ANALYST_REPORT,
    BUNDLE_MANIFEST,
    BUNDLE_ZIP,
    build_analyst_report,
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


def _full_spine():
    return {
        "status": "REVIEW_REQUIRED",
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED",
        "episode_candidate_count": 2,
        "episode_feature_vector_count": 2,
        "temporal_episode_signature_count": 2,
        "intelligence_chain_count": 1,
        "hard_block_hits": [],
        "review_hits": ["synthetic_review"],
        "active_match_authority": "/runtime/active_single_match/current",
        "intelligence_chains": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "Gorunur kanit grafigi aday okumayi destekler."
                }
            }
        ],
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
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_bundle_contains_only_current_invocation_files_plus_standard_outputs(tmp_path):
    stale = tmp_path / "stale_previous_run.txt"
    stale.write_text("stale", encoding="utf-8")
    old_ns = time.time_ns() - 10_000_000_000
    os.utime(stale, ns=(old_ns, old_ns))

    start_ns = time.time_ns()
    current = tmp_path / "current_run.json"
    current.write_text("{}", encoding="utf-8")
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )

    result = write_standard_user_outputs(tmp_path, _full_spine(), run_started_ns=start_ns)
    assert Path(result["analyst_report"]).name == ANALYST_REPORT
    assert Path(result["bundle_zip"]).name == BUNDLE_ZIP
    assert Path(result["bundle_manifest"]).name == BUNDLE_MANIFEST

    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        names = set(archive.namelist())
    assert "current_run.json" in names
    assert "episode_feature_vector_lite_v1.json" in names
    assert ANALYST_REPORT in names
    assert BUNDLE_MANIFEST in names
    assert "stale_previous_run.txt" not in names

    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["bundle_scope"] == "FILES_CREATED_OR_REWRITTEN_DURING_CURRENT_INVOCATION"
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["production_release"] is False
