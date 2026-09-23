from hpfa.modules.core.active_match_spine_runner.src.user_output_bundle import _human_aerial_duel_cards


def _rich(rows):
    return {
        "aerial_duel_first_visible_state_context": {
            "rows": rows,
            "claim_ceiling": "MATCH_LOCAL_AERIAL_DUEL_FIRST_VISIBLE_STATE_CANDIDATE_ONLY",
        }
    }


def _identity():
    return {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "TEAM_A",
                "team_aliases_raw": ["Team A"],
            }
        ]
    }


def test_aerial_duel_card_reports_first_visible_continuation_not_control_truth():
    rows = [
        {
            "team_identity_candidate_id": "TEAM_A",
            "provider_aerial_duel_outcome_candidate": "PROVIDER_REVIEWED_AERIAL_DUEL_WON_CANDIDATE",
            "first_visible_team_relation_to_aerial_actor_team": "SAME_TEAM_FIRST_VISIBLE_ACTION",
            "binding_state": "SINGLE_VISIBLE_PROCESS_FAMILY_MATCH",
        },
        {
            "team_identity_candidate_id": "TEAM_A",
            "provider_aerial_duel_outcome_candidate": "PROVIDER_REVIEWED_AERIAL_DUEL_LOST_CANDIDATE",
            "first_visible_team_relation_to_aerial_actor_team": "OPPONENT_TEAM_FIRST_VISIBLE_ACTION",
            "binding_state": "FIRST_VISIBLE_TEAM_OBSERVED_PROCESS_NOT_BOUND",
        },
    ]

    cards = _human_aerial_duel_cards(_rich(rows), _identity(), "tr")

    assert len(cards) == 2
    assert "1 tanesi kazanıldı" in cards[0]
    assert "1 tanesi kaybedildi" in cards[0]
    assert "1 örnekte aynı takımda" in cards[0]
    assert "1 örnekte rakipte" in cards[0]
    assert "top kontrolü" in cards[1]
    assert "Claim scope yalnız ilk strikt-sonraki görünür takım durumuyla sınırlıdır" in cards[1]
    assert "ikinci top hâkimiyeti için ayrı observation gerekir" in cards[1]


def test_aerial_duel_card_preserves_review_and_no_followup_burden():
    rows = [
        {
            "team_identity_candidate_id": "TEAM_A",
            "provider_aerial_duel_outcome_candidate": "PROVIDER_REVIEWED_AERIAL_DUEL_WON_CANDIDATE",
            "first_visible_team_relation_to_aerial_actor_team": "UNRESOLVED",
            "binding_state": "REVIEW_REQUIRED_MIXED_TEAM_FIRST_VISIBLE_LAYER",
        },
        {
            "team_identity_candidate_id": "TEAM_A",
            "provider_aerial_duel_outcome_candidate": "PROVIDER_REVIEWED_AERIAL_DUEL_WON_CANDIDATE",
            "first_visible_team_relation_to_aerial_actor_team": "UNRESOLVED",
            "binding_state": "NO_VISIBLE_FOLLOWUP",
        },
    ]

    cards = _human_aerial_duel_cards(_rich(rows), _identity(), "en")

    assert len(cards) == 2
    assert "1 cases remain review-required" in cards[1]
    assert "1 have no visible follow-up" in cards[1]
    assert "not ball-control, possession, or second-ball-control truth" in cards[1]


def test_no_aerial_rows_produces_no_analyst_card():
    assert _human_aerial_duel_cards(_rich([]), _identity(), "tr") == []
