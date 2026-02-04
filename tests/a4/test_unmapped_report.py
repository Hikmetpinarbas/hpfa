import json
from datetime import datetime, timezone
from pathlib import Path

from adapters.engine.unmapped_report import generate_unmapped_actions_report


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_report_exists_and_schema(tmp_path):
    out = generate_unmapped_actions_report(
        provider="hp_engine",
        quarantine_items=[
            {"reason": "UNMAPPED_ACTION", "provider_action": "X", "raw_event": {"a": 1}, "ts_utc": "Z"}
        ],
        reports_dir=tmp_path,
        now=datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    data = _read(out)
    assert data["provider"] == "hp_engine"
    assert data["generated_at_utc"].endswith("Z")
    assert data["unmapped_actions"][0]["provider_action"] == "X"


def test_sorting_count_desc_then_name(tmp_path):
    items = [
        {"reason": "UNMAPPED_ACTION", "provider_action": "B", "raw_event": {"i": 1}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"i": 2}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "B", "raw_event": {"i": 3}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"i": 4}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"i": 5}, "ts_utc": "Z"},
    ]
    out = generate_unmapped_actions_report(
        provider="hp_engine",
        quarantine_items=items,
        reports_dir=tmp_path,
        now=datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    rows = _read(out)["unmapped_actions"]
    assert [r["provider_action"] for r in rows] == ["A", "B"]
    assert [r["count"] for r in rows] == [3, 2]


def test_examples_capped_and_trimmed(tmp_path):
    long_str = "x" * 10000
    items = [
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"payload": long_str, "i": 1}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"payload": long_str, "i": 2}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"payload": long_str, "i": 3}, "ts_utc": "Z"},
        {"reason": "UNMAPPED_ACTION", "provider_action": "A", "raw_event": {"payload": long_str, "i": 4}, "ts_utc": "Z"},
    ]
    out = generate_unmapped_actions_report(
        provider="hp_engine",
        quarantine_items=items,
        reports_dir=tmp_path,
        now=datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    row = _read(out)["unmapped_actions"][0]
    assert row["count"] == 4
    assert len(row["examples"]) == 3

    for ex in row["examples"]:
        b = json.dumps(ex, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        assert len(b) <= 2048
