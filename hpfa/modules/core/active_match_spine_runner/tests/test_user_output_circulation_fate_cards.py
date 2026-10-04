from hpfa.modules.core.active_match_spine_runner.src.user_output_bundle import _human_circulation_fate_cards


def test_human_circulation_fate_cards_render_visible_fate_without_sterility_claim():
    rich = {
        "visible_circulation_fate_profile": {
            "profiles": [
                {
                    "team_identity_candidate_id": "TEAM_A",
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "eligible_circulation_process_n": 4,
                    "visible_fate_counts": {
                        "SHOT_LINKED_VISIBLE": 1,
                        "LOSS_LINKED_VISIBLE": 1,
                        "RECOVERY_LINKED_VISIBLE": 1,
                        "OTHER_VISIBLE_OR_UNRESOLVED": 1,
                    },
                }
            ]
        }
    }
    identity = {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "TEAM_A",
                "team_aliases_raw": ["Alpha FC"],
            }
        ]
    }

    tr = _human_circulation_fate_cards(rich, identity, "tr")
    en = _human_circulation_fate_cards(rich, identity, "en")

    assert tr
    assert en
    assert any("pas/taşıma içeren 4 görünür süreç" in line for line in tr)
    assert any("steril/üretken oyun" in line for line in tr)
    assert any("Scope is limited to visible process fate" in line for line in en)
