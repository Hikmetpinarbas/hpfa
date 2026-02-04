import json
from pathlib import Path
import types
import importlib
import pytest

from motor_bridge.canon_reader import read_canon_json


def _write_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_read_canon_calls_validator_and_passes_when_ok(tmp_path, monkeypatch):
    # Patch contract validator with a permissive stub
    mod = importlib.import_module("canon.definitions.contract_validator")

    def ok_validator(payload):
        return True

    monkeypatch.setattr(mod, "validate_contract", ok_validator, raising=False)

    p = tmp_path / "canon.json"
    _write_json(
        p,
        {
            "epistemic_meta": {
                "epistemic_status": "VALIDATED",
                "lossy_mapping": False,
                "assumption_id": None,
                "human_override": False,
            }
        },
    )

    res = read_canon_json(p)
    assert res.epistemic_status == "VALIDATED"
    assert res.lossy_mapping is False
    assert res.assumption_id is None
    assert res.human_override is False
    assert isinstance(res.payload, dict)


def test_read_canon_fails_closed_on_invalid_contract(tmp_path, monkeypatch):
    mod = importlib.import_module("canon.definitions.contract_validator")

    def bad_validator(payload):
        raise ValueError("contract invalid")

    monkeypatch.setattr(mod, "validate_contract", bad_validator, raising=False)

    p = tmp_path / "canon.json"
    _write_json(
        p,
        {
            "epistemic_meta": {
                "epistemic_status": "VALIDATED",
            }
        },
    )

    with pytest.raises(ValueError):
        read_canon_json(p)


def test_read_canon_requires_epistemic_status(tmp_path, monkeypatch):
    mod = importlib.import_module("canon.definitions.contract_validator")

    def ok_validator(payload):
        return True

    monkeypatch.setattr(mod, "validate_contract", ok_validator, raising=False)

    p = tmp_path / "canon.json"
    _write_json(
        p,
        {
            "epistemic_meta": {
                # epistemic_status missing
                "lossy_mapping": False
            }
        },
    )

    with pytest.raises(ValueError):
        read_canon_json(p)
