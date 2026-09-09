from pathlib import Path


def test_professional_story_runner_requires_reconstruction_before_process() -> None:
    root = Path(__file__).resolve().parents[5]
    source = (root / "active_match_professional_story_run_v1.py").read_text(encoding="utf-8")

    base_call = source.index('"active_match_full_run.py"')
    reconstruction_call = source.index('"reconstruction_intelligence_packet_adapter_current_v1.py"')
    process_call = source.index('"reciprocal_process_chain_current_v1.py"')
    story_call = source.index("write_process_story_sidecar(out_dir)")

    assert base_call < reconstruction_call < process_call < story_call
    assert source.count('"--input-dir",\n                str(match_dir)') >= 2
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
