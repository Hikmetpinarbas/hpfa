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
    ANALYST_REPORT_EN,
    ANALYST_REPORT_TR,
    BUNDLE_MANIFEST,
    BUNDLE_ZIP,
    build_analyst_report,
    build_human_analyst_report_en,
    build_human_analyst_report_tr,
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


def test_process_contest_cards_put_attack_and_opponent_exposure_on_same_surface():
    rich = {
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 12,
                        "shot_ending_process_n": 3,
                        "visible_loss_process_n": 5,
                    },
                    {
                        "team_identity_candidate_id": "team_b",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 9,
                        "shot_ending_process_n": 1,
                        "visible_loss_process_n": 4,
                    },
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
            {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
        ]
    }
    cards = user_output_bundle._human_process_contest_cards(rich, identity, "tr")
    text = "\n".join(cards)
    assert "Alpha — yerleşik hücum" in text
    assert "12 görünür süreç" in text
    assert "savunma maruziyeti tarafında beta" in text.casefold()
    assert "9 süreç kurdu" in text
    assert "Savunma maruziyeti rakibin görünür süreç hacmi" in text


def test_six_phase_matrix_renders_all_twelve_direction_slots():
    rows = []
    phases = [
        ("ESTABLISHED_ATTACK", "ATTACK", "POSITIONAL_ATTACK_CANDIDATE"),
        ("ATTACKING_TRANSITION", "ATTACK", "COUNTERATTACK_CANDIDATE"),
        ("ATTACKING_SET_PIECE", "ATTACK", "SET_PIECE_ATTACK_CANDIDATE"),
        ("ESTABLISHED_DEFENCE", "DEFENCE", "POSITIONAL_ATTACK_CANDIDATE"),
        ("DEFENSIVE_TRANSITION", "DEFENCE", "COUNTERATTACK_CANDIDATE"),
        ("DEFENSIVE_SET_PIECE", "DEFENCE", "SET_PIECE_ATTACK_CANDIDATE"),
    ]
    for team, opp in (("team_a", "team_b"), ("team_b", "team_a")):
        for phase, perspective, family in phases:
            rows.append({
                "team_identity_candidate_id": team,
                "opponent_team_identity_candidate_id": opp,
                "canonical_phase_slot": phase,
                "perspective": perspective,
                "source_process_family_candidate": family,
                "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                "eligible_process_n": 10,
                "shot_ending_process_n": 2,
                "visible_loss_process_n": 4,
                "visible_recovery_process_n": 1,
            })
    rich = {"constructs": {"C03": {"six_phase_team_matrix": rows}}}
    identity = {"team_identity_candidates": [
        {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
        {"team_identity_candidate_id": "team_b", "team_normalized_key": "beta"},
    ]}
    cards = user_output_bundle._human_process_contest_cards(rich, identity, "tr")
    text = "\n".join(cards)
    assert "Alpha — 6 faz" in text
    assert "Beta — 6 faz" in text
    for label in ("yerleşik hücum", "geçiş hücumu", "duran top hücumu", "yerleşik savunma", "geçiş savunması", "duran top savunması"):
        assert text.count(label + ":") == 2
    assert "Değerlendirme süreç hacmi" in text


def test_phase_motif_sentence_exposes_recurrence_without_calling_it_tactical_truth():
    row = {
        "recurring_process_motif_family_count": 3,
        "recurring_process_motif_covered_process_n": 12,
        "top_recurring_process_motifs": [{
            "member_process_n": 6,
            "shot_variant_n": 2,
            "visible_loss_variant_n": 3,
            "visible_recovery_variant_n": 1,
            "morphology_signature": {
                "length_bucket": "MEDIUM_3_5_LAYERS",
                "action_family_presence": ["PASS", "CARRY"],
                "pass_carry_style": "MIXED_PASS_CARRY",
                "route_hint": "MIDDLE_THIRD->FINAL_THIRD",
            },
        }],
    }
    text = user_output_bundle._phase_motif_sentence(row, "tr")
    assert "3 aile" in text
    assert "12 süreç" in text
    assert "En sık motif 6 örnek" in text
    assert "2 şut bağlantılı" in text
    assert "3 görünür kayıp" in text


def test_phase_motif_sentence_surfaces_first_supported_divergence_safely():
    row = {
        "recurring_process_motif_family_count": 1,
        "recurring_process_motif_covered_process_n": 4,
        "top_recurring_process_motifs": [{
            "member_process_n": 4,
            "shot_variant_n": 1,
            "visible_loss_variant_n": 2,
            "visible_recovery_variant_n": 0,
            "morphology_signature": {
                "length_bucket": "MEDIUM_3_5_LAYERS",
                "action_family_presence": ["PASS", "CARRY"],
                "pass_carry_style": "MIXED_PASS_CARRY",
                "route_hint": "NO_UNAMBIGUOUS_ROUTE_HINT",
            },
            "representative_first_supported_grammar_divergence": {
                "left_variant_context": "SHOT_LINKED",
                "right_variant_context": "LOSS_LINKED",
                "first_supported_grammar_divergence": {
                    "operation": "SUBSTITUTE",
                    "left_token": "LAYER[PASS]",
                    "right_token": "LAYER[CARRY]",
                },
            },
        }],
    }
    text = user_output_bundle._phase_motif_sentence(row, "tr")
    assert "İlk destekli grammar ayrışması" in text
    assert "SHOT_LINKED ↔ LOSS_LINKED" in text
    assert "LAYER[PASS] ↔ LAYER[CARRY]" in text
    assert "görünür ayrışma noktasını" in text


def test_human_reports_use_football_language_and_keep_evidence_note_separate():
    rich = {
        "status": "REVIEW_REQUIRED",
        "constructs": {
            "C02": {
                "representative_actor_argument": {
                    "actor_labels": ["Mason Greenwood"],
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "eligible_n": 36,
                    "visible_target_annotation_k": 7,
                    "target_outcome_unresolved_u": 29,
                    "observed_visible_target_annotation_frequency": 7 / 36,
                    "match_local_baseline_shot_frequency": 10 / 72,
                    "descriptive_lift": (7 / 36) / (10 / 72),
                    "eligible_episode_spread": 25,
                    "positive_episode_spread": 7,
                    "selection_candidate_pool_n": 75,
                    "selection_rank": 1,
                },
                "representative_dyad_argument": None,
            }
        },
    }
    spine = _full_spine()
    spine["rich_multiformat_analysis_lattice"] = rich
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(".", spine)
    en = build_human_analyst_report_en(".", spine)

    assert "Greenwood" in tr
    assert "36 tanesinde" in tr
    assert "7 tanesinde" in tr
    assert "Kanıt notu:" in tr
    assert "admitted" not in tr
    assert "eligible süreç" not in tr
    assert "visible shot-present annotation" not in tr

    assert "Greenwood" in en
    assert "36 instances" in en
    assert "7 of those instances" in en
    assert "Evidence note:" in en
    assert "match-local descriptive ratio=" in en
    assert "match-local pool" not in en


def test_human_reports_render_team_process_and_mechanism_in_football_language(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(
        json.dumps(
            {
                "team_identity_candidates": [
                    {
                        "team_identity_candidate_id": "team_1",
                        "team_normalized_key": "galatasaray",
                        "team_aliases_raw": ["Galatasaray"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    feature_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "grammar_stable_variant_feature_delta_records": [
                    {
                        "grammar_stable_variant_feature_delta_id": "m1",
                        "source_process_variant_family_ref": "family_1",
                        "team_identity_candidate_ids": ["team_1"],
                        "period_candidates": ["1"],
                        "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                        "resolved_variant_count": 4,
                        "success_resolved_variant_count": 3,
                        "failure_resolved_variant_count": 1,
                        "right_censored_variant_count": 0,
                        "first_supported_consequence_difference_layer_candidate": 1,
                        "consequence_feature_difference_candidates": [{"feature_token": "x"}],
                        "visible_episode_spread_count": 2,
                        "occurrence_disjoint_support_cluster_count": 2,
                        "success_failure_supported_branch_divergence_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rich = {
        "status": "REVIEW_REQUIRED",
        "constructs": {
            "C02": {"representative_actor_argument": None, "representative_dyad_argument": None},
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_1",
                        "eligible_process_n": 12,
                        "visible_loss_process_n": 5,
                        "visible_recovery_process_n": 3,
                        "shot_ending_process_n": 2,
                    }
                ]
            },
        },
    }
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    spine["rich_multiformat_analysis_lattice"] = rich
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(tmp_path, spine)
    en = build_human_analyst_report_en(tmp_path, spine)

    assert "Galatasaray: Sistem bu maçta 12 görünür oyun sürecini" in tr
    assert "MEKANİZMA KARTI 1 | SINIF=ANA MEKANİZMA ADAYI | TAKIM=Galatasaray | DÖNEM=1. devre | TRACE=pas → pas" in tr
    assert "İnceleme noktası 1: Galatasaray, 1. devre. pas → pas bağlantısı" in tr
    assert "hangi aksiyon veya bağlam değişiminin sonuçları ayırdığı" in tr
    assert "MEKANİZMA ADAYLARI" not in tr
    assert "Kanıt notu:" in tr
    assert "independent_support=" not in tr
    assert "grammar_signature_tokens" not in tr

    assert "Galatasaray: The system linked 12 visible match processes" in en
    assert "MECHANISM CARD 1 | CLASS=MAIN MECHANISM CANDIDATE | TEAM=Galatasaray | PERIOD=first half | TRACE=pass → pass" in en
    assert "Review point 1: Galatasaray, first half. The pass → pass connection" in en
    assert "which subsequent action or context change separates those outcomes" in en
    assert "MECHANISM CANDIDATES" not in en
    assert "Evidence note:" in en



def test_unvalidated_actor_aggregate_label_does_not_leak_into_human_mechanism_card(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    rich_path = tmp_path / "rich_multiformat_analysis_lattice_v1.json"

    identity_path.write_text(json.dumps({
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_1", "team_normalized_key": "galatasaray"}
        ],
        "actor_identity_candidates": [
            {
                "actor_identity_candidate_id": "actor_unsafe",
                "actor_normalized_key": "wrong_plausible_name",
                "actor_aliases_raw": ["99. Wrong Plausible Name (999999)"],
                "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
                "validated_player_identity": False,
            }
        ],
    }), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_unsafe",
            "source_process_variant_family_ref": "family_unsafe",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["1"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 4,
            "success_resolved_variant_count": 3,
            "failure_resolved_variant_count": 1,
            "visible_episode_spread_count": 2,
            "occurrence_disjoint_support_cluster_count": 2,
            "first_supported_context_difference_layer_candidate": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "context_feature_difference_candidates": [{
                "feature_token": "LAYER[0]::actor_identity_candidate_ids:actor_unsafe",
                "success_visible_numerator": 3,
                "success_eligible_denominator": 3,
                "failure_visible_numerator": 0,
                "failure_eligible_denominator": 1,
                "descriptive_rate_delta_success_minus_failure": 1.0,
            }],
            "consequence_feature_difference_candidates": [],
        }]
    }), encoding="utf-8")
    rich_path.write_text(json.dumps({
        "status": "PASS",
        "constructs": {
            "C02": {
                "player_function_profiles": [{
                    "actor_identity_candidate_id": "actor_unsafe",
                    "actor_label": "Wrong Plausible Name",
                    "function_dimensions": {},
                }]
            }
        }
    }), encoding="utf-8")

    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path), str(rich_path)])
    spine["rich_multiformat_analysis_lattice"] = json.loads(rich_path.read_text(encoding="utf-8"))
    spine["engineering_evidence"]["rich_multiformat_lane_executed"] = True

    tr = build_human_analyst_report_tr(tmp_path, spine)
    assert "Wrong Plausible Name" not in tr


def test_human_report_exposes_visible_same_team_vs_handover_split_without_causal_claim(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(json.dumps({"team_identity_candidates": [{"team_identity_candidate_id": "team_1", "team_normalized_key": "galatasaray"}]}), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_split",
            "source_process_variant_family_ref": "family_split",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["2"],
            "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
            "resolved_variant_count": 284,
            "success_resolved_variant_count": 277,
            "failure_resolved_variant_count": 7,
            "right_censored_variant_count": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "consequence_feature_difference_candidates": [
                {"feature_token": "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 252, "success_eligible_denominator": 277, "failure_visible_numerator": 0, "failure_eligible_denominator": 7, "descriptive_rate_delta_success_minus_failure": 0.91},
                {"feature_token": "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 12, "success_eligible_denominator": 277, "failure_visible_numerator": 7, "failure_eligible_denominator": 7, "descriptive_rate_delta_success_minus_failure": -0.96},
            ],
            "visible_episode_spread_count": 16,
            "occurrence_disjoint_support_cluster_count": 33,
            "success_failure_supported_branch_divergence_count": 6,
        }]
    }), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    tr = build_human_analyst_report_tr(tmp_path, spine)
    en = build_human_analyst_report_en(tmp_path, spine)
    assert "252/277 tanesinde aynı takım devamı" in tr
    assert "7/7 tanesinde rakibe geçiş" in tr
    assert "aynı başlangıçtan sonra oluşan görünür sonuç ayrımını" in tr
    assert "same-team continuation appears in 252/277" in en
    assert "opponent handover appears in 7/7" in en
    assert "summarizes the visible outcome split" in en


def test_single_episode_mechanism_candidate_is_rendered_as_limited_comparison(tmp_path):
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    feature_path = tmp_path / "grammar_stable_variant_feature_delta_projection_v1.json"
    identity_path.write_text(json.dumps({"team_identity_candidates": [{"team_identity_candidate_id": "team_1", "team_normalized_key": "trabzonspor"}]}), encoding="utf-8")
    feature_path.write_text(json.dumps({
        "status": "PASS",
        "grammar_stable_variant_feature_delta_records": [{
            "grammar_stable_variant_feature_delta_id": "m_single",
            "source_process_variant_family_ref": "family_single",
            "team_identity_candidate_ids": ["team_1"],
            "period_candidates": ["1"],
            "grammar_signature_tokens": ["LAYER[DUEL]", "LAYER[PASS]"],
            "resolved_variant_count": 2,
            "success_resolved_variant_count": 1,
            "failure_resolved_variant_count": 1,
            "right_censored_variant_count": 0,
            "first_supported_consequence_difference_layer_candidate": 1,
            "consequence_feature_difference_candidates": [
                {"feature_token": "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 1, "success_eligible_denominator": 1, "failure_visible_numerator": 0, "failure_eligible_denominator": 1, "descriptive_rate_delta_success_minus_failure": 1.0},
                {"feature_token": "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE", "partial_order_layer_index": 1, "success_visible_numerator": 0, "success_eligible_denominator": 1, "failure_visible_numerator": 1, "failure_eligible_denominator": 1, "descriptive_rate_delta_success_minus_failure": -1.0},
            ],
            "visible_episode_spread_count": 1,
            "occurrence_disjoint_support_cluster_count": 1,
            "success_failure_supported_branch_divergence_count": 1,
        }]
    }), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(identity_path), str(feature_path)])
    tr = build_human_analyst_report_tr(tmp_path, spine)
    assert "Sınırlı karşılaştırma 1:" in tr
    assert "ana mekanizma olarak yorumlanmamalıdır" in tr
    assert "1/1 tanesinde aynı takım devamı" not in tr

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
    assert Path(result["analyst_report_tr"]).name == ANALYST_REPORT_TR
    assert Path(result["analyst_report_en"]).name == ANALYST_REPORT_EN
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
    assert ANALYST_REPORT_TR in names
    assert ANALYST_REPORT_EN in names
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


def test_team_process_cards_expose_visible_consequence_response_without_inflating_meaning():
    rich = {
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_a",
                        "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                        "eligible_process_n": 10,
                        "shot_ending_process_n": 2,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 1,
                        "visible_consequence_response_profile": {
                            "process_presence_counts": {
                                "OPPONENT_HANDOVER_CANDIDATE": 5,
                                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE": 3,
                                "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE": 2,
                                "NO_VISIBLE_FOLLOW_UP_CANDIDATE": 1,
                            }
                        },
                    }
                ]
            }
        }
    }
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_a", "team_normalized_key": "alpha"},
        ]
    }
    cards = user_output_bundle._human_team_process_cards(rich, identity, "tr")
    text = "\n".join(cards)

    assert "5 süreçte rakibe geçiş" in text
    assert "3 süreçte breakdown sonrası rakip takeover" in text
    assert "2 süreçte aynı-zamanlı iki takım belirsizliği" in text
    assert "1 süreçte görünür follow-up yokluğu" in text
    assert "maç-içi süreç kompozisyonunu gösterir" in text
    assert "Okuma çerçevesi" in text
    assert "follow-up durumlarının" in text
    assert "same-time review" in text



def _write_current_inventory(path: Path) -> None:
    path.write_text(
        json.dumps({
            "module_id": "multiformat_file_inventory_lite_v1",
            "status": "PASS",
            "files": [
                {"relative_path": "a.csv", "sha256": "a" * 64, "size_bytes": 10, "source_role": "PLAYER_SURFACE_CANDIDATE"},
                {"relative_path": "b.xml", "sha256": "b" * 64, "size_bytes": 20, "source_role": "PLAYER_SURFACE_CANDIDATE"},
            ],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }),
        encoding="utf-8",
    )


def test_bundle_manifest_binds_exact_head_input_snapshot_environment_and_artifacts(tmp_path):
    inventory = tmp_path / "multiformat_file_inventory_lite_v1.json"
    _write_current_inventory(inventory)
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(inventory), str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    write_standard_user_outputs(tmp_path, spine)
    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    provenance = manifest["current_run_provenance_envelope"]

    assert provenance["status"] == "PASS"
    assert len(provenance["exact_head_sha"]) == 40
    assert provenance["input_snapshot"]["status"] == "PASS"
    assert provenance["input_snapshot"]["file_count"] == 2
    assert len(provenance["input_snapshot"]["fingerprint_sha256"]) == 64
    assert len(provenance["runtime_environment"]["fingerprint_sha256"]) == 64
    assert len(provenance["artifact_manifest_digest_sha256"]) == 64
    assert len(provenance["current_run_context_fingerprint_sha256"]) == 64
    assert provenance["identity_kind"] == "DETERMINISTIC_CONTEXT_FINGERPRINT_NOT_UNIQUE_INVOCATION_UUID"
    assert provenance["provenance_creates_new_football_evidence"] is False
    assert provenance["provenance_can_authorize_emit"] is False
    assert provenance["provenance_can_strengthen_claim_ceiling"] is False
    assert provenance["production_release"] is False


def test_missing_current_inventory_downgrades_provenance_only_not_bundle_or_claim_state(tmp_path):
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    result = write_standard_user_outputs(tmp_path, spine)
    manifest = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
    provenance = manifest["current_run_provenance_envelope"]

    assert provenance["status"] == "REVIEW_REQUIRED"
    assert provenance["input_snapshot"]["reason"] == "current_multiformat_inventory_not_declared"
    assert Path(result["bundle_zip"]).is_file()
    assert manifest["runtime_status"] == "REVIEW_REQUIRED"
    assert manifest["canonical_event_count"] == "UNKNOWN"
    assert manifest["true_action_count"] == "UNKNOWN"
    assert manifest["production_release"] is False
    assert provenance["provenance_can_authorize_emit"] is False


def test_current_run_context_fingerprint_is_stable_for_same_declared_context(tmp_path):
    inventory = tmp_path / "multiformat_file_inventory_lite_v1.json"
    _write_current_inventory(inventory)
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(inventory), str(full_json), str(full_txt)])
    spine["execution_root"] = str(ROOT)

    write_standard_user_outputs(tmp_path, spine)
    first = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))["current_run_provenance_envelope"]
    write_standard_user_outputs(tmp_path, spine)
    second = json.loads((tmp_path / BUNDLE_MANIFEST).read_text(encoding="utf-8"))["current_run_provenance_envelope"]

    assert second["current_run_context_fingerprint_sha256"] == first["current_run_context_fingerprint_sha256"]
    assert second["artifact_manifest_digest_sha256"] == first["artifact_manifest_digest_sha256"]
    assert second["input_snapshot"]["fingerprint_sha256"] == first["input_snapshot"]["fingerprint_sha256"]

def test_mechanism_safe_context_uses_only_common_preoutcome_context(tmp_path):
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "source_first_supported_branch_divergence_ref": "fsbd_1",
            },
            {
                "safe_finding_handoff_candidate_id": "sfh_2",
                "source_first_supported_branch_divergence_ref": "fsbd_2",
            },
        ]
    }
    admission = {
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "ABSTAIN",
                "claim_output_allowed": False,
                "branch_preoutcome_context_enrichment": {
                    "state": "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS",
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                    "provider_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                },
            },
            {
                "source_safe_finding_handoff_ref": "sfh_2",
                "decision": "ABSTAIN",
                "claim_output_allowed": False,
                "branch_preoutcome_context_enrichment": {
                    "state": "PRE_BRANCH_CONTEXT_ENRICHED_PARTIAL",
                    "score_state_candidate": {"Alpha": 0, "Beta": 0},
                    "provider_process_family_candidates": [],
                },
            },
        ]
    }
    process_variant = {
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "opvf_1",
                "supported_branch_divergence_bindings": [
                    {"source_first_supported_branch_divergence_ref": "fsbd_1"},
                    {"source_first_supported_branch_divergence_ref": "fsbd_2"},
                ],
            }
        ]
    }
    seq_path = tmp_path / user_output_bundle.VISIBLE_SEQUENCE_JSON
    adm_path = tmp_path / user_output_bundle.SAFE_FINDING_ADMISSION_JSON
    seq_path.write_text(json.dumps(sequence), encoding="utf-8")
    adm_path.write_text(json.dumps(admission), encoding="utf-8")
    spine = _full_spine(current_artifacts=[str(seq_path), str(adm_path)])

    result = user_output_bundle._mechanism_safe_context_by_family(
        tmp_path, spine, process_variant
    )
    row = result["opvf_1"]
    assert row["score_state_consensus"] is True
    assert row["score_state_candidate"] == {"Alpha": 0, "Beta": 0}
    assert row["provider_process_family_consensus"] is True
    assert row["provider_process_family_candidates"] == [
        "POSITIONAL_ATTACK_CANDIDATE"
    ]
    assert row["provider_process_context_partial_count"] == 1
    assert row["emit_decision_count"] == 0
    assert row["creates_new_evidence"] is False
    assert row["creates_independent_support"] is False
    assert row["can_change_shortlist_selection"] is False
    assert row["can_change_safe_finding_decision"] is False
    assert row["can_authorize_emit"] is False

def test_actor_aggregate_context_is_match_context_not_mechanism_evidence():
    locator = {
        "feature_token": "actor_identity_candidate_ids:actor_1",
        "success_visible_numerator": 3,
        "success_eligible_denominator": 4,
        "failure_visible_numerator": 0,
        "failure_eligible_denominator": 1,
    }
    profiles = {
        "actor_1": {
            "actor_identity_candidate_id": "actor_1",
            "actor_label": "hikmet",
            "function_dimensions": {
                "ACCESS": [
                    {"metric_key": "progressive_passes", "raw_value": 8},
                    {"metric_key": "progressive_passes_accurate", "raw_value": 6},
                    {"metric_key": "final_third_entries", "raw_value": 4},
                ],
                "CREATION": [
                    {"metric_key": "xa_expected_assists", "raw_value": 0.31},
                ],
                "TERMINAL": [
                    {"metric_key": "shots", "raw_value": 3},
                    {"metric_key": "xg_expected_goals", "raw_value": 0.44},
                ],
                "PROCESS": {
                    "process_participation_counts": {
                        "POSITIONAL_ATTACK_CANDIDATE": 12,
                        "COUNTERATTACK_CANDIDATE": 3,
                    }
                },
            },
        }
    }
    text = user_output_bundle._actor_aggregate_context_sentence(
        "actor_1", locator, profiles, {"actor_1": "Hikmet"}, "tr"
    )
    assert "Oyuncu inceleme odağı: Hikmet." in text
    assert "progressive pass=8" in text
    assert "isabetli progressive pass=6" in text
    assert "son üçte bir girişi=4" in text
    assert "xA=0.31" in text
    assert "şut=3" in text
    assert "xG=0.44" in text
    assert "yerleşik hücum 12" in text
    assert "mekanizma aksiyon kimliği" in text
    assert "nedensel katkı için kullanıma kapalıdır" in text
