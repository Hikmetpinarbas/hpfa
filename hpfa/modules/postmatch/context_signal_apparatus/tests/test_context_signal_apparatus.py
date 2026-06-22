from hpfa.modules.postmatch.context_signal_apparatus.src.context_tagger import attach_context, period_scope
from hpfa.modules.postmatch.context_signal_apparatus.src.signal_profile import build_signal_profile


def test_period_scope_stoppage():
    assert period_scope({"half": 1, "start": 2701}) == "first_half_stoppage"
    assert period_scope({"half": 2, "start": 5401}) == "second_half_stoppage"


def test_context_fields_are_attached():
    rows = [
        {"ID": 1, "half": 1, "start": 10, "team": "Australia", "action": "Passes accurate", "pos_x": 30},
        {"ID": 2, "half": 1, "start": 20, "team": "Australia", "action": "Goal", "pos_x": 100},
    ]
    out = attach_context(rows, home_team="Australia", away_team="Turkey")
    assert out[0]["coordinate_scale"] == "105x68"
    assert out[1]["score_state"] == "1-0"
    assert out[1]["claim_safety"] == "EVIDENCE_ONLY"


def test_signal_profile_claim_safe():
    rows = [
        {"start": 1, "action": "Passes accurate", "pos_x": 20, "team": "A"},
        {"start": 2, "action": "Passes accurate", "pos_x": 30, "team": "A"},
        {"start": 3, "action": "Passes accurate", "pos_x": 35, "team": "A"},
    ]
    profile = build_signal_profile(rows, team="A")
    assert profile["surface_row_count"] == 3
    assert profile["claim_safety"] == "EVIDENCE_ONLY"
    assert "dominance" not in str(profile).lower()
