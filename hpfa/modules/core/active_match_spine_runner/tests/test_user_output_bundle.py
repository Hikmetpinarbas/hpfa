import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import user_output_bundle
from user_output_bundle import (
    ANALYST_REPORT,
    BUNDLE_MANIFEST,
    BUNDLE_ZIP,
    build_analyst_report,
    snapshot_output_state,
    write_standard_user_outputs,
)


def _feature_payload():
    return {
        "module_id": "episode_feature_vector_lite_v1",
        "status": "REVIEW_REQUIRED",
        "episode_feature_vector_count": 2,
        "total_eligible_action_candidate_count": 30,
        "eligible_action_family_candidate_counts": {"PASS": 20, "SHOT": 4, "TURNOVER": 3, "RECOVERY": 3},
        "review_debt_feature_vector_count": 1,
        "total_unresolved_semantics_context_count": 2,
        "episode_feature_vectors": [
            {
                "start_second_candidate": 60,
                "end_second_candidate": 120,
                "eligible_action_candidate_count": 10,
                "shot_candidate_count": 1,
                "turnover_candidate_count": 1,
                "recovery_candidate_count": 1,
                "eligible_action_count_by_team_candidate": {"Team A": 7},
                "unknown_team_eligible_action_count": 3,
                "eligible_action_zone_counts": {"MIDDLE_THIRD": 6, "FINAL_THIRD": 4},
                "eligible_action_channel_counts": {"LEFT": 5, "CENTRE": 5},
                "action_family_counts": {"PASS": 7, "SHOT": 1, "TURNOVER": 1, "RECOVERY": 1},
            },
            {
                "start_second_candidate": 300,
                "end_second_candidate": 360,
                "eligible_action_candidate_count": 20,
                "shot_candidate_count": 3,
                "turnover_candidate_count": 2,
                "recovery_candidate_count": 2,
                "eligible_action_count_by_team_candidate": {"Team A": 5, "Team B": 10},
                "unknown_team_eligible_action_count": 5,
                "eligible_action_zone_counts": {"FINAL_THIRD": 12, "MIDDLE_THIRD": 8},
                "eligible_action_channel_counts": {"RIGHT": 12, "CENTRE": 8},
                "action_family_counts": {"PASS": 13, "SHOT": 3, "TURNOVER": 2, "RECOVERY": 2},
            },
        ],
    }


def _full_spine(
    *,
    feature_current=True,
    c4_current=True,
    status="REVIEW_REQUIRED",
    current_artifacts=None,
):
    return {
        "status": status,
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED" if status != "FAIL_CLOSED" else "BLOCK_FULL_SPINE",
        "episode_candidate_count": 2 if feature_current else None,
        "episode_feature_vector_count": 2 if feature_current else None,
        "temporal_episode_signature_count": 2 if feature_current else None,
        "intelligence_chain_count": 1 if c4_current else 0,
        "hard_block_hits": [] if status != "FAIL_CLOSED" else ["synthetic_failure"],
        "review_hits": ["synthetic_review"] if status != "FAIL_CLOSED" else [],
        "active_match_authority": "/runtime/active_single_match/current",
        "current_invocation_artifacts": list(current_artifacts or []),
        "engineering_evidence": {
            "current_context_episode_feature_lane_completed": feature_current,
            "current_c4_producers_reused": c4_current,
        },
        "intelligence_chains": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "Gorunur kanit grafigi aday okumayi destekler."
                }
            }
        ] if c4_current else [],
    }


def test_analyst_report_uses_current_episode_surface(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(tmp_path, _full_spine())
    assert "eligible_action_candidate_total=30" in text
    assert "05:00-06:00 shots=3" in text
    assert '"Team A": 12' in text
    assert '"Team B": 10' in text
    assert "SAFE_ARGUMENT_CANDIDATES" in text
    assert "feature_surface_current_invocation=true" in text
    assert "canonical_event_count=UNKNOWN" in text
    assert "production_release=false" in text
    assert "event-only occurrence/episode" not in text




def test_analyst_report_surfaces_current_p02_turnover_response_without_overclaim(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    full = _full_spine()
    full["engineering_evidence"]["rich_multiformat_lane_executed"] = True
    full["rich_multiformat_analysis_lattice"] = {
        "status": "REVIEW_REQUIRED",
        "review_hits": [],
        "entity_views": {
            "player_view_candidates": [],
            "team_view_candidates": [],
            "goalkeeper_view_candidates": [],
            "observed_metric_cell_count": 0,
        },
        "constructs": {"C01": {}},
        "phase_state_candidates": [],
        "primitive_metrics": [],
        "analysis_lattice": {},
        "progression_pool_p02": {
            "p02_team_pool_items": [
                {
                    "team_identity_candidate_id": "teamc_A",
                    "team_candidate": "Team A",
                }
            ],
            "process_units": {
                "opponent_response_summary_by_team": [
                    {
                        "team_identity_candidate_id": "teamc_A",
                        "turnover_handover_linked_count": 10,
                        "turnover_handover_opponent_advanced_access_count": 3,
                        "turnover_handover_opponent_no_advanced_access_count": 5,
                        "turnover_handover_opponent_access_unresolved_count": 2,
                    }
                ]
            },
        },
    }
    text = build_analyst_report(tmp_path, full)
    assert "turnover_handover_opponent_response:" in text
    assert "Team A" in text
    assert "10 process-unit" in text
    assert "advanced access=3" in text
    assert "no advanced access=5" in text
    assert "unresolved=2" in text
    assert "nedensellik, tehlikeli gecis veya taktik ustunluk kaniti degildir" in text
    assert "event-only occurrence/episode" not in text
    assert "EVENT bu gozlem evreninin yalniz bir ailesidir" in text




def test_analyst_report_surfaces_review_bounded_variant_contrasts_without_success_label(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    full = _full_spine()
    full["engineering_evidence"]["rich_multiformat_lane_executed"] = True
    full["rich_multiformat_analysis_lattice"] = {
        "status": "REVIEW_REQUIRED",
        "review_hits": [],
        "entity_views": {
            "player_view_candidates": [],
            "team_view_candidates": [],
            "goalkeeper_view_candidates": [],
            "observed_metric_cell_count": 0,
        },
        "constructs": {"C01": {}},
        "phase_state_candidates": [],
        "primitive_metrics": [],
        "analysis_lattice": {},
        "progression_pool_p02": {
            "p02_team_pool_items": [
                {"team_identity_candidate_id": "teamc_A", "team_candidate": "Team A"},
            ],
            "process_units": {"opponent_response_summary_by_team": []},
            "process_unit_comparisons": {
                "process_unit_comparison_populations": [
                    {
                        "status": "POPULATION_ELIGIBLE",
                        "member_count": 4,
                        "variant_family_count": 3,
                        "reference_context": {
                            "team_identity_candidate_id": "teamc_A",
                            "period_candidate": "1",
                            "score_state_candidate": "LEVEL",
                            "process_start_zone_candidate": "MIDDLE_THIRD",
                        },
                        "terminal_activity_distribution": {
                            "TEAM_HANDOVER_BOUNDARY_VISIBLE": 2,
                            "TIME_GAP_BOUNDARY_VISIBLE": 2,
                        },
                        "end_zone_distribution": {
                            "FINAL_THIRD": 2,
                            "MIDDLE_THIRD": 2,
                        },
                        "pairwise_comparison_candidates": [
                            {
                                "outcome_relation": "OPPOSITE",
                                "variant_contrast_dimensions": [
                                    "visible_exit_class_candidate",
                                    "opponent_response_status",
                                ],
                                "success_failure_label": "NOT_ASSIGNED",
                            },
                            {
                                "outcome_relation": "SAME",
                                "variant_contrast_dimensions": [
                                    "opponent_advanced_access_state_candidate",
                                ],
                                "success_failure_label": "NOT_ASSIGNED",
                            },
                        ],
                    }
                ]
            },
        },
    }
    text = build_analyst_report(tmp_path, full)
    assert "GORUNUR VARYANT KARSILASTIRMASI — REVIEW-BOUNDED" in text
    assert "Team A" in text
    assert "4 process-unit" in text
    assert "3 gorunur varyant ailesi" in text
    assert "Advanced-access sonucu farkli pair=1" in text
    assert "exit-class farki=1" in text
    assert "rakip-response durumu farki=1" in text
    assert "rakibin sonraki advanced-access sonucu farki=1" in text
    assert "success/failure etiketi atanmaz" in text
    assert "bagimsiz kanit degildir" in text



def test_analyst_report_surfaces_emit_candidate_without_promoting_release(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    full = _full_spine()
    full["engineering_evidence"]["rich_multiformat_lane_executed"] = True
    full["rich_multiformat_analysis_lattice"] = {
        "status": "REVIEW_REQUIRED",
        "review_hits": [],
        "entity_views": {
            "player_view_candidates": [],
            "team_view_candidates": [],
            "goalkeeper_view_candidates": [],
            "observed_metric_cell_count": 0,
        },
        "constructs": {"C01": {}},
        "phase_state_candidates": [],
        "primitive_metrics": [],
        "analysis_lattice": {},
        "progression_pool_p02": {
            "p02_team_pool_items": [
                {"team_identity_candidate_id": "teamc_A", "team_candidate": "Team A"},
            ],
            "process_units": {"opponent_response_summary_by_team": []},
            "process_unit_comparisons": {"process_unit_comparison_populations": []},
            "professional_finding_target_candidates": [
                {
                    "finding_status": "EMIT_CANDIDATE",
                    "finding_admission_decision": "EMIT_CANDIDATE",
                    "finding_admission_reasons": [],
                    "exact_context": {
                        "team_identity_candidate_id": "teamc_A",
                        "period_candidate": "1",
                        "score_state_candidate": "LEVEL",
                        "process_start_zone_candidate": "MIDDLE_THIRD",
                    },
                    "resolved_target_state_denominator": 4,
                    "target_observed_visible_count": 2,
                    "target_not_observed_complete_path_count": 2,
                    "target_state_unresolved_count": 0,
                    "visible_variant_family_count": 3,
                    "admitted_opposite_counterevidence_pair_count": 1,
                    "WHAT_VISIBLE": "bounded visible variation",
                    "SAFE_MEANING": "bounded match-local meaning only",
                    "visible_exit_class_distribution": {"TEAM_HANDOVER_BOUNDARY_VISIBLE": 2},
                    "opponent_response_status_distribution": {"EXACT_HANDOVER_BOUNDARY_LINKED": 2},
                },
                {
                    "finding_status": "REVIEW_REQUIRED",
                    "finding_admission_decision": "REVIEW_REQUIRED",
                    "finding_admission_reasons": ["target_state_unresolved_burden_present"],
                    "exact_context": {
                        "team_identity_candidate_id": "teamc_A",
                        "period_candidate": "2",
                        "score_state_candidate": "LEVEL",
                        "process_start_zone_candidate": "DEFENSIVE_THIRD",
                    },
                    "resolved_target_state_denominator": 3,
                    "target_observed_visible_count": 1,
                    "target_not_observed_complete_path_count": 2,
                    "target_state_unresolved_count": 1,
                    "visible_variant_family_count": 3,
                    "admitted_opposite_counterevidence_pair_count": 1,
                    "WHAT_VISIBLE": "review bounded visible variation",
                    "SAFE_MEANING": "review bounded match-local meaning only",
                    "visible_exit_class_distribution": {},
                    "opponent_response_status_distribution": {},
                },
            ],
        },
    }
    full["P02_professional_finding_report_contract_item_count"] = 1
    full["p02_professional_finding_report_contracts"] = {
        "status": "SMOKE_PASS",
        "items": [
            {
                "safe_sentence": {
                    "safe_sentence_candidate_tr": "P02_ADMITTED_SAFE_SENTENCE_FIXTURE",
                },
                "assembly": {
                    "assembly_decision": "READY_FOR_DRAFT_REPORT_ASSEMBLY_CANDIDATE",
                    "status": "SMOKE_PASS",
                    "final_report_allowed": False,
                    "production_report_allowed": False,
                },
            }
        ],
    }
    text = build_analyst_report(tmp_path, full)
    assert "[EMIT_CANDIDATE] Team A" in text
    assert "[REVIEW_REQUIRED] Team A" in text
    assert "ADMISSION_REASONS: []" in text
    assert "target_state_unresolved_burden_present" in text
    assert "Admission summary: EMIT_CANDIDATE=1; REVIEW_REQUIRED=1" in text
    assert "EMIT_CANDIDATE release veya production claim degildir." in text
    assert "P02_ADMITTED_SAFE_SENTENCE_FIXTURE" in text
    p02_index = text.index("P02_ADMITTED_SAFE_SENTENCE_FIXTURE")
    generic_index = text.find("Görünür kanıt grafiği")
    if generic_index >= 0:
        assert p02_index < generic_index

def test_fail_closed_report_does_not_consume_stale_feature_artifact(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    text = build_analyst_report(
        tmp_path,
        _full_spine(feature_current=False, c4_current=False, status="FAIL_CLOSED"),
    )
    assert "feature_surface_current_invocation=false" in text
    assert "eligible_action_candidate_total=UNAVAILABLE_CURRENT_INVOCATION" in text
    assert "05:00-06:00 shots=3" not in text
    assert "onceki run artifact'i kullanilmadi" in text
    assert "Current invocation Episode Feature yuzeyi tamamlanmadi" in text


def test_bundle_uses_producer_write_ledger_even_when_content_unchanged(tmp_path):
    stale = tmp_path / "stale_previous_run.txt"
    stale.write_text("stale", encoding="utf-8")
    rewritten = tmp_path / "deterministic_rewritten.json"
    rewritten.write_text("same", encoding="utf-8")
    before = snapshot_output_state(tmp_path)

    # Simulate deterministic producer rewrite with identical bytes.
    rewritten.write_text("same", encoding="utf-8")
    feature = tmp_path / "episode_feature_vector_lite_v1.json"
    feature.write_text(json.dumps(_feature_payload()), encoding="utf-8")
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")

    result = write_standard_user_outputs(
        tmp_path,
        _full_spine(
            current_artifacts=[str(rewritten), str(feature), str(full_json), str(full_txt)]
        ),
        before_state=before,
    )
    assert Path(result["analyst_report"]).name == ANALYST_REPORT
    assert Path(result["bundle_zip"]).name == BUNDLE_ZIP
    assert Path(result["bundle_manifest"]).name == BUNDLE_MANIFEST

    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
    assert "deterministic_rewritten.json" in names
    assert "episode_feature_vector_lite_v1.json" in names
    assert "active_match_full_spine_v1.json" in names
    assert "active_match_full_spine_v1.txt" in names
    assert ANALYST_REPORT in names
    assert BUNDLE_MANIFEST in names
    assert "stale_previous_run.txt" not in names

    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["bundle_scope"] == "PRODUCER_DECLARED_CURRENT_INVOCATION_ARTIFACTS_PLUS_STANDARD_DELIVERABLES"
    assert manifest["selection_basis"] == "PRODUCER_WRITE_LEDGER_NOT_MTIME_OR_CONTENT_CHANGE_HEURISTIC"
    assert manifest["feature_surface_current_invocation"] is True
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["production_release"] is False


def test_bundle_rejects_declared_nested_or_outside_paths(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_file = nested / "should_not_ship.json"
    nested_file.write_text("{}", encoding="utf-8")
    outside = tmp_path.parent / "outside_should_not_ship.json"
    outside.write_text("{}", encoding="utf-8")
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")

    write_standard_user_outputs(
        tmp_path,
        _full_spine(
            feature_current=False,
            c4_current=False,
            current_artifacts=[str(nested_file), str(outside), str(full_json), str(full_txt)],
        ),
    )
    with zipfile.ZipFile(tmp_path / BUNDLE_ZIP) as archive:
        names = set(archive.namelist())
    assert nested_file.name not in names
    assert outside.name not in names
    outside.unlink()


def test_atomic_zip_publication_never_exposes_partial_new_bundle(tmp_path, monkeypatch):
    old_zip = tmp_path / BUNDLE_ZIP
    with zipfile.ZipFile(old_zip, "w") as archive:
        archive.writestr("old.txt", "old-valid-bundle")
    before_old = old_zip.read_bytes()

    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    before = snapshot_output_state(tmp_path)

    real_zipfile = user_output_bundle.zipfile.ZipFile

    class BrokenZipFile:
        def __init__(self, *args, **kwargs):
            self._inner = real_zipfile(*args, **kwargs)
        def __enter__(self):
            self._inner.__enter__()
            return self
        def __exit__(self, *args):
            return self._inner.__exit__(*args)
        def write(self, *args, **kwargs):
            self._inner.write(*args, **kwargs)
            raise OSError("synthetic archive failure")

    monkeypatch.setattr(user_output_bundle.zipfile, "ZipFile", BrokenZipFile)
    with pytest.raises(OSError):
        write_standard_user_outputs(
            tmp_path,
            _full_spine(feature_current=False, current_artifacts=[str(full_json), str(full_txt)]),
            before_state=before,
        )

    assert old_zip.read_bytes() == before_old
    assert not (tmp_path / f".{BUNDLE_ZIP}.tmp").exists()


def test_analyst_report_surfaces_football_process_mechanisms_without_internal_codes(tmp_path):
    (tmp_path / "episode_feature_vector_lite_v1.json").write_text(
        json.dumps(_feature_payload()), encoding="utf-8"
    )
    full = _full_spine()
    full["engineering_evidence"]["rich_multiformat_lane_executed"] = True
    full["rich_multiformat_analysis_lattice"] = {
        "status": "REVIEW_REQUIRED",
        "review_hits": [],
        "entity_views": {
            "player_view_candidates": [],
            "team_view_candidates": [],
            "goalkeeper_view_candidates": [],
            "observed_metric_cell_count": 0,
        },
        "constructs": {"C01": {}},
        "phase_state_candidates": [],
        "primitive_metrics": [],
        "analysis_lattice": {},
        "progression_pool_p02": {
            "penalty_area_access_evaluation_status": "UNOBSERVABLE_WITH_CURRENT_DATA",
            "penalty_area_access_evaluable": False,
            "p02_team_pool_items": [
                {"team_identity_candidate_id": "teamc_A", "team_candidate": "Team A"},
                {"team_identity_candidate_id": "teamc_B", "team_candidate": "Team B"},
            ],
            "process_units": {"opponent_response_summary_by_team": []},
            "visible_consequence_path_severity_candidates": [
                {
                    "team_identity_candidate_id": "teamc_A",
                    "visible_consequence_path_signature": (
                        "ANCHOR:TURNOVER -> L1:OPPONENT:PASS -> L2:OPPONENT:PASS"
                    ),
                    "eligible_anchor_population_count": 20,
                    "visible_occurrence_count": 8,
                    "exact_process_response_bound_count": 7,
                    "final_third_visible_count": 3,
                    "no_final_third_visible_count": 3,
                    "zone_path_unresolved_count": 1,
                    "penalty_area_visible_count": 0,
                    "shot_activity_visible_count": 1,
                    "response_zone_route_counts": {"MIDDLE_THIRD->FINAL_THIRD": 3},
                }
            ],
            "same_team_continuation_process_profiles": [
                {
                    "team_identity_candidate_id": "teamc_A",
                    "visible_consequence_path_signature": (
                        "ANCHOR:PASS -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS"
                    ),
                    "anchor_visible_occurrence_count": 30,
                    "unique_process_unit_count": 10,
                    "process_unit_with_final_third_entry_count": 4,
                    "process_unit_with_final_third_continuation_count": 1,
                    "process_unit_with_no_final_third_visible_count": 4,
                    "process_unit_with_zone_unresolved_count": 1,
                    "final_third_entry_process_with_shot_activity_count": 1,
                    "final_third_entry_process_with_turnover_activity_count": 2,
                    "final_third_entry_process_with_cross_activity_count": 2,
                    "final_third_entry_process_end_reason_counts": {
                        "TEAM_HANDOVER_BOUNDARY": 2,
                        "TIME_GAP_BOUNDARY": 2,
                    },
                    "max_anchor_windows_within_single_process_unit": 5,
                },
                {
                    "team_identity_candidate_id": "teamc_A",
                    "visible_consequence_path_signature": (
                        "ANCHOR:RECOVERY -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS"
                    ),
                    "unique_process_unit_count": 3,
                    "process_unit_with_final_third_entry_count": 1,
                    "process_unit_with_final_third_continuation_count": 0,
                    "process_unit_with_no_final_third_visible_count": 2,
                    "process_unit_with_zone_unresolved_count": 0,
                    "process_unit_with_shot_activity_after_anchor_count": 1,
                },
            ],
        },
    }
    text = build_analyst_report(tmp_path, full)

    assert "MAC MEKANIZMASI ADAYLARI — SUREC / DEVAM / SONUC" in text
    assert "Top kaybi sonrasi rakibin pas-pas devami:" in text
    assert "gorunur devami degerlendirilebilir 20 top-kaybi adayinin 8'inde" in text
    assert "Pas dolasiminin final-third'e donusumu:" in text
    assert "30 gorunur pas -> pas -> pas penceresi 10 benzersiz oyun surecinde toplandi" in text
    assert "takim el degistirme=2" in text
    assert "Recovery sonrasi ayni takimin yeniden hucum devami:" in text
    assert "ayni surecteki coklu pencereler bagimsiz kanit sayilmaz" in text
    assert "ceza sahasi erisimi bu surec-bolge yuzeyinde mevcut veriyle gozlenemiyor" in text
    assert "ceza-sahasi gorundu=0" not in text
    assert "ANCHOR:" not in text
    assert "process_unit" not in text
