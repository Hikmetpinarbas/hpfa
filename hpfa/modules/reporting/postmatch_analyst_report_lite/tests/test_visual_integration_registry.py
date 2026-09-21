import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "reporting" / "postmatch_analyst_report_lite" / "src"
sys.path.insert(0, str(SRC))

from postmatch_analyst_report import build_report


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_visual_registry_fails_closed_when_upstream_visual_inputs_absent(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()

    report = build_report(out)
    registry = report["visual_integration_registry"]

    assert registry["status"] == "NOT_EVALUATED"
    assert registry["available_surface_count"] == 0
    assert registry["creates_new_finding"] is False
    assert registry["creates_new_claim"] is False
    assert registry["production_release"] is False
    assert all(s["graph_state"] == "UNOBSERVABLE_OR_NOT_ADMITTED" for s in registry["surfaces"])


def test_visual_registry_binds_governed_surfaces_without_claim_promotion(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()

    write_json(out / "cross_format_reconciliation_lite_v1.json", {
        "claim_ceiling": "CROSS_FORMAT_SURFACE_RECONCILIATION_CANDIDATE_ONLY",
    })
    write_json(out / "safe_finding_admission_projection_v1.json", {
        "safe_finding_admission_decisions": [{"claim_ceiling": "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"}],
    })
    write_json(out / "occurrence_consequence_projection_v1.json", {"status": "REVIEW_REQUIRED"})
    write_json(out / "observable_process_variant_binding_projection_v1.json", {
        "claim_ceiling": "OBSERVED_PROCESS_VARIANT_BINDING_CANDIDATE_ONLY",
    })
    write_json(out / "temporal_episode_signature_lite_v1.json", {
        "claim_ceiling": "TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY",
    })
    write_json(out / "analyst_episode_process_participation_projection_v1.json", {
        "claim_ceiling": "OBSERVED_PROCESS_PARTICIPATION_WITHIN_DEFINED_ELIGIBLE_PROCESS_UNIVERSE",
    })
    write_json(out / "spatial_transition_candidate_lite_v1.json", {
        "claim_ceiling": "VISIBLE_SPATIAL_TRANSITION_CANDIDATE_ONLY",
    })
    write_json(out / "state_transition_dynamics_lite_v1.json", {
        "claim_ceiling": "SEMANTIC_SPATIAL_CONSEQUENCE_ASSOCIATION_ONLY",
    })

    report = build_report(out)
    registry = report["visual_integration_registry"]

    assert registry["status"] == "PASS"
    assert registry["available_surface_count"] == 6
    assert registry["binding_role"] == "DOWNSTREAM_PRESENTATION_ONLY"
    assert registry["creates_new_finding"] is False
    assert registry["creates_new_claim"] is False

    by_id = {s["surface_id"]: s for s in registry["surfaces"]}
    assert by_id["DEPENDENCY_RECONCILIATION"]["claim_ceiling"] == "CROSS_FORMAT_SURFACE_RECONCILIATION_CANDIDATE_ONLY"
    assert by_id["SAFE_FINDING_DISPOSITION"]["claim_ceiling"] == "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
    assert by_id["PROCESS_VARIANT_CONSEQUENCE"]["claim_ceiling"] == "OBSERVED_PROCESS_VARIANT_BINDING_CANDIDATE_ONLY"
    assert by_id["TEMPORAL_EPISODE_CHANGE"]["claim_ceiling"] == "TEMPORAL_EPISODE_CHANGE_CANDIDATES_ONLY"
    assert by_id["PROCESS_PARTICIPATION"]["claim_ceiling"] == "OBSERVED_PROCESS_PARTICIPATION_WITHIN_DEFINED_ELIGIBLE_PROCESS_UNIVERSE"
    assert by_id["SPATIAL_STATE_TRANSITION"]["claim_ceiling"] == {
        "spatial": "VISIBLE_SPATIAL_TRANSITION_CANDIDATE_ONLY",
        "transition": "SEMANTIC_SPATIAL_CONSEQUENCE_ASSOCIATION_ONLY",
    }

    assert "coordinate != tracking" in by_id["SPATIAL_STATE_TRANSITION"]["forbidden_inference"]
    assert "0 EMIT != system failure" in by_id["SAFE_FINDING_DISPOSITION"]["forbidden_inference"]
    assert all(s["creates_new_football_truth"] is False for s in registry["surfaces"])
