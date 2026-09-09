import zipfile
from pathlib import Path

import active_match_professional_story_run_v1 as runner


def _valid_manifest() -> dict:
    return {
        "module_id": runner.BUNDLE_MODULE_ID,
        "analyst_text_requires_final_assembly_admission": True,
        "sequence_lineage_preserved_in_analyst_report": True,
        "sequence_claim_ceiling_revalidated_in_analyst_report": True,
        "sequence_null_context_locks_revalidated_in_analyst_report": True,
        "match_story_lineage_preserved_in_analyst_report": True,
        "match_story_alternative_explanation_lineage_revalidated_in_analyst_report": True,
        "alternative_explanation_is_independent_counterevidence_vote": False,
        "alternative_explanation_count_is_support_count": False,
        "current_invocation_artifacts_are_publication_authority": False,
        "bundle_file_inventory_is_publication_authority": False,
        "process_story_publication_authority_artifact": runner.PROCESS_STORY_TXT,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _write_bundle(path: Path, members: set[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in members:
            archive.writestr(name, "ok")


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
    assert "and bundle_contract_valid" in source
    assert "and bundle_physical_valid" in source
    assert 'return 0 if required_analysis_layers_activated else 2' in source


def test_bundle_contract_accepts_only_claim_safe_manifest() -> None:
    manifest = _valid_manifest()
    assert runner._bundle_contract_valid(manifest) is True

    for field, bad_value in (
        ("bundle_file_inventory_is_publication_authority", True),
        ("current_invocation_artifacts_are_publication_authority", True),
        ("alternative_explanation_is_independent_counterevidence_vote", True),
        ("alternative_explanation_count_is_support_count", True),
        ("production_release", True),
        ("canonical_event_count", 31),
        ("true_action_count", 31),
    ):
        bad = dict(manifest)
        bad[field] = bad_value
        assert runner._bundle_contract_valid(bad) is False


def test_bundle_contract_requires_match_story_lineage_locks() -> None:
    manifest = _valid_manifest()
    for field in (
        "analyst_text_requires_final_assembly_admission",
        "match_story_lineage_preserved_in_analyst_report",
        "match_story_alternative_explanation_lineage_revalidated_in_analyst_report",
    ):
        bad = dict(manifest)
        bad[field] = False
        assert runner._bundle_contract_valid(bad) is False


def test_bundle_physical_gate_requires_crc_and_user_facing_members(tmp_path: Path) -> None:
    required = {
        runner.BUNDLE_MANIFEST,
        runner.ANALYST_REPORT,
        runner.PROCESS_STORY_TXT,
        runner.FULL_SPINE_JSON,
    }
    good = tmp_path / "good.zip"
    _write_bundle(good, required)
    assert runner._bundle_physical_valid(good) is True

    missing_story = tmp_path / "missing_story.zip"
    _write_bundle(missing_story, required - {runner.PROCESS_STORY_TXT})
    assert runner._bundle_physical_valid(missing_story) is False

    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"not-a-zip")
    assert runner._bundle_physical_valid(broken) is False


def test_professional_story_runner_preserves_claim_locks() -> None:
    root = Path(__file__).resolve().parents[5]
    source = (root / "active_match_professional_story_run_v1.py").read_text(encoding="utf-8")

    assert '"canonical_event_count": CANONICAL_EVENT_COUNT' in source
    assert '"true_action_count": TRUE_ACTION_COUNT' in source
    assert '"production_release": False' in source
    assert '"bundle_file_inventory_is_publication_authority": False' in source
    assert '"bundle_presence_is_analysis_activation": False' in source
    assert '"alternative_explanation_is_independent_counterevidence_vote": False' in source
    assert '"alternative_explanation_count_is_support_count": False' in source
    assert '"pipeline_is_possession_truth": False' in source
    assert '"pipeline_is_tactical_plan_truth": False' in source
    assert '"professional_story_is_causality_truth": False' in source
