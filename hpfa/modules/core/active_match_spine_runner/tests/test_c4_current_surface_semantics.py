import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import full_spine_runner
from hpfa.modules.core.composite_evidence_packet_builder_lite.src.composite_evidence_packet_builder import build_composite_packet


def _packet():
    return build_composite_packet({
        "packet_family": "sequence",
        "input_features": [{"feature_id": "feature_generic_001", "source_surface": "feature_surface"}],
        "input_windows": [{"window_id": "window_generic_001", "source_surface": "window_surface"}],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": [{"signal_id": "signal_generic_001", "source_surface": "signal_surface"}],
        "contradicting_signals": [],
        "claim_ceiling": "composite_candidate_only",
    })


def _episode_pass(_input_dir, _output_dir, _execution_root):
    return {
        "status": "SMOKE_PASS",
        "episode_candidate_count": 1,
        "episode_feature_vector_count": 1,
        "temporal_episode_signature_status": "SMOKE_PASS",
        "temporal_episode_signature_count": 1,
        "shared_foundation_reused": True,
        "context_episode_feature_lane_executed": True,
        "context_episode_feature_lane_completed": True,
        "temporal_episode_signature_executed": True,
        "row_nucleus_recomputed_by_episode_lane": False,
        "current_invocation_artifacts": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_failed_c4_is_executed_but_not_current_analyst_surface(tmp_path, monkeypatch):
    execution_root = tmp_path / "checkout"
    active_match = execution_root / "runtime" / "active_single_match" / "current"
    active_match.mkdir(parents=True)
    out_dir = tmp_path / "out"
    packet = _packet()

    def fake_bridge(_input_dir, output_dir):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        packet_path = output / "composite_evidence_packet_builder_lite_v1.json"
        packet_path.write_text(json.dumps({
            "module_id": "composite_evidence_packet_builder_lite_v1",
            "status": "SMOKE_PASS",
            "packet_count": 1,
            "blocked_packet_count": 0,
            "packets": [packet],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }), encoding="utf-8")
        return {
            "status": "SMOKE_PASS",
            "match_surface_binding_id": "msb_generic",
            "current_invocation_artifacts": [str(packet_path)],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    def failed_chain(_packet):
        return {
            "packet": _packet,
            "fusion": {
                "status": "FAIL_CLOSED",
                "decision": "BLOCK_FUSION",
                "hard_block_hits": ["synthetic_fusion_failure"],
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            },
        }

    monkeypatch.setattr(full_spine_runner, "run_intelligence_chain", failed_chain)
    report = full_spine_runner.run_full_spine(
        active_match_dir=active_match,
        out_dir=out_dir,
        execution_root=execution_root,
        bridge_runner=fake_bridge,
        episode_runner=_episode_pass,
    )

    assert report["status"] == "FAIL_CLOSED"
    evidence = report["engineering_evidence"]
    assert evidence["current_c4_producers_executed"] is True
    assert evidence["current_c4_producers_reused"] is False
    assert report["analyst_evidence"]["safe_report_language_only"] is False
    assert report["analyst_evidence"]["counterevidence_preserved_by_current_c4_chain"] is False
    assert report["completed_intelligence_chain_count"] == 0
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
