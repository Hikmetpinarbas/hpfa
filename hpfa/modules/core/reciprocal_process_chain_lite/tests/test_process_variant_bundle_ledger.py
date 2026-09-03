from pathlib import Path
import zipfile

import active_match_spine_runner as active_runner
from hpfa.modules.core.reciprocal_process_chain_lite.src.full_spine_packet_bridge import (
    bridge_reciprocal_packets,
)


def test_process_variant_outputs_are_carried_into_full_spine_current_artifact_ledger(tmp_path: Path):
    producer_names = [
        "reciprocal_process_chain_lite_v1.json",
        "reciprocal_process_chain_lite_v1.txt",
        "reciprocal_process_chain_analyst_audit_v1.txt",
        "reciprocal_process_variant_profile_lite_v1.json",
        "reciprocal_process_variant_profile_lite_v1.txt",
        "reciprocal_process_variant_profile_analyst_audit_v1.txt",
    ]

    def reciprocal_runner(_active_match_dir, out_dir):
        root = Path(out_dir)
        outputs = {}
        for index, name in enumerate(producer_names):
            path = root / name
            path.write_text(f"artifact-{index}\n", encoding="utf-8")
            outputs[f"artifact_{index}"] = str(path)
        return {
            "status": "PASS",
            "reciprocal_process_chain_candidate_count": 2,
            "outcome_contrast_candidate_count": 2,
            "different_outcome_analogue_link_count": 2,
            "defeasible_process_finding_inputs": [],
            "defeasible_process_finding_input_count": 0,
            "reciprocal_c4_packet_candidates": [],
            "process_variant_profile_status": "PASS",
            "process_variant_profile_count": 1,
            "repeated_process_variant_profile_count": 1,
            "multi_episode_process_variant_profile_count": 1,
            "single_episode_repeat_risk_profile_count": 0,
            "outcome_variation_profile_count": 1,
            "incomplete_episode_binding_profile_count": 0,
            "outputs": outputs,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    def packet_builder(_candidate):
        raise AssertionError("no packet candidate should be built")

    def intelligence_runner(_packet):
        raise AssertionError("no intelligence chain should be run")

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=reciprocal_runner,
        packet_builder=packet_builder,
        intelligence_runner=intelligence_runner,
    )

    declared = {Path(path).name for path in report["current_invocation_artifacts"]}
    for name in producer_names:
        assert name in declared
    assert "reciprocal_full_spine_packet_bridge_v1.json" in declared
    assert "reciprocal_full_spine_packet_bridge_v1.txt" in declared
    assert report["reciprocal_producer_declared_artifact_count"] == len(producer_names)
    assert report["process_variant_profile_count"] == 1
    assert report["multi_episode_process_variant_profile_count"] == 1
    assert report["outcome_variation_profile_count"] == 1
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_bridge_artifacts_reach_official_standard_bundle(tmp_path: Path):
    profile_names = [
        "reciprocal_process_variant_profile_lite_v1.json",
        "reciprocal_process_variant_profile_lite_v1.txt",
        "reciprocal_process_variant_profile_analyst_audit_v1.txt",
    ]
    bridge_paths = []
    for name in profile_names:
        path = tmp_path / name
        path.write_text("current-run-profile\n", encoding="utf-8")
        bridge_paths.append(str(path))

    full_spine_json = tmp_path / "active_match_full_spine_v1.json"
    full_spine_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_spine_json.write_text("{}\n", encoding="utf-8")
    full_spine_txt.write_text("status=REVIEW_REQUIRED\n", encoding="utf-8")

    result = {
        "status": "REVIEW_REQUIRED",
        "decision": "TEST",
        "active_match_authority": "runtime/active_single_match/current",
        "current_invocation_artifacts": [str(full_spine_json), str(full_spine_txt)],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    bridge = {
        "status": "REVIEW_REQUIRED",
        "current_invocation_artifacts": bridge_paths,
        "claim_output_allowed_count": 0,
    }

    active_runner._merge_current_invocation_artifacts(result, bridge, tmp_path)
    outputs = active_runner.write_standard_user_outputs(tmp_path, result)

    with zipfile.ZipFile(outputs["bundle_zip"]) as archive:
        bundled = set(archive.namelist())

    for name in profile_names:
        assert name in bundled
    assert result["reciprocal_bridge_artifacts_promoted_to_full_spine_ledger_count"] == len(profile_names)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_non_declared_or_nested_artifacts_are_not_admitted(tmp_path: Path):
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_file = nested / "not_admitted.json"
    nested_file.write_text("{}\n", encoding="utf-8")
    missing = tmp_path / "missing.json"

    def reciprocal_runner(_active_match_dir, _out_dir):
        return {
            "status": "PASS",
            "defeasible_process_finding_inputs": [],
            "reciprocal_c4_packet_candidates": [],
            "outputs": {
                "nested": str(nested_file),
                "missing": str(missing),
            },
        }

    report = bridge_reciprocal_packets(
        active_match_dir=tmp_path,
        out_dir=tmp_path,
        reciprocal_runner=reciprocal_runner,
        packet_builder=lambda candidate: candidate,
        intelligence_runner=lambda packet: packet,
    )

    declared = {Path(path).name for path in report["current_invocation_artifacts"]}
    assert "not_admitted.json" not in declared
    assert "missing.json" not in declared
    assert report["reciprocal_producer_declared_artifact_count"] == 0
