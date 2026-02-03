import pandas as pd
import pytest

from canon.definitions.master_schema import load_schema, default_schema_path
from canon.definitions.contract_validator import check_contract


def base_row():
    # HP-CDL v1.0.0 minimal valid row (20 cols)
    return {
        "match_id": "HP_OPTA_1",
        "event_id": "e1",
        "timestamp": 10.0,
        "period": 1,
        "x_norm": 10.0,
        "y_norm": 10.0,
        "provider": "opta",
        "schema_version": "1.0.0",

        "action_type": "PASS",
        "outcome": 1,
        "xT_value": None,
        "vaep_score": None,
        "player_id": "p1",

        "phase_id": 1,
        "sub_phase": None,
        "energy_pulse": None,
        "is_moment": 0,

        "popper_tag": "VALIDATED",
        "audit_flag": 0,
        "video_ref": None,
    }


@pytest.fixture
def schema():
    return load_schema(default_schema_path())


def test_happy_path_ok(schema):
    df = pd.DataFrame([base_row()])
    out, rep = check_contract(df, schema=schema)
    assert rep.ok() is True
    assert rep.quarantined_rows == 0
    assert len(rep.errors) == 0


def test_missing_required_column_fails(schema):
    r = base_row()
    r.pop("match_id")
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)
    assert rep.ok() is False
    assert any("missing required columns" in e for e in rep.errors)


def test_coordinate_out_of_bounds_fails(schema):
    r = base_row()
    r["x_norm"] = 999.0
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)
    assert rep.ok() is False
    assert any("x_norm outside pitch ontology" in e for e in rep.errors)


def test_phase_out_of_range_fails(schema):
    r = base_row()
    r["phase_id"] = 9
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)
    assert rep.ok() is False
    assert any("phase_id outside 1-6 range" in e for e in rep.errors)


def test_unmapped_action_type_quarantines_and_degrades(schema):
    r = base_row()
    r["action_type"] = "teleport_pass"  # invalid enum
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)

    assert rep.ok() is True  # not fatal
    assert rep.quarantined_rows == 1
    assert out.loc[0, "audit_flag"] in (True, 1)
    assert out.loc[0, "popper_tag"] == "LOW_CONFIDENCE"
    assert out.loc[0, "action_type"] == schema.enums["action_type"].fallback


def test_unmapped_popper_tag_quarantines_and_degrades(schema):
    r = base_row()
    r["popper_tag"] = "GOD_MODE"
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)

    assert rep.ok() is True  # not fatal; degrade to fallback
    assert rep.quarantined_rows == 1
    assert out.loc[0, "audit_flag"] in (True, 1)
    assert out.loc[0, "popper_tag"] == schema.enums["epistemic_tag"].fallback


def test_non_nullable_null_fails(schema):
    r = base_row()
    r["timestamp"] = None  # non-nullable
    df = pd.DataFrame([r])
    out, rep = check_contract(df, schema=schema)

    assert rep.ok() is False
    assert any("nulls in non-nullable columns" in e for e in rep.errors)
