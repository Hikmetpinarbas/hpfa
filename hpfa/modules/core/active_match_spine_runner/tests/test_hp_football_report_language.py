import json
import zipfile

from hpfa.modules.core.active_match_spine_runner.src.user_output_bundle import (
    ANALYST_REPORT_TR,
    build_hp_football_report_tr,
    write_standard_user_outputs,
)


def test_hp_report_is_football_only_and_uses_hp_language(tmp_path):
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_gs", "team_normalized_key": "galatasaray", "team_aliases_raw": ["Galatasaray"]},
            {"team_identity_candidate_id": "team_ts", "team_normalized_key": "trabzonspor", "team_aliases_raw": ["Trabzonspor"]},
        ]
    }
    (tmp_path / "match_local_identity_candidates_lite_v1.json").write_text(
        json.dumps(identity), encoding="utf-8"
    )
    rich = {
        "status": "PASS",
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_gs",
                        "eligible_process_n": 10,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 2,
                        "shot_ending_process_n": 3,
                        "process_family_profiles": [
                            {
                                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                                "eligible_process_n": 8,
                                "visible_loss_process_n": 3,
                                "visible_recovery_process_n": 1,
                                "shot_ending_process_n": 3,
                            }
                        ],
                    },
                    {
                        "team_identity_candidate_id": "team_ts",
                        "eligible_process_n": 8,
                        "visible_loss_process_n": 5,
                        "visible_recovery_process_n": 1,
                        "shot_ending_process_n": 1,
                        "process_family_profiles": [
                            {
                                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                                "eligible_process_n": 6,
                                "visible_loss_process_n": 4,
                                "visible_recovery_process_n": 1,
                                "shot_ending_process_n": 1,
                            }
                        ],
                    },
                ]
            }
        },
        "time_window_process_mix_change_context": {
            "status": "PASS",
            "profiles": [
                {
                    "team_identity_candidate_id": "team_gs",
                    "period_candidate": "1",
                    "window_start_second_candidate": 0.0,
                    "window_end_second_candidate": 900.0,
                    "eligible_visible_process_n": 5,
                    "process_family_counts": {"POSITIONAL_ATTACK_CANDIDATE": 4, "COUNTERATTACK_CANDIDATE": 1},
                }
            ],
            "comparisons": [],
        },
        "loss_next_opponent_process_context": {
            "status": "PASS",
            "loss_context_row_count": 6,
            "next_opponent_process_family_counts": {"POSITIONAL_ATTACK_CANDIDATE": 3, "COUNTERATTACK_CANDIDATE": 1},
            "rows": [],
        },
        "recovery_next_process_context": {
            "status": "PASS",
            "recovery_context_row_count": 4,
            "next_visible_process_family_counts": {"POSITIONAL_ATTACK_CANDIDATE": 2},
            "rows": [],
        },
        "visible_circulation_fate_profile": {
            "status": "PASS",
            "profiles": [
                {
                    "team_identity_candidate_id": "team_gs",
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "eligible_circulation_process_n": 8,
                    "visible_fate_counts": {"SHOT_LINKED_VISIBLE": 3, "LOSS_LINKED_VISIBLE": 3, "OTHER_VISIBLE_OR_UNRESOLVED": 2},
                }
            ],
        },
        "player_score_state_process_participation": {"status": "PASS", "profiles": []},
    }
    spine = {
        "status": "REVIEW_REQUIRED",
        "rich_multiformat_analysis_lattice": rich,
        "engineering_evidence": {
            "rich_multiformat_lane_executed": True,
            "current_invocation_artifacts": ["match_local_identity_candidates_lite_v1.json"],
        },
        "current_invocation_artifacts": ["match_local_identity_candidates_lite_v1.json"],
    }

    report = build_hp_football_report_tr(tmp_path, spine)

    assert "HPFA MAÇ ANALİZİ" in report
    assert "MAÇIN ANA RESMİ" in report
    assert "TOPLA OYUN" in report
    assert "TOP KAYBI VE KAZANIM SONRASI" in report
    assert "MAÇIN DEĞİŞEN YÜZÜ" in report
    assert "TEKRAR EDEN YOLLAR" in report
    assert "OYUNCU İŞLEVLERİ" in report
    assert "ANALİST KARARI — NEREYE BAKMALI?" in report
    assert "SONUÇ — ANALİST NOTU" in report
    assert "Galatasaray" in report
    assert "yerleşik hücum" in report

    forbidden = [
        "admitted", "candidate", "claim", "current-run", "M09", "provider",
        "trace", "layer", "review", "evidence", "XLSX", "runtime",
        "canonical_event_count", "true_action_count", "Kanıt notu",
        "Okuma çerçevesi", "PASS", "REVIEW_REQUIRED", "kabul edilmiş",
        "maruziyet", "skor-state", "kader", "CREATE=UNKNOWN", "substitution",
        "sonuç ufku", "possession",
    ]
    lowered = report.casefold()
    for token in forbidden:
        assert token.casefold() not in lowered


def test_standard_user_output_uses_hp_football_report_for_turkish_surface(tmp_path):
    identity = {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "team_gs", "team_normalized_key": "galatasaray", "team_aliases_raw": ["Galatasaray"]},
            {"team_identity_candidate_id": "team_ts", "team_normalized_key": "trabzonspor", "team_aliases_raw": ["Trabzonspor"]},
        ]
    }
    identity_path = tmp_path / "match_local_identity_candidates_lite_v1.json"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    rich = {
        "status": "PASS",
        "constructs": {
            "C03": {
                "team_process_profiles": [
                    {
                        "team_identity_candidate_id": "team_gs",
                        "eligible_process_n": 10,
                        "visible_loss_process_n": 4,
                        "visible_recovery_process_n": 2,
                        "shot_ending_process_n": 3,
                        "process_family_profiles": [],
                    }
                ]
            }
        },
        "visible_circulation_fate_profile": {"status": "PASS", "profiles": []},
        "player_score_state_process_participation": {"status": "PASS", "profiles": []},
    }
    full_json = tmp_path / "active_match_full_spine_v1.json"
    full_txt = tmp_path / "active_match_full_spine_v1.txt"
    full_json.write_text("{}", encoding="utf-8")
    full_txt.write_text("status=REVIEW_REQUIRED", encoding="utf-8")
    spine = {
        "status": "REVIEW_REQUIRED",
        "decision": "FULL_SPINE_COMPLETED_REVIEW_REQUIRED",
        "rich_multiformat_analysis_lattice": rich,
        "engineering_evidence": {"rich_multiformat_lane_executed": True},
        "current_invocation_artifacts": [str(identity_path), str(full_json), str(full_txt)],
        "production_release": False,
    }

    result = write_standard_user_outputs(tmp_path, spine)
    report_path = tmp_path / ANALYST_REPORT_TR
    assert result["analyst_report_tr"] == str(report_path)
    delivery_zip = result["football_delivery_zip"]
    with zipfile.ZipFile(delivery_zip) as archive:
        assert set(archive.namelist()) == {ANALYST_REPORT_TR}
    report = report_path.read_text(encoding="utf-8")
    assert "MAÇIN ANA RESMİ" in report
    assert "TOPLA OYUN — İLERLEME VE ÜRETİM" in report
    forbidden = ["Kanıt notu", "Okuma çerçevesi", "current-run", "provider", "claim", "M09", "SEQUENCE / PROCESS INTELLIGENCE"]
    for token in forbidden:
        assert token.casefold() not in report.casefold()
