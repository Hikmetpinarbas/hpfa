import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src import process_story_sidecar as sidecar


def _assembly_item(*, bad_source=False, lock_breach=False):
    source_id = "OUTSIDE" if bad_source else "NARRATIVE_A"
    return {
        "status": "SMOKE_PASS",
        "assembly_decision": sidecar.READY_ASSEMBLY_DECISION,
        "draft_report_candidate_allowed": True,
        "block_family": sidecar.MATCH_STORY_BLOCK_FAMILY,
        "assembly_item_candidate_tr": "ASSEMBLY_ADMITTED_PROCESS_STORY",
        "match_story_evidence_lineage": {
            "source_narrative_ids": ["NARRATIVE_A", "NARRATIVE_B"],
            "process_narrative_count": 2,
            "recurrent_process_count": 1,
            "robust_recurrent_process_count": 1,
            "counterevidence_bearing_process_count": 1,
            "context_sensitive_process_count": 1,
            "null_evaluated_process_count": 1,
            "nominal_support_is_independent_evidence_count": False,
            "cross_process_support_independence_proven": False,
            "alternative_explanation_bearing_process_count": 1,
            "alternative_explanations": [
                {
                    "source_narrative_id": source_id,
                    "alternative_explanation": {
                        "type": "CONTEXT_DEPENDENCE",
                        "safe_meaning": "Visible recurrence may depend on admitted context."
                    },
                }
            ],
            "alternative_explanation_is_independent_counterevidence_vote": True if lock_breach else False,
            "alternative_explanation_count_is_support_count": False,
        },
    }


def _report(item):
    return {
        "module_id": sidecar.MODULE_ID,
        "status": "SMOKE_PASS",
        "decision": "PROCESS_STORY_RUNTIME_CANDIDATES_BUILT",
        "story_path_blocked": False,
        "entity_stories": [],
        "entity_story_count": 0,
        "report_block_count": 1,
        "assembly_items": [item],
        "assembly_item_count": 1,
        "ready_assembly_item_count": 1,
        "review_hits": [],
        "hard_block_hits": [],
        "nominal_support_is_independent_evidence_count": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_publication_txt_preserves_structured_alternative_explanation_lineage(monkeypatch, tmp_path):
    monkeypatch.setattr(sidecar, "build_process_story_from_current_reconstruction", lambda root: _report(_assembly_item()))
    sidecar.write_process_story_sidecar(tmp_path)
    text = (tmp_path / sidecar.OUTPUT_TXT).read_text(encoding="utf-8")
    assert "publication_admitted_match_story_count=1" in text
    assert "alternative_explanation_bearing_process_count=1" in text
    assert '"source_narrative_id": "NARRATIVE_A"' in text
    assert '"type": "CONTEXT_DEPENDENCE"' in text
    assert "alternative_explanation_is_independent_counterevidence_vote=false" in text
    assert "alternative_explanation_count_is_support_count=false" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "true_action_count=UNKNOWN" in text
    assert "production_release=false" in text


def test_alternative_explanation_source_outside_story_cohort_is_not_publishable(monkeypatch, tmp_path):
    monkeypatch.setattr(sidecar, "build_process_story_from_current_reconstruction", lambda root: _report(_assembly_item(bad_source=True)))
    sidecar.write_process_story_sidecar(tmp_path)
    text = (tmp_path / sidecar.OUTPUT_TXT).read_text(encoding="utf-8")
    assert "publication_admitted_match_story_count=0" in text
    assert "ASSEMBLY_ADMITTED_PROCESS_STORY" not in text
    assert "CONTEXT_DEPENDENCE" not in text


def test_alternative_explanation_cannot_be_promoted_to_independent_counterevidence(monkeypatch, tmp_path):
    monkeypatch.setattr(sidecar, "build_process_story_from_current_reconstruction", lambda root: _report(_assembly_item(lock_breach=True)))
    sidecar.write_process_story_sidecar(tmp_path)
    text = (tmp_path / sidecar.OUTPUT_TXT).read_text(encoding="utf-8")
    assert "publication_admitted_match_story_count=0" in text
    assert "ASSEMBLY_ADMITTED_PROCESS_STORY" not in text


def test_publication_contract_preserves_claim_locks():
    path = Path("hpfa/modules/core/active_match_spine_runner/contract/process_story_publication_alternative_explanation_lineage_v1.json")
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["invariants"]["alternative_explanation_is_independent_counterevidence_vote"] is False
    assert contract["invariants"]["alternative_explanation_count_is_support_count"] is False
    assert contract["claim_boundary"]["canonical_event_count"] == "UNKNOWN"
    assert contract["claim_boundary"]["true_action_count"] == "UNKNOWN"
    assert contract["claim_boundary"]["production_release"] is False
