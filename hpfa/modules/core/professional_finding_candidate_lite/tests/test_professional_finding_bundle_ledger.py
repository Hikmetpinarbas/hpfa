from pathlib import Path
import zipfile

import active_match_spine_runner as active_runner
from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import bridge_reciprocal_packets


NEW_PRODUCER_ARTIFACTS = [
    "match_reconciliation_ledger_lite_v2.json",
    "match_reconciliation_ledger_lite_v2.txt",
    "match_reconciliation_ledger_analyst_audit_v2.txt",
    "team_episode_activity_lens_lite_v1.json",
    "team_episode_activity_lens_lite_v1.txt",
    "team_episode_activity_lens_analyst_audit_v1.txt",
    "visible_geometry_lens_lite_v1.json",
    "visible_geometry_lens_lite_v1.txt",
    "visible_geometry_lens_analyst_audit_v1.txt",
    "player_aggregate_process_reconciliation_lite_v1.json",
    "player_aggregate_process_reconciliation_lite_v1.txt",
    "player_aggregate_process_reconciliation_analyst_audit_v1.txt",
    "process_robustness_lens_lite_v1.json",
    "process_robustness_lens_lite_v1.txt",
    "process_robustness_lens_analyst_audit_v1.txt",
    "process_metric_profile_lite_v1.json",
    "process_metric_profile_lite_v1.txt",
    "process_metric_profile_analyst_audit_v1.txt",
    "professional_finding_candidate_lite_v1.json",
    "professional_finding_candidate_lite_v1.txt",
    "professional_finding_candidate_analyst_audit_v1.txt",
]


def _reciprocal_runner(_active_match_dir, out_dir):
    root = Path(out_dir)
    outputs = {}
    for index, name in enumerate(NEW_PRODUCER_ARTIFACTS):
        path = root / name
        path.write_text(f"current-run-{index}\n", encoding="utf-8")
        outputs[f"artifact_{index}"] = str(path)
    return {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "REVIEW_REQUIRED",
        "reciprocal_process_chain_candidate_count": 0,
        "outcome_contrast_candidate_count": 0,
        "different_outcome_analogue_link_count": 0,
        "defeasible_process_finding_inputs": [],
        "defeasible_process_finding_input_count": 0,
        "reciprocal_c4_packet_candidates": [],
        "outputs": outputs,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_all_new_current_run_artifacts_reach_bridge_ledger(tmp_path: Path):
    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=_reciprocal_runner,
        packet_builder=lambda candidate: candidate,
        intelligence_runner=lambda packet: packet,
    )
    declared = {Path(value).name for value in report["current_invocation_artifacts"]}
    for name in NEW_PRODUCER_ARTIFACTS:
        assert name in declared
    assert report["reciprocal_producer_declared_artifact_count"] == len(NEW_PRODUCER_ARTIFACTS)


def test_all_new_current_run_artifacts_reach_official_bundle(tmp_path: Path):
    bridge = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=_reciprocal_runner,
        packet_builder=lambda candidate: candidate,
        intelligence_runner=lambda packet: packet,
    )
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}\n", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED\n", encoding="utf-8")
    result = {
        "status": "REVIEW_REQUIRED",
        "decision": "TEST",
        "active_match_authority": "runtime/active_single_match/current",
        "current_invocation_artifacts": [str(full_json), str(full_txt)],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    active_runner._merge_current_invocation_artifacts(result, bridge, tmp_path)
    outputs = active_runner.write_standard_user_outputs(tmp_path, result)
    with zipfile.ZipFile(outputs["bundle_zip"]) as archive:
        members = set(archive.namelist())
        assert archive.testzip() is None
    for name in NEW_PRODUCER_ARTIFACTS:
        assert name in members
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_only_direct_root_existing_declared_files_enter_bundle(tmp_path: Path):
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_file = nested / "professional_finding_candidate_lite_v1.json"
    nested_file.write_text("{}\n", encoding="utf-8")

    def runner(_active_match_dir, _out_dir):
        return {
            "status": "REVIEW_REQUIRED",
            "defeasible_process_finding_inputs": [],
            "reciprocal_c4_packet_candidates": [],
            "outputs": {"nested": str(nested_file)},
        }

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=runner,
        packet_builder=lambda candidate: candidate,
        intelligence_runner=lambda packet: packet,
    )
    names = {Path(value).name for value in report["current_invocation_artifacts"]}
    assert "professional_finding_candidate_lite_v1.json" not in names
