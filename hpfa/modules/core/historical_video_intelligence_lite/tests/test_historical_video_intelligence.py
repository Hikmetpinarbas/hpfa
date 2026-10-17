from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
MODULE = ROOT / "hpfa" / "modules" / "core" / "historical_video_intelligence_lite"
SRC = MODULE / "src"
TESTS = MODULE / "tests"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from counterfactual_layer import build_counterfactual, write_counterfactual  # noqa: E402
from evaluation import admit_capability, derive_reference_events, evaluate, load_bas_reference, match_events  # noqa: E402
from hpfa_export import SURFACE_CSV, SURFACE_DIR, apply_review, surface_rows  # noqa: E402
from hvi_contract import (  # noqa: E402
    COUNTERFACTUAL_LAYER,
    EXPERIMENTAL,
    NOT_SUPPORTED,
    SUPPORTED,
    VERIFIED_HUMAN,
    VERIFIED_REFERENCE,
    make_event,
    validate_event,
    wilson_interval,
)
from pipeline import resolve_capability, run  # noqa: E402
from rights_gate import evaluate_rights, require_processing  # noqa: E402
from stages import PipelineConfig  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

OPEN_MANIFEST = {
    "manifest_id": "fixture_v1",
    "video_id": "fixture_video",
    "rights_status": "OPEN_LICENSE",
    "license": "CC0-1.0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "attribution": "generated test fixture",
    "acquisition_method": "GENERATED_LOCALLY",
    "download_protection_circumvented": False,
    "publication_cleared": False,
}


def _event(event_type: str = "SET_PIECE_RESTART", t: float = 10.0, score: float = 0.5) -> dict:
    return make_event(
        source_video_id="v",
        source_fingerprint="fp",
        rights_manifest_id="m",
        event_type=event_type,
        video_time_s=t,
        detector_id="d",
        stage="B",
        score=score,
        time_uncertainty_s=1.0,
    )


# ------------------------------------------------------------- contract


def test_event_contract_defaults_are_claim_safe() -> None:
    ev = _event()
    assert validate_event(ev) == []
    assert ev["verification_status"] == "CANDIDATE"
    assert ev["team"] == "UNKNOWN" and ev["player"] == "UNKNOWN"
    assert ev["capability_status"] == NOT_SUPPORTED
    assert ev["score_basis"].startswith("UNCALIBRATED")
    assert ev["video_timestamp"] == "00:00:10.000"


def test_contract_rejects_tracking_fields_and_unbased_claims() -> None:
    ev = _event()
    ev["tracking_speed"] = 31.0
    ev["team"] = "Alpha"
    ev["verification_status"] = VERIFIED_HUMAN
    problems = validate_event(ev)
    assert "tracking_field_forbidden:tracking_speed" in problems
    assert "team_without_basis" in problems
    assert "verified_without_basis" in problems
    with pytest.raises(ValueError):
        make_event(source_video_id="v", source_fingerprint="f", rights_manifest_id="m", event_type="PRESSING", video_time_s=1, detector_id="d", stage="B", score=0, time_uncertainty_s=1)


def test_wilson_interval_bounds() -> None:
    lo, hi = wilson_interval(8, 10)
    assert 0.44 < lo < 0.5 and 0.94 < hi < 0.97
    assert wilson_interval(0, 0) is None


# ------------------------------------------------------------- rights


def test_rights_gate_fails_closed_without_cleared_basis() -> None:
    assert evaluate_rights(None)["processing_allowed"] is False
    unknown = OPEN_MANIFEST | {"rights_status": "UNKNOWN"}
    assert "rights_status_not_cleared:UNKNOWN" in evaluate_rights(unknown)["hard_block_hits"]
    bypass = OPEN_MANIFEST | {"download_protection_circumvented": True}
    assert evaluate_rights(bypass)["processing_allowed"] is False
    ripped = OPEN_MANIFEST | {"acquisition_method": "DOWNLOAD_PROTECTION_BYPASS"}
    assert evaluate_rights(ripped)["processing_allowed"] is False
    no_licence = OPEN_MANIFEST | {"license_url": ""}
    assert "open_license_without_license_reference" in evaluate_rights(no_licence)["hard_block_hits"]
    with pytest.raises(PermissionError):
        require_processing(unknown)


def test_processing_permission_is_not_publication_permission() -> None:
    verdict = evaluate_rights(OPEN_MANIFEST)
    assert verdict["processing_allowed"] is True
    assert verdict["publication_allowed"] is False
    assert verdict["legal_determination_made"] is False
    attested = OPEN_MANIFEST | {"rights_status": "OPERATOR_ATTESTED_LAWFUL_ACCESS", "attestation": ""}
    assert "operator_attestation_text_missing" in evaluate_rights(attested)["hard_block_hits"]


def test_historical_rights_review_manifests_fail_closed() -> None:
    folder = ROOT / "configs" / "historical_video" / "rights_review"
    manifests = sorted(folder.glob("*.json"))
    assert len(manifests) >= 2
    for path in manifests:
        verdict = evaluate_rights(json.loads(path.read_text(encoding="utf-8")))
        assert verdict["processing_allowed"] is False, path.name
        assert verdict["publication_allowed"] is False, path.name


# ------------------------------------------------------------- evaluation


def test_reference_derivation_adds_restarts_and_kickoff() -> None:
    raw = [
        {"idx": 0, "t": 10.0, "label": "Out", "team": "left", "player_id": None},
        {"idx": 1, "t": 30.0, "label": "Pass", "team": "right", "player_id": None},
        {"idx": 2, "t": 50.0, "label": "Goal", "team": "left", "player_id": "p9"},
        {"idx": 3, "t": 101.0, "label": "Pass", "team": "right", "player_id": None},
        {"idx": 4, "t": 120.0, "label": "Throw In", "team": "left", "player_id": None},
    ]
    refs = derive_reference_events(raw)
    kinds = sorted((r["event_type"], r["t"]) for r in refs)
    assert ("SET_PIECE_RESTART", 30.0) in kinds
    assert ("KICK_OFF", 101.0) in kinds
    assert ("GOAL", 50.0) in kinds
    assert ("THROW_IN", 120.0) in kinds and ("SET_PIECE_RESTART", 120.0) in kinds


def test_matching_is_one_to_one_and_tolerance_bound() -> None:
    cands = [_event(t=10.0, score=0.9), _event(t=11.0, score=0.8), _event(t=40.0, score=0.7)]
    refs = [{"ref_id": "r1", "t": 10.5, "event_type": "SET_PIECE_RESTART"}]
    pairs, fp, fn = match_events(cands, refs, 2.0)
    assert len(pairs) == 1 and len(fp) == 2 and not fn


def test_capability_admission_requires_evidence() -> None:
    per = {
        "SET_PIECE_RESTART": {"references": 40, "precision": 0.8, "recall": 0.75, "precision_wilson95": [0.66, 0.9], "recall_wilson95": [0.6, 0.86]},
        "GOAL": {"references": 2, "precision": 1.0, "recall": 1.0, "precision_wilson95": [0.34, 1.0], "recall_wilson95": [0.34, 1.0]},
        "SHOT": {"references": 20, "precision": 0.1, "recall": 0.05, "precision_wilson95": [0.0, 0.3], "recall_wilson95": [0.0, 0.2]},
    }
    cap = admit_capability(per)
    assert cap["SET_PIECE_RESTART"]["status"] == SUPPORTED
    assert cap["GOAL"]["status"] == EXPERIMENTAL
    assert cap["SHOT"]["status"] == NOT_SUPPORTED
    assert cap["BALL_RECOVERY"]["status"] == NOT_SUPPORTED


def test_supported_capability_does_not_transfer_across_domains() -> None:
    report = {"validated_domain": "PANORAMIC_FIXED_AMATEUR", "capability": {"SET_PIECE_RESTART": {"status": SUPPORTED}}}
    assert resolve_capability(report, "PANORAMIC_FIXED_AMATEUR")["SET_PIECE_RESTART"] == SUPPORTED
    assert resolve_capability(report, "BROADCAST_SD_ARCHIVE")["SET_PIECE_RESTART"] == EXPERIMENTAL
    assert resolve_capability(None, "X")["SHOT"] == NOT_SUPPORTED


def test_unknown_reference_label_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"annotations": [{"gameTime": "1 - 00:01", "position": "1000", "label": "Dribble Magic", "team": "left"}]}))
    with pytest.raises(ValueError, match="unknown_reference_label"):
        load_bas_reference(path, 1)


# ------------------------------------------------------------- review / export / counterfactual


def test_surface_export_keeps_candidates_out() -> None:
    cand = _event()
    assert surface_rows([cand]) == []
    cf = dict(cand, layer=COUNTERFACTUAL_LAYER)
    with pytest.raises(ValueError, match="non_observed_layer_row"):
        surface_rows([cf])


def test_human_review_requires_reviewer_and_records_basis(tmp_path: Path) -> None:
    a, b, c, d = _event(t=1), _event(t=2), _event(t=3), _event(t=4)
    tsv = tmp_path / "review.tsv"
    with tsv.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, delimiter="\t")
        w.writerow(["event_id", "decision", "corrected_event_type", "team", "player", "reviewer", "note"])
        w.writerow([a["event_id"], "CONFIRM", "", "Alpha", "", "analyst_1", ""])
        w.writerow([b["event_id"], "REJECT", "", "", "", "analyst_1", "camera close-up"])
        w.writerow([c["event_id"], "RELABEL", "THROW_IN", "", "", "analyst_1", ""])
        w.writerow([d["event_id"], "CONFIRM", "", "", "", "", "no reviewer"])
    rows, stats = apply_review([a, b, c, d], tsv)
    by = {r["event_id"]: r for r in rows}
    assert by[a["event_id"]]["verification_status"] == VERIFIED_HUMAN
    assert by[a["event_id"]]["team_basis"] == "HUMAN_REVIEW_VISUAL"
    assert by[b["event_id"]]["verification_status"] == "REJECTED"
    assert by[c["event_id"]]["event_type"] == "THROW_IN"
    assert by[d["event_id"]]["verification_status"] == "CANDIDATE"
    assert stats["invalid"] == [d["event_id"]]
    assert all(validate_event(r) == [] for r in rows)


def test_counterfactual_layer_is_separate(tmp_path: Path) -> None:
    ev = _event()
    cf = build_counterfactual([ev], [{"id": "A1", "statement": "modern pressing intensity"}], "Would this restart pattern survive today?")
    assert cf["layer"] == COUNTERFACTUAL_LAYER
    assert cf["numeric_projection_allowed"] is False
    assert cf["observed_basis"]["verified_event_ids"] == []
    with pytest.raises(ValueError):
        build_counterfactual([ev], [], "q")
    with pytest.raises(ValueError):
        write_counterfactual(tmp_path / "hpfa_surface", cf)
    path = write_counterfactual(tmp_path / "scenario", cf)
    assert path.exists()


# ------------------------------------------------------------- end-to-end on video


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory: pytest.TempPathFactory) -> dict:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    from synthetic_video import RESTARTS, STOPS, bas_reference_json, write_synthetic_video

    base = tmp_path_factory.mktemp("hvi")
    video = write_synthetic_video(base / "synthetic.mp4")
    ref = bas_reference_json(base / "synthetic_bas.json")
    return {"base": base, "video": video, "ref": ref, "restarts": RESTARTS, "stops": STOPS}


@needs_ffmpeg
def test_pipeline_blocks_uncleared_video_before_decoding(synthetic: dict) -> None:
    out = synthetic["base"] / "blocked"
    report = run(str(synthetic["video"]), OPEN_MANIFEST | {"rights_status": "NOT_CLEARED"}, str(out))
    assert report["status"] == "FAIL_CLOSED"
    assert not (out / "video_events_v1.json").exists()


@needs_ffmpeg
def test_two_stage_pipeline_recovers_scripted_restarts(synthetic: dict) -> None:
    out = synthetic["base"] / "run_candidates"
    report = run(str(synthetic["video"]), OPEN_MANIFEST, str(out), PipelineConfig())
    payload = json.loads((out / "video_events_v1.json").read_text(encoding="utf-8"))
    rows = payload["event_rows"]
    restarts = [r["video_time_s"] for r in rows if r["event_type"] == "SET_PIECE_RESTART"]
    for expected in synthetic["restarts"]:
        assert any(abs(t - expected) <= 2.0 for t in restarts), (expected, restarts)
    goals = [r for r in rows if r["event_type"] == "GOAL"]
    assert len(goals) == 1 and abs(goals[0]["video_time_s"] - synthetic["stops"][-1][0]) <= 3.0
    m = report["measurement"]
    assert m["stage_a"]["samples"] > 0 and m["stage_b"]["windows_random_audit"] >= 1
    assert m["stage_b"]["coverage_fraction"] < 1.0
    # No reference, no review: nothing is verified and the surface is empty.
    assert payload["verified_row_count"] == 0
    with (out / SURFACE_DIR / SURFACE_CSV).open(encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 0
    assert all(r["team"] == "UNKNOWN" and r["capability_status"] == NOT_SUPPORTED for r in rows)


@needs_ffmpeg
def test_reference_evaluation_verifies_and_measures(synthetic: dict) -> None:
    out = synthetic["base"] / "run_reference"
    refs = load_bas_reference(synthetic["ref"], 1)
    report = run(str(synthetic["video"]), OPEN_MANIFEST, str(out), PipelineConfig(), reference=refs, period="1")
    per = report["evaluation"]["per_event_type"]
    assert per["SET_PIECE_RESTART"]["recall"] == 1.0
    assert per["GOAL"]["true_positive"] == 1
    assert per["SHOT"]["recall"] == 0.0  # no ball/shot observation capability
    assert report["capability_from_this_run"]["capability"]["BALL_RECOVERY"]["status"] == NOT_SUPPORTED
    payload = json.loads((out / "video_events_v1.json").read_text(encoding="utf-8"))
    verified = [r for r in payload["event_rows"] if r["verification_status"] == VERIFIED_REFERENCE]
    assert verified and all(r["verification_basis"]["ref_id"] for r in verified)
    assert all(r["team_basis"].endswith("SIDE_LABEL_NOT_IDENTITY") for r in verified)


@needs_ffmpeg
def test_hpfa_integration_csv_surface_reader_accepts_verified_surface(synthetic: dict) -> None:
    out = synthetic["base"] / "run_integration"
    refs = load_bas_reference(synthetic["ref"], 1)
    run(str(synthetic["video"]), OPEN_MANIFEST, str(out), PipelineConfig(), reference=refs, period="1")
    surface_root = out / SURFACE_DIR

    inv_src = ROOT / "hpfa" / "modules" / "core" / "multiformat_file_inventory_lite" / "src"
    csv_src = ROOT / "hpfa" / "modules" / "core" / "csv_surface_reader_lite" / "src"
    for path in (inv_src, csv_src):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from csv_surface_reader import build_csv_surface_audit
    from multiformat_file_inventory import build_inventory

    inventory = build_inventory(surface_root)
    files = [f for f in inventory["files"] if f.get("extension") == ".csv"]
    assert len(files) == 1
    assert files[0]["source_role"] == "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE"

    audit = build_csv_surface_audit(surface_root, inventory)
    assert audit["status"] in {"PASS", "REVIEW_REQUIRED"}
    assert audit["hard_block_hits"] == []
    result = audit["files"][0]
    bundle = result["field_bundle"]
    assert bundle["team"] == "team" and bundle["action"] == "event_type"
    assert bundle["start"] == "start_time_s" and bundle["period"] == "period"
    assert result["time_audit"]["period_time_monotonic"] is True
    families = {a["raw_subtype"]: a["canonical_action_family_candidate"] for a in result["action_taxonomy"] if a["raw_type"] == "SET PIECE"}
    # Restart subtypes come from the reference labels and map to HPFA restart families.
    assert families.get("THROW IN") == "throw_in"
    assert families.get("FREE KICK") == "free_kick"
    assert families.get("KICK OFF") == "kick_off"
    assert result["team_binding"]["binding_status"] == "CANDIDATE_ONLY"
    assert audit["canonical_event_count"] == "UNKNOWN"


def test_no_sample_match_identity_leak() -> None:
    forbidden = ["Fenerbah", "Benfica", "Galatasaray", "Arsenal", "Real Madrid", "117092", "117093", "118575", "128057", "132831"]
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path.name
