import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "time_scale_router_lite" / "src"
sys.path.insert(0, str(SRC))

from time_scale_router import build_report, route_window, write_outputs


def write_windows(path: Path, windows):
    path.write_text(json.dumps({
        "module_id": "event_window_builder_lite_v1",
        "event_window_count": len(windows),
        "event_windows_sample": windows,
    }, ensure_ascii=False), encoding="utf-8")


def base_window(**overrides):
    item = {
        "window_id": "win_0000",
        "window_axis": "minute",
        "surface_row_count": 30,
        "context_density": 6.0,
        "window_confidence": "high",
        "terminal_action_surface_present": False,
        "loss_recovery_surface_present": False,
        "restart_surface_present": False,
    }
    item.update(overrides)
    return item


def test_routes_minute_axis_usable_windows():
    routed = route_window(base_window())
    assert routed["routing_decision"] == "MINUTE_AXIS_USABLE"
    assert routed["signal_density_candidate"] == "HIGH_SIGNAL_DENSITY"
    assert routed["claim_allowed"] is False


def test_routes_low_density_minute_windows():
    routed = route_window(base_window(surface_row_count=12, context_density=2.4, window_confidence="medium"))
    assert routed["routing_decision"] == "MINUTE_AXIS_LOW_DENSITY"
    assert routed["signal_density_candidate"] == "LOW_SIGNAL_DENSITY"


def test_routes_event_index_fallback_windows():
    routed = route_window(base_window(window_axis="event_index", surface_row_count=100, context_density=1.0))
    assert routed["routing_decision"] == "EVENT_INDEX_FALLBACK_ONLY"
    assert routed["signal_density_candidate"] == "EVENT_INDEX_DENSITY_ONLY"


def test_claim_boundaries_remain_false(tmp_path):
    write_windows(tmp_path / "event_window_builder_lite_v1.json", [base_window()])
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False
    assert report["rhythm_truth"] is False
    assert report["time_window_truth"] is False
    assert report["claim_allowed"] is False


def test_flat_phone_outputs(tmp_path):
    write_windows(tmp_path / "event_window_builder_lite_v1.json", [base_window()])
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "time_scale_router_lite_v1.json").exists()
    assert (out / "time_scale_router_lite_v1.txt").exists()
    assert report["claim_safety"] == "TIME_SCALE_CANDIDATE_ONLY"


def test_no_sample_match_identity_leak():
    src = (SRC / "time_scale_router.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "time_scale_router_lite_v1.md").read_text(encoding="utf-8")
    root_cli = (ROOT / "time_scale_router.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in src
        assert token not in contract
        assert token not in root_cli
