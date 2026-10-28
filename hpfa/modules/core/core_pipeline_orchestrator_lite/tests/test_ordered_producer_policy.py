from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "core_pipeline_orchestrator_lite" / "src"
sys.path.insert(0, str(SRC))

from core_pipeline_orchestrator import OrchestrationContractError, run_ordered_producer_steps


def test_ordered_producer_policy_stops_after_first_failed_step() -> None:
    called = {"third": False}

    def first() -> dict:
        return {"passed": True, "name": "first"}

    def second() -> dict:
        return {"passed": False, "name": "second"}

    def third() -> dict:
        called["third"] = True
        return {"passed": True, "name": "third"}

    steps = run_ordered_producer_steps([first, second, third])
    assert [row["name"] for row in steps] == ["first", "second"]
    assert called["third"] is False


def test_ordered_producer_policy_rejects_non_dict_step() -> None:
    try:
        run_ordered_producer_steps([lambda: []])  # type: ignore[list-item]
    except OrchestrationContractError as exc:
        assert str(exc) == "producer_step_must_be_dict"
    else:
        raise AssertionError("non-dict producer step was not rejected")
