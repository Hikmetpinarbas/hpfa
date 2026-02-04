import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from adapters.engine.mapping_coverage import generate_mapping_coverage_report


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_mapping_coverage_schema_sort_and_math(tmp_path):
    reports_dir = tmp_path / "reports"
    mappings_dir = tmp_path / "mappings"
    reports_dir.mkdir()
    mappings_dir.mkdir()

    # mapped_types = 3
    (mappings_dir / "engine_action_map.json").write_text(
        json.dumps({"A": {"x": 1}, "B": {"x": 2}, "C": {"x": 3}}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    # unmapped_types = 4 (rows)
    (reports_dir / "unmapped_actions.json").write_text(
        json.dumps(
            {
                "provider": "hp_engine",
                "generated_at_utc": "2026-02-04T00:00:00Z",
                "unmapped_actions": [
                    {"provider_action": "zzz", "count": 5, "examples": []},
                    {"provider_action": "aaa", "count": 5, "examples": []},
                    {"provider_action": "bbb", "count": 9, "examples": []},
                    {"provider_action": "ccc", "count": 1, "examples": []},
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out = generate_mapping_coverage_report(
        provider="hp_engine",
        mappings_path=mappings_dir / "engine_action_map.json",
        unmapped_report_path=reports_dir / "unmapped_actions.json",
        output_path=reports_dir / "mapping_coverage.json",
        now=datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc),
    )

    data = _read(out)
    assert data["provider"] == "hp_engine"
    assert data["generated_at_utc"].endswith("Z")

    m = data["mapping"]
    assert m["mapped_actions"] == 3
    assert m["unmapped_actions"] == 4
    assert m["total_observed_actions"] == 7
    assert m["coverage_ratio"] == pytest.approx(3 / 7, rel=1e-12, abs=0.0)

    # top_unmapped: count desc then action asc (tie on 5 => aaa before zzz)
    assert [x["provider_action"] for x in data["top_unmapped"]] == ["bbb", "aaa", "zzz", "ccc"]
    assert [x["count"] for x in data["top_unmapped"]] == [9, 5, 5, 1]


def test_top10_cap(tmp_path):
    reports_dir = tmp_path / "reports"
    mappings_dir = tmp_path / "mappings"
    reports_dir.mkdir()
    mappings_dir.mkdir()

    (mappings_dir / "engine_action_map.json").write_text(
        json.dumps({"M1": 1}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    unmapped_rows = [{"provider_action": f"a{i:02d}", "count": i, "examples": []} for i in range(1, 30)]
    (reports_dir / "unmapped_actions.json").write_text(
        json.dumps(
            {"provider": "hp_engine", "generated_at_utc": "2026-02-04T00:00:00Z", "unmapped_actions": unmapped_rows},
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out = generate_mapping_coverage_report(
        provider="hp_engine",
        mappings_path=mappings_dir / "engine_action_map.json",
        unmapped_report_path=reports_dir / "unmapped_actions.json",
        output_path=reports_dir / "mapping_coverage.json",
        now=datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    data = _read(out)

    assert len(data["top_unmapped"]) == 10
    assert [x["count"] for x in data["top_unmapped"]] == list(range(29, 19, -1))
