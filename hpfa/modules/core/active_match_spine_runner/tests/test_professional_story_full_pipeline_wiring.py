from pathlib import Path


def test_professional_story_runner_uses_single_canonical_full_spine_orchestrator() -> None:
    root = Path(__file__).resolve().parents[5]
    source = (root / "active_match_professional_story_run_v1.py").read_text(encoding="utf-8")

    assert '"active_match_spine_runner.py"' in source
    assert '"--full-spine"' in source
    assert '"--execution-root"' in source
    assert '"parallel_runtime_engine_created": False' in source
    assert '"reconstruction_intelligence_packet_adapter_current_v1.py"' not in source
    assert '"reciprocal_process_chain_current_v1.py"' not in source
    assert "write_process_story_sidecar" not in source


def test_professional_story_runner_requires_analyst_facing_bundle_artifacts() -> None:
    root = Path(__file__).resolve().parents[5]
    source = (root / "active_match_professional_story_run_v1.py").read_text(encoding="utf-8")

    for artifact in (
        "active_match_full_spine_v1.json",
        "active_match_process_story_sidecar_v1.json",
        "active_match_process_story_sidecar_v1.txt",
        "HPFA_ANALYST_REPORT.txt",
        "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json",
        "HPFA_ACTIVE_MATCH_BUNDLE.zip",
    ):
        assert artifact in source
    assert '"required_analysis_layers_activated": required_analysis_layers_activated' in source
    assert 'return 0 if required_analysis_layers_activated else 2' in source


def test_professional_story_runner_preserves_claim_locks() -> None:
    root = Path(__file__).resolve().parents[5]
    source = (root / "active_match_professional_story_run_v1.py").read_text(encoding="utf-8")

    assert '"canonical_event_count": CANONICAL_EVENT_COUNT' in source
    assert '"true_action_count": TRUE_ACTION_COUNT' in source
    assert '"production_release": False' in source
    assert '"pipeline_is_possession_truth": False' in source
    assert '"pipeline_is_tactical_plan_truth": False' in source
    assert '"professional_story_is_causality_truth": False' in source
