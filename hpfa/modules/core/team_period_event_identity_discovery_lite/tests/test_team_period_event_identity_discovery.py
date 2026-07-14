from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team_period_event_identity_discovery import build_report, write_outputs


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


def _row(fmt: str, team: str, period: str, role: str, event_id: str, start: str, end: str, action: str) -> dict:
    return {
        "source_format": fmt,
        "row_surface_class": "EVENT_LIKE_SOURCE_CANDIDATE",
        "team_raw": team,
        "period_candidate": period,
        "source_role": role,
        "source_event_id_raw": event_id,
        "start_raw": start,
        "end_raw": end,
        "event_type_raw": action,
    }


def test_exact_pairing_is_partitioned_by_team_and_period(tmp_path):
    rows = [
        _row("csv", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("xml", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("csv", "B", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("xml", "B", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("csv", "A", "SECOND_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("xml", "A", "SECOND_HALF", "PLAYER", "1", "10", "11", "Pass"),
    ]
    report = build_report(_write(tmp_path, rows))
    assert report["provider_id_exact_pair_count"] == 3
    assert report["team_period_partition_count"] == 3
    assert report["canonical_event_count"] == "UNKNOWN"


def test_same_time_different_team_not_collapsed(tmp_path):
    rows = [
        _row("csv", "A", "FIRST_HALF", "PLAYER", "1", "20", "21", "Duel"),
        _row("xml", "A", "FIRST_HALF", "PLAYER", "1", "20", "21", "Duel"),
        _row("csv", "B", "FIRST_HALF", "PLAYER", "2", "20", "21", "Duel"),
        _row("xml", "B", "FIRST_HALF", "PLAYER", "2", "20", "21", "Duel"),
    ]
    report = build_report(_write(tmp_path, rows))
    assert report["assembled_same_role_pair_candidate_count"] == 2
    assert report["cross_team_same_time_window_count"] == 1


def test_temporal_action_pair_when_id_missing(tmp_path):
    rows = [
        _row("csv", "A", "FIRST_HALF", "PLAYER", "", "30", "31", "Shot"),
        _row("xml", "A", "FIRST_HALF", "PLAYER", "", "30", "31", "Shot"),
    ]
    report = build_report(_write(tmp_path, rows))
    assert report["provider_id_exact_pair_count"] == 0
    assert report["temporal_action_pair_count"] == 1


def test_xlsx_is_excluded(tmp_path):
    rows = [
        {
            "source_format": "xlsx",
            "row_surface_class": "AGGREGATE_VALIDATION",
            "team_raw": "A",
            "period_candidate": "FIRST_HALF",
            "source_role": "PLAYER",
        }
    ]
    report = build_report(_write(tmp_path, rows))
    assert report["eligible_csv_xml_trace_count"] == 0
    assert report["status"] == "FAIL_CLOSED"


def test_flat_phone_output_only(tmp_path):
    source = _write(tmp_path, [
        _row("csv", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("xml", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
    ])
    out = tmp_path / "Download" / "HPFA"
    report = write_outputs(source, out)
    assert report["status"] == "DISCOVERY_PASS"
    assert (out / "team_period_event_identity_discovery_lite_v1.json").exists()
    assert (out / "team_period_event_identity_discovery_lite_v1.txt").exists()


def test_nested_phone_output_rejected(tmp_path):
    source = _write(tmp_path, [
        _row("csv", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
        _row("xml", "A", "FIRST_HALF", "PLAYER", "1", "10", "11", "Pass"),
    ])
    bad = tmp_path / "Download" / "HPFA" / "nested"
    try:
        write_outputs(source, bad)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested output path was accepted")
