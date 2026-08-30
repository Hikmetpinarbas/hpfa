import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import run_full_spine, run_intelligence_chain
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import (
    build_composite_packet,
)


def _packet():
    return build_composite_packet(
        {
            "packet_family": "sequence",
            "input_features": [
                {"feature_id": "feature_generic_001", "source_surface": "feature_surface"}
            ],
            "input_windows": [
                {"window_id": "window_generic_001", "source_surface": "window_surface"}
            ],
            "input_sequences": [],
            "input_metrics": [],
            "supporting_signals": [
                {"signal_id": "signal_generic_001", "source_surface": "signal_surface"}
            ],
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
    assert report["engineering_evidence"]["current_context_episode_feature_lane_reused"] is True
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
    assert report["intelligence_chain_count"] == 0


def test_full_spine_preserves_first_episode_failure(tmp_path):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)

    def failed_episode(_input_dir, _output_dir, _execution_root):
        return {
            "module_id": "active_match_episode_lane_adapter_v1",
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["episode_input_rejected"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    def failed_bridge(_input_dir, _output_dir):
        return {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["later_bridge_failure"],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    report = run_full_spine(
        active_match_dir=active_match,
        out_dir=tmp_path / "out",
        execution_root=execution_root,
        bridge_runner=failed_bridge,
        episode_runner=failed_episode,
    )
    assert report["status"] == "FAIL_CLOSED"
    assert report["first_failed_node"] == "episode_lane"
    assert report["first_failed_reason_code"] == "episode_input_rejected"


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
