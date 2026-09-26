from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "brand" / "HPFA_ANALYST_VISUALIZATION_POLICY_V1.md"


def test_visualization_policy_preserves_claim_boundary() -> None:
    text = POLICY.read_text(encoding="utf-8")
    required = [
        "action coordinate != player position",
        "coordinate != tracking",
        "same timestamp != ordered sequence",
        "model value != fact",
        "visual prominence != confidence",
        "production_release=false",
    ]
    for value in required:
        assert value in text


def test_visualization_policy_blocks_physical_proxy_renaming() -> None:
    text = POLICY.read_text(encoding="utf-8")
    for construct in [
        "true team shape",
        "compactness",
        "pitch control",
        "pressure geometry",
        "true player/ball speed",
        "coach intention",
        "tactical dominance",
        "causality",
    ]:
        assert construct in text
    assert "A proxy never inherits the physical/tactical construct name." in text


def test_historical_graphics_pack_and_match_data_are_not_current_product_surfaces() -> None:
    assert not (ROOT / "graphics_pack").exists()
    assert not (ROOT / "data" / "keepbox").exists()
    assert not (ROOT / "data" / "quarantine").exists()
