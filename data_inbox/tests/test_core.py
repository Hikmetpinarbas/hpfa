from hpfa_core.action_registry import ActionRegistry, RegistryError
from hpfa_core.type_rules import parse_percent
from hpfa_core.missing_policy import validate_event_row, validate_xlsx_row


def test_registry_load_and_resolve(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text("""
- canonical_action: GK_SAVE
  aliases: [save, parry]
  possession_effect: NEUTRAL
  allowed_states: [CONTESTED]
  fail_closed_default: UNVALIDATED
""", encoding="utf-8")

    reg = ActionRegistry.from_yaml(str(p))
    ca, q, st = reg.resolve("save")
    assert ca == "GK_SAVE"
    assert st == "VALID"
    assert q["gk_holds"] is False


def test_registry_duplicate_alias_hard_fail(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text("""
- canonical_action: A
  aliases: [x]
  possession_effect: NEUTRAL
  allowed_states: [CONTESTED]
  fail_closed_default: UNVALIDATED
- canonical_action: B
  aliases: [x]
  possession_effect: NEUTRAL
  allowed_states: [CONTESTED]
  fail_closed_default: UNVALIDATED
""", encoding="utf-8")
    try:
        ActionRegistry.from_yaml(str(p))
        assert False, "expected RegistryError"
    except RegistryError:
        assert True


def test_parse_percent_scale_safe():
    assert parse_percent("85") == 0.85
    assert parse_percent("0.85") == 0.85
    assert parse_percent(0.85) == 0.85


def test_parse_percent_out_of_range():
    try:
        parse_percent("120")
        assert False, "expected ValueError"
    except ValueError:
        assert True


def test_missing_policy_event():
    r = validate_event_row({"actor_id": "1", "team_name": "X", "start_sec": 1.0, "end_sec": 2.0, "half": 1})
    assert r.status == "VALID"
    r2 = validate_event_row({"team_name": "X", "start_sec": 1.0, "end_sec": 2.0, "half": 1})
    assert r2.status == "UNVALIDATED"


def test_missing_policy_xlsx():
    r = validate_xlsx_row({"player_name": "A", "team_name": "B"})
    assert r.status == "VALID"
    r2 = validate_xlsx_row({"player_name": "", "team_name": "B"})
    assert r2.status == "UNVALIDATED"
