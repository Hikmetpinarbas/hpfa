from hpfa.modules.core.active_match_spine_runner.src import orphan_capability_sidecars as sidecars


def test_process_story_parent_projection_keeps_diagnostic_counts_qualified():
    projection = sidecars._process_story_diagnostic_projection(
        {
            "artifact_semantics": "DIAGNOSTIC_INTERNAL_EVIDENCE_TRACE",
            "publication_authority_artifact": "active_match_process_story_sidecar_v1.txt",
            "entity_story_count": 2,
            "ready_assembly_item_count": 1,
            "current_invocation_artifacts": [
                "/tmp/TRACE_A/active_match_process_story_sidecar_v1.json",
                "/tmp/TRACE_A/active_match_process_story_sidecar_v1.txt",
            ],
        }
    )

    assert projection["process_story_diagnostic_artifact_semantics"] == "DIAGNOSTIC_INTERNAL_EVIDENCE_TRACE"
    assert projection["process_story_diagnostic_user_facing_publication_authority"] is False
    assert projection["process_story_publication_authority_artifact"] == "active_match_process_story_sidecar_v1.txt"
    assert projection["process_story_upstream_publication_authority_declaration_matches_contract"] is True
    assert projection["process_story_entity_story_count_diagnostic"] == 2
    assert projection["process_story_ready_assembly_item_count_diagnostic"] == 1
    assert projection["process_story_diagnostic_counts_are_publication_admission"] is False
    assert projection["process_story_current_invocation_artifacts_are_publication_authority"] is False
    assert projection["process_story_diagnostic_artifact"] == "active_match_process_story_sidecar_v1.json"
    assert projection["process_story_diagnostic_artifact_present_in_current_invocation"] is True
    assert projection["process_story_publication_authority_artifact_present_in_current_invocation"] is True
    assert "process_story_entity_story_count" not in projection
    assert "process_story_ready_assembly_item_count" not in projection


def test_process_story_parent_projection_does_not_trust_upstream_publication_flag_or_redirect():
    projection = sidecars._process_story_diagnostic_projection(
        {
            "artifact_semantics": "DIAGNOSTIC_INTERNAL_EVIDENCE_TRACE",
            "user_facing_publication_authority": True,
            "publication_authority_artifact": "active_match_process_story_sidecar_v1.json",
            "entity_story_count": True,
            "ready_assembly_item_count": True,
            "current_invocation_artifacts": [
                "/tmp/TRACE_B/active_match_process_story_sidecar_v1.json",
            ],
        }
    )

    assert projection["process_story_diagnostic_user_facing_publication_authority"] is False
    assert projection["process_story_publication_authority_artifact"] == "active_match_process_story_sidecar_v1.txt"
    assert projection["process_story_upstream_publication_authority_declaration_matches_contract"] is False
    assert projection["process_story_diagnostic_counts_are_publication_admission"] is False
    assert projection["process_story_current_invocation_artifacts_are_publication_authority"] is False
    assert projection["process_story_diagnostic_artifact_present_in_current_invocation"] is True
    assert projection["process_story_publication_authority_artifact_present_in_current_invocation"] is False


def test_no_sample_match_identity_leak():
    source = __import__("pathlib").Path(
        "hpfa/modules/core/active_match_spine_runner/src/orphan_capability_sidecars.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
