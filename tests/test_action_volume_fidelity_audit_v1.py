from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

TOOL = Path(__file__).resolve().parents[1] / "tools" / "hpfa_action_volume_fidelity_audit_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("hpfa_action_volume_fidelity_audit_v1", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _xlsx(path: Path, header: list[str], rows: list[list[object]]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def _rebind(path: Path, counts: dict[str, int]) -> Path:
    path.write_text(json.dumps({"status": "REVIEW_REQUIRED", "eligible_action_family_candidate_counts": counts}), encoding="utf-8")
    return path


@pytest.fixture
def anchors(tmp_path):
    players = _xlsx(
        tmp_path / "players.xlsx",
        ["Player", "Passes", "Shots", "Lost balls"],
        [["A", 40, 2, 5], ["B", "-", 1, 3], ["C", 20, None, 2]],
    )
    keepers = _xlsx(tmp_path / "keepers.xlsx", ["Player", "Passes"], [["K", 10]])
    return [players, keepers]


def test_ratios_are_rows_over_provider_totals(tmp_path, anchors):
    tool = _load()
    rebind = _rebind(tmp_path / "rebind.json", {"PASS": 210, "SHOT": 9, "TURNOVER": 25, "DUEL": 40})
    out = tool.build_audit(rebind_path=rebind, anchor_paths=anchors)
    fam = {row["family"]: row for row in out["families"]}
    assert fam["PASS"]["provider_anchor_total"] == 70
    assert fam["PASS"]["row_to_anchor_ratio"] == 3.0
    assert fam["SHOT"]["provider_anchor_total"] == 3
    assert fam["TURNOVER"]["provider_anchor_total"] == 10
    assert fam["DUEL"]["provider_anchor_total"] is None
    assert fam["DUEL"]["row_to_anchor_ratio"] is None


def test_status_is_never_pass_and_claims_stay_bounded(tmp_path, anchors):
    tool = _load()
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 70}), anchor_paths=anchors)
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["claim_ceiling"] == "ROW_VOLUME_VS_PROVIDER_AGGREGATE_FIDELITY_ONLY"
    boundary = out["claim_boundary"]
    assert boundary["canonical_event_count"] == "UNKNOWN"
    assert boundary["true_action_count"] == "UNKNOWN"
    assert boundary["provider_aggregate_is_football_truth"] is False
    assert boundary["production_release"] is False


def test_differential_inflation_is_flagged(tmp_path, anchors):
    tool = _load()
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 245, "SHOT": 3, "TURNOVER": 10}), anchor_paths=anchors)
    diff = out["differential_inflation"]
    assert diff["family_count"] == 3
    assert diff["min_ratio"] == 1.0 and diff["max_ratio"] == 3.5
    assert diff["composition_bias_suspected"] is True


def test_uniform_ratios_do_not_flag_composition_bias(tmp_path, anchors):
    tool = _load()
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 140, "SHOT": 6, "TURNOVER": 20}), anchor_paths=anchors)
    assert out["differential_inflation"]["composition_bias_suspected"] is False


def test_unreviewed_alias_column_is_reported_not_summed(tmp_path):
    tool = _load()
    drifted = _xlsx(tmp_path / "drift.xlsx", ["Player", "Passes", "Loss balls"], [["A", 10, 7]])
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 30, "TURNOVER": 4}), anchor_paths=[drifted])
    fam = {row["family"]: row for row in out["families"]}
    assert fam["TURNOVER"]["provider_anchor_total"] is None
    assert out["unreviewed_alias_columns"] == [
        {"anchor": "drift.xlsx", "column": "Loss balls", "candidate_family": "TURNOVER", "mapping_status": "UNREVIEWED_ALIAS_NOT_SUMMED"}
    ]


def test_missing_rebind_fails_closed(tmp_path, anchors):
    tool = _load()
    out = tool.build_audit(rebind_path=tmp_path / "absent.json", anchor_paths=anchors)
    assert out["status"] == "FAIL_CLOSED"
    assert "REBIND_ARTEFACT_UNREADABLE" in out["blocks"]


def test_no_anchor_family_fails_closed(tmp_path):
    tool = _load()
    empty = _xlsx(tmp_path / "empty.xlsx", ["Player", "Minutes"], [["A", 90]])
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 10}), anchor_paths=[empty])
    assert out["status"] == "FAIL_CLOSED"
    assert "NO_ANCHOR_FAMILY_AVAILABLE" in out["blocks"]


def test_occurrence_bundle_count_is_located_with_json_path(tmp_path, anchors):
    tool = _load()
    occ = tmp_path / "occ.json"
    occ.write_text(json.dumps({"summary": {"action_occurrence_candidate_count": 812}}), encoding="utf-8")
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 70}), anchor_paths=anchors, occurrence_path=occ)
    bundle = out["occurrence_bundle"]
    assert bundle["action_occurrence_candidate_count"] == 812
    assert bundle["json_path"] == "summary.action_occurrence_candidate_count"
    assert bundle["family_split_available"] is False


def test_anchor_provenance_includes_sha256_and_per_column_totals(tmp_path, anchors):
    tool = _load()
    out = tool.build_audit(rebind_path=_rebind(tmp_path / "r.json", {"PASS": 70}), anchor_paths=anchors)
    first = out["inputs"]["anchors"][0]
    assert len(first["sha256"]) == 64
    assert first["column_totals"]["Passes"] == 60


def test_inputs_are_not_modified(tmp_path, anchors):
    tool = _load()
    rebind = _rebind(tmp_path / "r.json", {"PASS": 70})
    before = {p: p.read_bytes() for p in [rebind, *anchors]}
    tool.build_audit(rebind_path=rebind, anchor_paths=anchors)
    assert {p: p.read_bytes() for p in before} == before


def test_cli_writes_json_and_refuses_runtime_authority_output(tmp_path, anchors):
    tool = _load()
    rebind = _rebind(tmp_path / "r.json", {"PASS": 70})
    out_path = tmp_path / "audit.json"
    args = ["--rebind", str(rebind), "--out", str(out_path)]
    for anchor in anchors:
        args += ["--anchor-xlsx", str(anchor)]
    assert tool.main(args) == 0
    assert json.loads(out_path.read_text(encoding="utf-8"))["schema"] == "HPFA_ACTION_VOLUME_FIDELITY_AUDIT_V1"
    forbidden = tmp_path / "runtime" / "active_single_match" / "current" / "audit.json"
    assert tool.main(args[:-2] + ["--out", str(forbidden)]) == 2
    assert not forbidden.exists()


def test_tool_has_no_sample_match_identity():
    text = TOOL.read_text(encoding="utf-8").lower()
    for token in ("galatasaray", "trabzonspor", "kasimpasa", "besiktas", "kocaeli"):
        assert token not in text
