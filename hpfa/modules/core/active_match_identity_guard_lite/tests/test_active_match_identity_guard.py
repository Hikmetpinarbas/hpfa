import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_identity_guard_lite" / "src"
sys.path.insert(0, str(SRC))

from active_match_identity_guard import build_report, write_outputs


def make_match(tmp_path: Path, label: str = "Alpha 1-0 Beta", date: str = "2026-01-01") -> Path:
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    (match / f"{label} {date}, Full match Teams.csv").write_text(
        "ID;start;end;code;team;action;half;pos_x;pos_y\n1;0.0;1.0;P;Alpha;Pass;1;10;20\n",
        encoding="utf-8",
    )
    (match / f"{label} {date}, Full match Players.xml").write_text(
        "<root><event><start>0.0</start><end>1.0</end><half>1</half><team>Alpha</team><action>Pass</action></event></root>",
        encoding="utf-8",
    )
    return match


def make_manifest(tmp_path: Path, label: str = "Alpha 1-0 Beta", date: str = "2026-01-01") -> Path:
    manifest = tmp_path / "declared_match_manifest.json"
    manifest.write_text(
        json.dumps({"match_label": label, "date": date, "competition": "Example Cup"}, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def test_runtime_identity_drift_blocks_active_match_evidence_pass(tmp_path):
    match = make_match(tmp_path, label="Alpha 1-0 Beta", date="2026-01-01")
    manifest = make_manifest(tmp_path, label="Gamma 2-0 Delta", date="2026-02-02")

    report = build_report(match, manifest)

    assert report["status"] == "FAIL_CLOSED"
    assert report["identity_match_status"] == "RUNTIME_IDENTITY_DRIFT_DETECTED"
    assert report["active_match_evidence_allowed"] is False
    assert "match_label_contradiction" in report["identity_reasons"]


def test_missing_manifest_returns_review_required(tmp_path):
    match = make_match(tmp_path)

    report = build_report(match)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["identity_match_status"] == "UNKNOWN_OR_REVIEW_REQUIRED"
    assert report["active_match_evidence_allowed"] is False


def test_compatible_identity_still_requires_review(tmp_path):
    match = make_match(tmp_path, label="Alpha 1-0 Beta", date="2026-01-01")
    manifest = make_manifest(tmp_path, label="Alpha 1-0 Beta", date="2026-01-01")

    report = build_report(match, manifest)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["identity_match_status"] == "ACTIVE_MATCH_IDENTITY_COMPATIBLE_REVIEW_REQUIRED"
    assert report["active_match_evidence_allowed"] is True
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["claim_boundary"]["tactical_truth"] is False


def test_write_outputs_flat_and_claim_safe(tmp_path):
    match = make_match(tmp_path)
    out = tmp_path / "HPFA"

    report = write_outputs(match, out, root=ROOT)

    assert (out / "active_match_identity_guard_lite_v1.json").exists()
    assert (out / "active_match_identity_guard_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())
    assert report["claim_safety"] == "RUNTIME_IDENTITY_CHECK_ONLY"
    assert "tactical truth" in report["blocked_claims"]


def test_nested_phone_output_directory_is_rejected(tmp_path):
    match = make_match(tmp_path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(match, "/sdcard/Download/HPFA/identity", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "active_match_identity_guard.py").read_text(encoding="utf-8")
    wrapper = (ROOT / "active_match_identity_guard.py").read_text(encoding="utf-8")
    forbidden = [
        "Australia",
        "Turkey",
        "United States",
        "World Cup",
        "13.06.2026",
        "25.06.2026",
    ]
    for token in forbidden:
        assert token not in src
        assert token not in wrapper
