import json
from pathlib import Path
import importlib
import pytest

from motor_bridge.canon_reader import read_canon_json


def _write_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _any_allowed_status() -> str:
    mod = importlib.import_module("canon.epistemic_meta")
    enum_obj = getattr(mod, "EpistemicStatus")
    return next(iter([x.value for x in enum_obj]))


def test_read_canon_calls_validator_and_passes_when_ok(tmp_path, monkeypatch):
    mod = importlib.import_module("canon.definitions.contract_validator")
    monkeypatch.setattr(mod, "validate_contract", lambda payload: True, raising=False)

    status = _any_allowed_status()

    p = tmp_path / "canon.json"
    _write_json(
        p,
        {
            "epistemic_meta": {
                "epistemic_status": status,
                "lossy_mapping": False,
                "assumption_id": None,
                "human_override": False,
            }
        },
    )

    res = read_canon_json(p)
    assert res.epistemic_status == status
    assert res.decision == "ACCEPT"
    assert "policy OK" in res.decision_reason
    assert isinstance(res.payload, dict)


def test_read_canon_fails_closed_on_invalid_contract(tmp_path, monkeypatch):
    mod = importlib.import_module("canon.definitions.contract_validator")

    def bad_validator(payload):
        raise ValueError("contract invalid")

    monkeypatch.setattr(mod, "validate_contract", bad_validator, raising=False)

    status = _any_allowed_status()

    p = tmp_path / "canon.json"
    _write_json(p, {"epistemic_meta": {"epistemic_status": status}})

    with pytest.raises(ValueError):
        read_canon_json(p)


def test_read_canon_requires_epistemic_status(tmp_path, monkeypatch):
    mod = importlib.import_module("canon.definitions.contract_validator")
    monkeypatch.setattr(mod, "validate_contract", lambda payload: True, raising=False)

    p = tmp_path / "canon.json"
    _write_json(p, {"epistemic_meta": {"lossy_mapping": False}})

    with pytest.raises(ValueError):
        read_canon_json(p)
