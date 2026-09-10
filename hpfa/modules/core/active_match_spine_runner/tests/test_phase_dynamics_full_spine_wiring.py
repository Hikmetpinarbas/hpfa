from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def test_phase_dynamics_lane_is_wired_into_current_full_spine_sidecars():
    source = Path(sidecars.__file__).read_text(encoding="utf-8")

    assert "run_phase_dynamics_intelligence_lane" in source
    assert "PHASE_DYNAMICS_INPUTS" in source
    assert "phase_dynamics_intelligence_lane_status" in source
    assert "phase_dynamics_intelligence_lane_prerequisite_present" in source
    assert "phase_dynamics_intelligence_lane_missing_inputs" in source
    assert "phase_dynamics_intelligence_lane_prerequisite_missing" in source


def test_phase_dynamics_missing_prerequisites_are_not_silent():
    source = Path(sidecars.__file__).read_text(encoding="utf-8")

    assert '"status": "NOT_EVALUATED_PREREQUISITE_MISSING"' in source
    assert 'review_hits.append("phase_dynamics_intelligence_lane_prerequisite_missing")' in source


def test_phase_dynamics_wiring_preserves_claim_locks():
    source = Path(sidecars.__file__).read_text(encoding="utf-8")

    for token in (
        '"canonical_event_count": "UNKNOWN"',
        '"true_action_count": "UNKNOWN"',
        '"phase_truth": False',
        '"possession_truth": False',
        '"sequence_truth": False',
        '"tactical_truth": False',
        '"production_release": False',
    ):
        assert token in source


def test_no_sample_match_identity_leak():
    source = Path(sidecars.__file__).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Turkey", "Australia", "15.08.2026"):
        assert token not in source
