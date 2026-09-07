import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src import process_story_sidecar as sidecar


def _source(module_id):
    return {
        "module_id": module_id,
        "status": "PASS",
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _write_prerequisites(root: Path):
    (root / sidecar.SEQUENCE_JSON).write_text(json.dumps(_source("visible_action_sequence_candidates_lite_v1")), encoding="utf-8")
    (root / sidecar.TRACE_JSON).write_text(json.dumps(_source("trackable_action_trace_candidates_lite_v1")), encoding="utf-8")
    (root / sidecar.CONSEQUENCE_JSON).write_text(json.dumps(_source("trackable_action_consequence_candidates_lite_v1")), encoding="utf-8")


def _stage(module_id, status="PASS", **extra):
    payload = {
        "module_id": module_id,
        "status": status,
        "hard_block_hits": [],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    payload.update(extra)
    return payload


def _assembly_item(**lineage_updates):
    lineage = {
        "source_narrative_ids": ["NARRATIVE_A", "NARRATIVE_B"],
        "process_narrative_count": 2,
        "recurrent_process_count": 1,
        "robust_recurrent_process_count": 1,
        "counterevidence_bearing_process_count": 1,
        "context_sensitive_process_count": 1,
        "null_evaluated_process_count": 1,
        "nominal_support_is_independent_evidence_count": False,
        "cross_process_support_independence_proven": False,
    }
    lineage.update(lineage_updates)
    return {
        "status": "SMOKE_PASS",
        "assembly_decision": sidecar.READY_ASSEMBLY_DECISION,
        "draft_report_candidate_allowed": True,
        "block_family": sidecar.MATCH_STORY_BLOCK_FAMILY,
        "assembly_item_candidate_tr": "ASSEMBLY_ADMITTED_PROCESS_STORY",
        "match_story_evidence_lineage": lineage,
    }


def test_current_reconstruction_story_sidecar_reuses_artifacts_and_reaches_assembly(monkeypatch, tmp_path):
    _write_prerequisites(tmp_path)
    calls = []

    def variant(*args, **kwargs):
        calls.append("variant")
        return _stage("partial_order_trace_variant_lite_v1")

    def similarity(*args, **kwargs):
        calls.append(("similarity", kwargs))
        return _stage("trace_similarity_primitive_lite_v1")

    def contrast(*args, **kwargs):
        calls.append(("contrast", kwargs))
        return _stage("trace_contrast_packet_lite_v1")

    def robustness(*args, **kwargs):
        calls.append(("robustness", kwargs))
        return _stage("recurrence_robustness_envelope_lite_v1")

    def admission(*args, **kwargs):
        calls.append("admission")
        return _stage("sequence_pattern_admission_lite_v1")

    def binding(*args, **kwargs):
        calls.append("binding")
        return _stage("sequence_safe_finding_binding_lite_v1")

    def narrative(*args, **kwargs):
        calls.append("narrative")
        return _stage("sequence_analyst_narrative_lite_v1")

    def story(*args, **kwargs):
        calls.append("story")
        return _stage(
            "match_story_synthesis_lite_v1",
            entity_stories=[{"entity_scope": "team_a", "story_tr": "Gorunur surecler birlikte degerlendirildi."}],
            entity_story_count=1,
        )

    def report(*args, **kwargs):
        calls.append("report")
        return _stage(
            "analyst_report_block_composer_lite_v1",
            report_blocks=[{"report_block_id": "r1"}],
            report_block_count=1,
        )

    def contract(block, idx):
        calls.append("contract")
        return _stage(
            "report_output_contract_lite_v1",
            inclusion_decision="INCLUDE_BLOCK_CANDIDATE",
            contract_item_id="c1",
            report_block_id="r1",
        )

    def assembly(item, idx):
        calls.append("assembly")
        return _stage(
            "final_report_assembly_gate_lite_v1",
            assembly_decision="READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
        )

    monkeypatch.setattr(sidecar, "build_partial_order_trace_variants", variant)
    monkeypatch.setattr(sidecar, "build_trace_similarity_primitive", similarity)
    monkeypatch.setattr(sidecar, "build_trace_contrast_packets", contrast)
    monkeypatch.setattr(sidecar, "build_recurrence_robustness_envelopes", robustness)
    monkeypatch.setattr(sidecar, "build_sequence_pattern_admissions", admission)
    monkeypatch.setattr(sidecar, "build_sequence_safe_finding_blocks", binding)
    monkeypatch.setattr(sidecar, "compose_sequence_analyst_narrative", narrative)
    monkeypatch.setattr(sidecar, "synthesize_match_story", story)
    monkeypatch.setattr(sidecar, "compose_match_story_report", report)
    monkeypatch.setattr(sidecar, "evaluate_report_block", contract)
    monkeypatch.setattr(sidecar, "evaluate_assembly_item", assembly)

    result = sidecar.build_process_story_from_current_reconstruction(tmp_path)
    assert result["status"] == "SMOKE_PASS"
    assert result["story_path_blocked"] is False
    assert result["entity_story_count"] == 1
    assert result["report_block_count"] == 1
    assert result["assembly_item_count"] == 1
    assert result["ready_assembly_item_count"] == 1
    assert result["reconstruction_artifacts_reused_without_reingest"] is True
    assert result["parallel_sequence_engine_created"] is False
    assert result["exploratory_similarity_parameters"]["calibrated"] is False
    assert result["nominal_support_is_independent_evidence_count"] is False
    assert result["artifact_semantics"] == sidecar.JSON_ARTIFACT_SEMANTICS
    assert result["user_facing_publication_authority"] is False
    assert result["publication_authority_artifact"] == sidecar.OUTPUT_TXT
    assert result["raw_entity_stories_are_publication_authority"] is False
    assert result["assembly_admission_required_for_user_facing_story"] is True
    assert calls[0] == "variant"
    similarity_call = next(item for item in calls if isinstance(item, tuple) and item[0] == "similarity")
    assert similarity_call[1]["weights"] == sidecar.SIMILARITY_WEIGHTS
    contrast_call = next(item for item in calls if isinstance(item, tuple) and item[0] == "contrast")
    assert contrast_call[1]["minimum_similarity"] == sidecar.MINIMUM_SIMILARITY
    assert contrast_call[1]["eligibility_weights"] == sidecar.SIMILARITY_WEIGHTS
    robust_call = next(item for item in calls if isinstance(item, tuple) and item[0] == "robustness")
    assert robust_call[1]["tested_similarity_thresholds"] == sidecar.ROBUSTNESS_THRESHOLDS
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_missing_current_reconstruction_artifact_does_not_rerun_ingest(tmp_path):
    result = sidecar.build_process_story_from_current_reconstruction(tmp_path)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["story_path_blocked"] is True
    assert result["entity_story_count"] == 0
    assert result["decision"] == "PROCESS_STORY_NOT_EVALUATED_PREREQUISITE_MISSING"
    assert "current_reconstruction_story_prerequisite_missing" in result["review_hits"][0]
    assert result["artifact_semantics"] == sidecar.JSON_ARTIFACT_SEMANTICS
    assert result["user_facing_publication_authority"] is False


def test_inner_fail_closed_blocks_only_story_path(monkeypatch, tmp_path):
    _write_prerequisites(tmp_path)
    monkeypatch.setattr(
        sidecar,
        "build_partial_order_trace_variants",
        lambda *args, **kwargs: _stage("partial_order_trace_variant_lite_v1", status="FAIL_CLOSED", hard_block_hits=["bad_variant"]),
    )
    for name in (
        "build_trace_similarity_primitive",
        "build_trace_contrast_packets",
        "build_recurrence_robustness_envelopes",
        "build_sequence_pattern_admissions",
        "build_sequence_safe_finding_blocks",
        "compose_sequence_analyst_narrative",
        "synthesize_match_story",
        "compose_match_story_report",
    ):
        monkeypatch.setattr(sidecar, name, lambda *args, **kwargs: _stage("downstream", status="FAIL_CLOSED", hard_block_hits=["upstream_failed"]))
    result = sidecar.build_process_story_from_current_reconstruction(tmp_path)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["story_path_blocked"] is True
    assert result["entity_story_count"] == 0
    assert result["report_block_count"] == 0
    assert result["assembly_item_count"] == 0
    assert "partial_order_trace_variant_fail_closed" in result["hard_block_hits"]


def test_write_sidecar_persists_direct_current_invocation_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sidecar,
        "build_process_story_from_current_reconstruction",
        lambda root: _stage(
            sidecar.MODULE_ID,
            status="REVIEW_REQUIRED",
            decision="PROCESS_STORY_RUNTIME_CANDIDATES_BUILT",
            story_path_blocked=False,
            entity_stories=[{"story_tr": "RAW_DIAGNOSTIC_STORY"}],
            entity_story_count=1,
            report_block_count=0,
            assembly_items=[],
            assembly_item_count=0,
            ready_assembly_item_count=0,
            review_hits=["independence_unproven"],
            nominal_support_is_independent_evidence_count=False,
            **sidecar._artifact_authority_metadata(),
        ),
    )
    result = sidecar.write_process_story_sidecar(tmp_path)
    json_path = tmp_path / sidecar.OUTPUT_JSON
    txt_path = tmp_path / sidecar.OUTPUT_TXT
    assert json_path.is_file()
    assert txt_path.is_file()
    assert set(result["current_invocation_artifacts"]) == {str(json_path), str(txt_path)}
    diagnostic = json.loads(json_path.read_text(encoding="utf-8"))
    assert diagnostic["artifact_semantics"] == sidecar.JSON_ARTIFACT_SEMANTICS
    assert diagnostic["user_facing_publication_authority"] is False
    assert diagnostic["publication_authority_artifact"] == sidecar.OUTPUT_TXT
    assert diagnostic["raw_entity_stories_are_publication_authority"] is False
    assert diagnostic["assembly_admission_required_for_user_facing_story"] is True
    assert diagnostic["entity_stories"][0]["story_tr"] == "RAW_DIAGNOSTIC_STORY"
    text = txt_path.read_text(encoding="utf-8")
    assert f"artifact_semantics={sidecar.TXT_ARTIFACT_SEMANTICS}" in text
    assert "user_facing_publication_authority=true" in text
    assert "RAW_DIAGNOSTIC_STORY" not in text


def test_sidecar_txt_publishes_only_assembly_admitted_story(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sidecar,
        "build_process_story_from_current_reconstruction",
        lambda root: _stage(
            sidecar.MODULE_ID,
            status="SMOKE_PASS",
            decision="PROCESS_STORY_RUNTIME_CANDIDATES_BUILT",
            story_path_blocked=False,
            entity_stories=[{"story_tr": "RAW_STORY_MUST_NOT_SHIP"}],
            entity_story_count=1,
            report_block_count=1,
            assembly_items=[_assembly_item()],
            assembly_item_count=1,
            ready_assembly_item_count=1,
            review_hits=[],
            nominal_support_is_independent_evidence_count=False,
        ),
    )
    sidecar.write_process_story_sidecar(tmp_path)
    text = (tmp_path / sidecar.OUTPUT_TXT).read_text(encoding="utf-8")
    assert "ASSEMBLY_ADMITTED_PROCESS_STORY" in text
    assert "RAW_STORY_MUST_NOT_SHIP" not in text
    assert "publication_admitted_match_story_count=1" in text
    assert "process_narrative_count=2" in text


def test_sidecar_txt_suppresses_malformed_process_accounting(monkeypatch, tmp_path):
    malformed = _assembly_item(null_evaluated_process_count=True)
    monkeypatch.setattr(
        sidecar,
        "build_process_story_from_current_reconstruction",
        lambda root: _stage(
            sidecar.MODULE_ID,
            status="SMOKE_PASS",
            decision="PROCESS_STORY_RUNTIME_CANDIDATES_BUILT",
            story_path_blocked=False,
            entity_stories=[{"story_tr": "RAW_STORY_MUST_NOT_SHIP"}],
            entity_story_count=1,
            report_block_count=1,
            assembly_items=[malformed],
            assembly_item_count=1,
            ready_assembly_item_count=1,
            review_hits=[],
            nominal_support_is_independent_evidence_count=False,
        ),
    )
    sidecar.write_process_story_sidecar(tmp_path)
    text = (tmp_path / sidecar.OUTPUT_TXT).read_text(encoding="utf-8")
    assert "ASSEMBLY_ADMITTED_PROCESS_STORY" not in text
    assert "RAW_STORY_MUST_NOT_SHIP" not in text
    assert "publication_admitted_match_story_count=0" in text


def test_match_story_publication_accounting_invariants():
    assert sidecar._publishable_match_story_assembly(_assembly_item()) is True
    assert sidecar._publishable_match_story_assembly(_assembly_item(process_narrative_count=3)) is False
    assert sidecar._publishable_match_story_assembly(_assembly_item(context_sensitive_process_count=3)) is False
    assert sidecar._publishable_match_story_assembly(_assembly_item(recurrent_process_count=0, robust_recurrent_process_count=1)) is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/active_match_spine_runner/src/process_story_sidecar.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
