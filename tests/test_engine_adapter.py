"""
Tests for adapters/engine/engine_adapter.py

Uses a tmp action map file — does not depend on HPFA_REPORTS_DIR or any
side-effect-producing env var, so tests are hermetic.
"""
import json
import tempfile
import os
from pathlib import Path

import pytest

from adapters.engine.engine_adapter import adapt_engine_events, CanonEvent
from adapters.engine.quarantine import QuarantineItem
from canon.epistemic_meta import CanonMeta, EpistemicStatus


# --- helpers ---

_MAP = {
    "PASS": {
        "canon_action": "PASS",
        "lossy": False,
        "assumption_id": "00000000-0000-0000-0000-000000000001",
    },
    "PRESSURE": {
        "canon_action": "PRESSURE",
        "lossy": True,
        "assumption_id": "00000000-0000-0000-0000-000000000003",
    },
}


def _write_map(tmp_dir: str, content: dict = _MAP) -> str:
    path = os.path.join(tmp_dir, "engine_action_map.json")
    Path(path).write_text(json.dumps(content), encoding="utf-8")
    return path


# --- canonical routing ---

def test_mapped_lossless_action_becomes_canon_event_with_fact_status():
    with tempfile.TemporaryDirectory() as d:
        ev = {"action": "PASS", "team_id": 1, "event_start_time": 1.0}
        canon, quarantine = adapt_engine_events([ev], _write_map(d))

    assert len(canon) == 1
    assert len(quarantine) == 0
    ce = canon[0]
    assert isinstance(ce, CanonEvent)
    assert ce.action == "PASS"
    assert isinstance(ce.meta, CanonMeta)
    assert ce.meta.epistemic_status == EpistemicStatus.FACT
    assert ce.meta.lossy_mapping is False


def test_mapped_lossy_action_becomes_signal_status():
    with tempfile.TemporaryDirectory() as d:
        ev = {"action": "PRESSURE", "team_id": 2, "event_start_time": 5.0}
        canon, quarantine = adapt_engine_events([ev], _write_map(d))

    assert len(canon) == 1
    assert canon[0].meta.epistemic_status == EpistemicStatus.SIGNAL
    assert canon[0].meta.lossy_mapping is True


# --- quarantine paths ---

def test_unmapped_action_goes_to_quarantine():
    with tempfile.TemporaryDirectory() as d:
        ev = {"action": "UNKNOWN_ACTION_XYZ", "team_id": 1, "event_start_time": 1.0}
        canon, quarantine = adapt_engine_events([ev], _write_map(d))

    assert len(canon) == 0
    assert len(quarantine) == 1
    qi = quarantine[0]
    assert isinstance(qi, QuarantineItem)
    assert qi.reason == "UNMAPPED_ACTION"
    assert qi.provider_action == "UNKNOWN_ACTION_XYZ"


def test_missing_action_field_goes_to_quarantine_as_missing():
    with tempfile.TemporaryDirectory() as d:
        ev = {"team_id": 1, "event_start_time": 1.0}  # no "action" key
        canon, quarantine = adapt_engine_events([ev], _write_map(d))

    assert len(canon) == 0
    assert len(quarantine) == 1
    assert quarantine[0].reason == "MISSING_ACTION"
    assert quarantine[0].provider_action == "__MISSING__"


def test_empty_action_string_goes_to_quarantine():
    with tempfile.TemporaryDirectory() as d:
        ev = {"action": "   ", "team_id": 1, "event_start_time": 1.0}
        canon, quarantine = adapt_engine_events([ev], _write_map(d))

    assert len(canon) == 0
    assert len(quarantine) == 1
    assert quarantine[0].reason == "MISSING_ACTION"


# --- mixed batch ---

def test_mixed_batch_routes_correctly():
    with tempfile.TemporaryDirectory() as d:
        events = [
            {"action": "PASS", "team_id": 1, "event_start_time": 0.0},
            {"action": "NO_MAP", "team_id": 1, "event_start_time": 1.0},
            {"action": "PRESSURE", "team_id": 2, "event_start_time": 2.0},
            {"action": "", "team_id": 1, "event_start_time": 3.0},
        ]
        canon, quarantine = adapt_engine_events(events, _write_map(d))

    assert len(canon) == 2
    assert len(quarantine) == 2
    assert {ce.action for ce in canon} == {"PASS", "PRESSURE"}


# --- payload passthrough ---

def test_original_event_preserved_in_canon_event_payload():
    with tempfile.TemporaryDirectory() as d:
        ev = {"action": "PASS", "team_id": 99, "event_start_time": 7.5, "extra": "data"}
        canon, _ = adapt_engine_events([ev], _write_map(d))

    assert canon[0].payload["team_id"] == 99
    assert canon[0].payload["extra"] == "data"


# --- empty input ---

def test_empty_event_list_returns_empty_results():
    with tempfile.TemporaryDirectory() as d:
        canon, quarantine = adapt_engine_events([], _write_map(d))

    assert canon == []
    assert quarantine == []
