from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "xlsx_surface_reader_lite" / "src"
sys.path.insert(0, str(SRC))

from xlsx_header_semantics import semantic_header_norm


def load_product_entrypoint():
    entrypoint = ROOT / "xlsx_surface_reader_lite.py"
    spec = importlib.util.spec_from_file_location("xlsx_product_entrypoint", entrypoint)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_percent_marker_preserves_distinct_semantic_header() -> None:
    assert semantic_header_norm("Passes accurate") == "passes_accurate"
    assert semantic_header_norm("Passes accurate, %") == "passes_accurate_percent"
    assert semantic_header_norm("Shots saved") != semantic_header_norm("Shots saved, %")


def test_product_entrypoint_avoids_false_duplicate_header_review(tmp_path: Path) -> None:
    workbook_path = tmp_path / "players.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Main statistics"
    sheet.append(
        [
            "Player",
            "Team",
            "Passes accurate",
            "Passes accurate, %",
            "Shots on target",
            "Shots on target, %",
        ]
    )
    sheet.append(["Alpha", "Side A", 40, 80, 2, 50])
    workbook.save(workbook_path)

    inventory = {
        "files": [
            {
                "file_id": "xlsx_a",
                "relative_path": workbook_path.name,
                "extension": ".xlsx",
                "sha256": "candidate_sha",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
            }
        ]
    }

    product = load_product_entrypoint()
    payload = product.xlsx_surface_reader.build_xlsx_surface_audit(
        tmp_path,
        inventory,
    )
    sheet_audit = payload["files"][0]["sheets"][0]

    assert payload["status"] == "PASS"
    assert sheet_audit["status"] == "PASS"
    assert sheet_audit["duplicate_column_names"] == []
    assert sheet_audit["normalized_columns"] == [
        "player",
        "team",
        "passes_accurate",
        "passes_accurate_percent",
        "shots_on_target",
        "shots_on_target_percent",
    ]
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_no_sample_match_identity_leak() -> None:
    text = (SRC / "xlsx_header_semantics.py").read_text(encoding="utf-8").casefold()
    forbidden = [
        "australia",
        "turkey",
        "galatasaray",
        "fenerbahce",
        "13.06.2026",
    ]
    assert not any(token in text for token in forbidden)
