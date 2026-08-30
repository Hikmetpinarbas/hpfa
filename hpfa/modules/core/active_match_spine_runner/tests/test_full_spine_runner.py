import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import episode_lane_runner
from full_spine_runner import _first_failure, run_full_spine, run_intelligence_chain
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet


def _packet():
    return build_composite_packet(
        {
            "packet_family": "sequence",
            "input_features": [{"feature_id": "feature_generic_001", "source_surface": "feature_surface"}],
            "input_windows": [{"window_id": "window_generic_001", "source_surface": "window_surface"}],
            "input_sequences": [],
            "input_metrics": [],
            "supporting_signals": [{"signal_id": "signal_generic_001", "source_surface": "signal_surface"}],
            "contradicting_signals": [],
            "claim_ceiling": "composite_candidate_only",
        }
    )


def _episode_pass(_input_dir, _output_dir, _execution_root):
    return {
        "module_id": "active_match_episode_lane_adapter_v1",
        "status": "SMOKE_PASS",
        "episode_candidate_count": 2,
        "episode_feature_vector_count": 2,
        "temporal_episode_signature_status": "SMOKE_PASS",
        "temporal_episode_signature_count": 2,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_full_spine_reuses_current_c4_chain_without_truth_promotion():
    chain = run_intelligence_chain(_packet())
    assert chain["fusion"]["packet_id"] == chain["packet"]["packet_id"]
    assert chain["argument"]["fusion_id"] == chain["fusion"]["fusion_id"]
    assert chain["route"]["argument_id"] == chain["argument"]["argument_id"]
    assert chain["graph"]["route_id"] == chain["route"]["route_id"]
    assert chain["report_block"]["safe_sentence_id"] == chain["safe_sentence"]["safe_sentence_id"]
    assert chain["assembly"]["contract_item_id"] == chain["output_contract"]["contract_item_id"]
    for record in chain.values():
        assert record.get("canonical_event_count") == "UNKNOWN"


def test_c4_stage_exception_is_contracted_into_fail_closed_record():
    def explode(_artifact):
        raise RuntimeError("synthetic")

    chain = run_intelligence_chain(_packet(), stage_overrides={"graph": explode})
    assert chain["graph"]["status"] == "FAIL_CLOSED"
    assert chain["graph"]["hard_block_hits"] == ["c4_stage_exception:graph:RuntimeError"]
    assert "lens" not in chain
    node, reason = _first_failure([chain])
    assert node == "graph"
    assert reason == "c4_stage_exception:graph:RuntimeError"


def test_lens_failure_is_in_first_failure_order_without_rewiring_main_sentence_path():
    def blocked_lens(_artifact):
        return {
            "module_id": "lens_failure_fixture",
            "status": "FAIL_CLOSED",
            "decision": "BLOCK_LENS",
            "hard_block_hits": ["lens_specific_failure"],
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    chain = run_intelligence_chain(_packet(), stage_overrides={"lens": blocked_lens})
    node, reason = _first_failure([chain])
    assert node == "lens"
    assert reason == "lens_specific_failure"
    assert "safe_sentence" in chain
    assert chain["safe_sentence"].get("graph_id") == chain["graph"].get("graph_id")


def test_full_spine_uses_single_active_match_authority_and_flat_outputs(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    out_dir = tmp_path / "out"
    packet = _packet()

    def fake_bridge(input_dir, output_dir):
        assert Path(input_dir).resolve() == active_match.resolve()
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "composite_evidence_packet_builder_lite_v1.json").write_text(
            json.dumps(
                {
                    "module_id": "composite_evidence_packet_builder_lite_v1",
                    "status": "SMOKE_PASS",
                    "packet_count": 1,
                    "blocked_packet_count": 0,
                    "packets": [packet],
                    "canonical_event_count": "UNKNOWN",
                    "production_release": False,
                }
            ),
            encoding="utf-8",
        )
        return {
            "module_id": "reconstruction_intelligence_packet_bridge_current_v1",
            "status": "SMOKE_PASS",
            "match_surface_binding_id": "msb_generic",
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = run_full_spine(
        active_match_dir=active_match,
        out_dir=out_dir,
        execution_root=execution_root,
        bridge_runner=fake_bridge,
        episode_runner=_episode_pass,
    )

    assert report["active_match_authority"] == str(active_match.resolve())
    assert report["episode_candidate_count"] == 2
    assert report["temporal_episode_signature_count"] == 2
    assert report["engineering_evidence"]["single_active_match_authority_validated"] is True
    assert report["engineering_evidence"]["shared_foundation_reused"] is True
    assert report["engineering_evidence"]["row_nucleus_recomputed_by_episode_lane"] is False
    assert report["engineering_evidence"]["c4_stage_exception_containment_enabled"] is True
    assert report["engineering_evidence"]["c4_sidecar_dependency_preserved"] is True
    assert report["engineering_evidence"]["parallel_reasoning_engine_created"] is False
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert (out_dir / "active_match_full_spine_v1.json").is_file()
    assert (out_dir / "active_match_full_spine_v1.txt").is_file()


def test_full_spine_fails_closed_when_bridge_fails(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)

    def failed_bridge(_input_dir, _output_dir):
        return {
            "module_id": "reconstruction_intelligence_packet_bridge_current_v1",
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["synthetic_upstream_failure"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = run_full_spine(
        active_match_dir=active_match,
        out_dir=tmp_path / "out",
        execution_root=execution_root,
        bridge_runner=failed_bridge,
        episode_runner=_episode_pass,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert "reconstruction_intelligence_bridge_fail_closed" in report["hard_block_hits"]
    assert report["first_failed_node"] == "reconstruction_intelligence_bridge"
    assert report["first_failed_reason_code"] == "synthetic_upstream_failure"
    assert report["episode_lane_status"] == "NOT_EVALUATED"
    assert report["intelligence_chain_count"] == 0


def test_full_spine_does_not_run_episode_after_foundation_failure(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)

    def failed_bridge(_input_dir, _output_dir):
        return {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["foundation_failure"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    def should_not_run_episode(_input_dir, _output_dir, _execution_root):
        raise AssertionError("episode lane must not run after shared foundation failure")

    report = run_full_spine(
        active_match_dir=active_match,
        out_dir=tmp_path / "out",
        execution_root=execution_root,
        bridge_runner=failed_bridge,
        episode_runner=should_not_run_episode,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_node"] == "reconstruction_intelligence_bridge"
    assert report["first_failed_reason_code"] == "foundation_failure"


def test_episode_lane_code_root_is_product_checkout_not_selected_execution_root():
    product_root = episode_lane_runner._product_root()
    assert product_root == ROOT
    assert (product_root / "active_match_full_run.py").is_file()


def test_episode_lane_preserves_first_failed_subprocess_stage(tmp_path, monkeypatch):
    active_match = tmp_path / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    output = tmp_path / "out"
    output.mkdir()
    (output / episode_lane_runner.ROW_NUCLEUS_OUTPUT).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "readable_surface_files",
        lambda _match_dir: [active_match / "surface.csv"],
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_provider_time_context_step",
        lambda *_args, **_kwargs: {
            "command": ["internal:provider_time_semantic_admission_lite_v1"],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        },
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "run_step",
        lambda _root, command: {
            "command": command,
            "returncode": 17,
            "stdout": "",
            "stderr": "synthetic failure",
            "passed": False,
        },
    )
    monkeypatch.setattr(
        episode_lane_runner.current_episode,
        "write_summary",
        lambda *_args, **_kwargs: {"status": "FAIL_CLOSED", "analyst_evidence": {}},
    )

    report = episode_lane_runner.run_current_episode_lane(active_match, output, tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_episode_step"] == {
        "stage": "context_action_semantics_rebind.py",
        "returncode": 17,
        "stderr": "synthetic failure",
    }
    assert report["hard_block_hits"] == [
        "episode_step_failed:context_action_semantics_rebind.py:returncode_17"
    ]


def test_no_sample_match_identity_leak():
    files = [SRC / "full_spine_runner.py", SRC / "episode_lane_runner.py"]
    for source_path in files:
        source = source_path.read_text(encoding="utf-8")
        for token in [
            "Genclerbirligi",
            "Fenerbahce",
            "Sturm Graz",
            "Heart of Midlothian",
            "Turkey",
            "Australia",
            "15.08.2026",
            "22.08.2026",
        ]:
            assert token not in source
