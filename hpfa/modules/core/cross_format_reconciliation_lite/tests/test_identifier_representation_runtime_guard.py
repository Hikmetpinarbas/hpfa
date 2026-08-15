from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
WRAPPER = ROOT / "cross_format_reconciliation_lite.py"


def load_wrapper():
    spec = importlib.util.spec_from_file_location("hpfa_cross_format_runtime_wrapper", WRAPPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_leading_zero_identifier_is_not_numeric_collapsed() -> None:
    module = load_wrapper()
    assert module.normalize_identifier_candidate("001") == "001"
    assert module.normalize_identifier_candidate("1") == "1"
    assert module.normalize_identifier_candidate("001") != module.normalize_identifier_candidate("1")


def test_decimal_like_identifier_is_not_numeric_collapsed() -> None:
    module = load_wrapper()
    assert module.normalize_identifier_candidate("1.0") == "1.0"
    assert module.normalize_identifier_candidate("1") == "1"
    assert module.normalize_identifier_candidate("1.0") != module.normalize_identifier_candidate("1")


def test_identifier_guard_only_trims_outer_whitespace() -> None:
    module = load_wrapper()
    assert module.normalize_identifier_candidate("  A-001  ") == "A-001"
    assert module.normalize_identifier_candidate("A-001") != module.normalize_identifier_candidate("a-001")


def test_missing_identifier_cannot_be_linkage_key() -> None:
    module = load_wrapper()
    for value in (None, "", "  ", "null", "NaN", "-"):
        assert module.normalize_identifier_candidate(value) is None


def test_measurement_fields_keep_existing_numeric_normalization() -> None:
    module = load_wrapper()
    assert module.runtime_norm_field("pos_x", "01.00") == "1"
    assert module.runtime_norm_field("start", "1.0") == "1"
    assert module.runtime_norm_field("id", "01.00") == "01.00"


def test_no_sample_match_identity_leak_in_identifier_runtime_guard() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    forbidden = ["Sturm Graz", "Heart of Midlothian", "Galatasaray", "Australia", "Turkey", "World Cup", "2062"]
    assert not any(token in source for token in forbidden)
