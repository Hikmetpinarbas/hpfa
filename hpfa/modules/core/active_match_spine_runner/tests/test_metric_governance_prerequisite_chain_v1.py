from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.active_match_spine_runner.src import metric_governance_prerequisite_chain as chain


def _step_name(command: list[str]) -> str:
    script = Path(command[1]).name
    return {
        "multiformat_file_inventory.py": "inventory",
        "csv_surface_reader_lite.py": "csv",
        "xlsx_surface_reader_lite.py": "xlsx",
        "xml_surface_reader_lite.py": "xml",
        "provider_alias_field_semantics_lite.py": "field_semantics",
        "provider_label_value_semantics_lite.py": "label_semantics",
        "cross_format_reconciliation_lite.py": "reconciliation",
    }[script]


def test_chain_materializes_governance_inputs_in_dependency_order(tmp_path, monkeypatch) -> None:
    active = tmp_path / "runtime" / "active_single_match" / "current"
    out = tmp_path / "out"
    root = tmp_path / "product"
    active.mkdir(parents=True)
    root.mkdir()
    observed: list[str] = []

    def fake_run(_root: Path, command: list[str]):
        name = _step_name(command)
        observed.append(name)
        out.mkdir(parents=True, exist_ok=True)
        (out / chain.STEP_OUTPUTS[name]).write_text(
            json.dumps({
                "module_id": f"{name}_v1",
                "status": "PASS",
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            }),
            encoding="utf-8",
        )
        return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "passed": True}

    monkeypatch.setattr(chain, "_run", fake_run)
    report = chain.run_metric_governance_prerequisite_chain(active, out, root)

    assert observed == [
        "inventory",
        "csv",
        "xlsx",
        "xml",
        "field_semantics",
        "label_semantics",
        "reconciliation",
    ]
    assert report["required_governance_inputs_ready"] is True
    assert report["status"] == "SMOKE_PASS"
    assert (out / "provider_label_value_semantics_lite_v1.json").is_file()
    assert (out / "cross_format_reconciliation_lite_v1.json").is_file()
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False


def test_chain_stops_fail_closed_when_a_producer_fails(tmp_path, monkeypatch) -> None:
    active = tmp_path / "runtime" / "active_single_match" / "current"
    out = tmp_path / "out"
    root = tmp_path / "product"
    active.mkdir(parents=True)
    root.mkdir()
    observed: list[str] = []

    def fake_run(_root: Path, command: list[str]):
        name = _step_name(command)
        observed.append(name)
        if name == "xml":
            return {"command": command, "returncode": 2, "stdout": "", "stderr": "boom", "passed": False}
        out.mkdir(parents=True, exist_ok=True)
        (out / chain.STEP_OUTPUTS[name]).write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "passed": True}

    monkeypatch.setattr(chain, "_run", fake_run)
    report = chain.run_metric_governance_prerequisite_chain(active, out, root)

    assert observed == ["inventory", "csv", "xlsx", "xml"]
    assert report["status"] == "FAIL_CLOSED"
    assert report["required_governance_inputs_ready"] is False
    assert report["hard_block_hits"] == ["metric_governance_prerequisite_step_failed:xml"]
    assert report["production_release"] is False


def test_review_required_upstream_is_visible_but_does_not_fake_truth(tmp_path, monkeypatch) -> None:
    active = tmp_path / "runtime" / "active_single_match" / "current"
    out = tmp_path / "out"
    root = tmp_path / "product"
    active.mkdir(parents=True)
    root.mkdir()

    def fake_run(_root: Path, command: list[str]):
        name = _step_name(command)
        out.mkdir(parents=True, exist_ok=True)
        status = "REVIEW_REQUIRED" if name == "label_semantics" else "PASS"
        (out / chain.STEP_OUTPUTS[name]).write_text(json.dumps({"status": status}), encoding="utf-8")
        return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "passed": True}

    monkeypatch.setattr(chain, "_run", fake_run)
    report = chain.run_metric_governance_prerequisite_chain(active, out, root)

    assert report["required_governance_inputs_ready"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert "metric_governance_prerequisite_review_required:label_semantics" in report["review_hits"]
    assert report["same_provider_multiformat_is_independent_support"] is False
    assert report["production_release"] is False
