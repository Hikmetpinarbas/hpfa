import pytest
from hpfa.narrative.forensic_guard import validate_narrative

def test_pass_simple_observation():
    r = validate_narrative("Observation: Pas, (x=45, y=30).", state="CONTROLLED")
    assert r["decision"] == "PASS"

def test_pass_banned_inside_quotes_only():
    r = validate_narrative('Oyuncu dedi ki: "maybe we were winning"', state="CONTROLLED")
    assert r["decision"] == "PASS"

@pytest.mark.parametrize("txt", [
    "Belki takım üstün.",
    "muhtemelen kazanıyorlar",
    "I think they are in control",
    "maybe the pass was key",
    "perhaps top oyunda",
    "apparently domine ediyor",
    "seems controlling possession",
    "could be a goal",
])
def test_deny_uncertainty_terms(txt):
    r = validate_narrative(txt, state="CONTROLLED")
    assert r["decision"] == "DENY"

def test_unvalidated_allows_only_logline_exact():
    r = validate_narrative("State: UNVALIDATED (veri eksikliği)", state="UNVALIDATED")
    assert r["decision"] == "PASS"

def test_contested_rewrite_possession_claims():
    r = validate_narrative("Takım üstün.", state="CONTESTED")
    assert r["decision"] == "REWRITE"

def test_dead_ball_rewrite_in_play_claims():
    r = validate_narrative("Top oyunda.", state="DEAD_BALL")
    assert r["decision"] == "REWRITE"
