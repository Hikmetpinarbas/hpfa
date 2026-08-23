import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
PACKET_SRC = ROOT / "hpfa" / "modules" / "core" / "composite_evidence_packet_builder_lite" / "src"
FUSION_SRC = ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "src"
sys.path.insert(0, str(PACKET_SRC))
sys.path.insert(0, str(FUSION_SRC))

from composite_evidence_packet_builder import build_composite_packet
from multi_signal_evidence_fusion import fuse_packet


def candidate_with_explicit_contradiction():
    return {
        "packet_family": "progression",
        "input_features": [
            {"feature_id": "feature_generic_001", "source_surface": "feature_surface"},
        ],
        "input_windows": [
            {"window_id": "window_generic_001", "source_surface": "window_surface"},
        ],
        "supporting_signals": [
            {"signal_id": "support_generic_001", "source_surface": "support_surface"},
        ],
        "contradicting_signals": [
            {
                "signal_id": "counter_generic_001",
                "source_surface": "counter_surface",
                "relation_type": "CONTRADICTS",
                "contradiction_basis": "same_construct_same_window_opposite_direction_candidate",
            }
        ],
        "claim_ceiling": "composite_candidate_only",
    }


def test_packet_preserves_signal_metadata_alongside_legacy_refs():
    packet = build_composite_packet(candidate_with_explicit_contradiction())
    assert packet["status"] == "SMOKE_PASS"
    assert packet["supporting_signals"] == ["support_generic_001"]
    assert packet["contradicting_signals"] == ["counter_generic_001"]
    assert packet["supporting_signal_records"][0]["signal_ref"] == "support_generic_001"
    counter = packet["contradicting_signal_records"][0]
    assert counter["signal_ref"] == "counter_generic_001"
    assert counter["relation_type"] == "CONTRADICTS"
    assert counter["contradiction_basis"] == "same_construct_same_window_opposite_direction_candidate"


def test_fusion_consumes_packet_builder_explicit_contradiction_metadata():
    packet = build_composite_packet(candidate_with_explicit_contradiction())
    fusion = fuse_packet(packet)
    assert fusion["fusion_status"] == "MIXED_WITH_EXPLICIT_CONTRADICTION"
    assert fusion["contradiction_signal_count"] == 1
    rows = [row for row in fusion["relation_records"] if row["signal_ref"] == "counter_generic_001"]
    assert len(rows) == 1
    assert rows[0]["relation_type"] == "CONTRADICTS"
    assert rows[0]["relation_basis"] == "same_construct_same_window_opposite_direction_candidate"


def test_non_explicit_counter_signal_remains_qualifier():
    candidate = candidate_with_explicit_contradiction()
    candidate["contradicting_signals"] = [
        {"signal_id": "tension_generic_001", "source_surface": "counter_surface"}
    ]
    packet = build_composite_packet(candidate)
    fusion = fuse_packet(packet)
    assert fusion["contradiction_signal_count"] == 0
    assert fusion["qualifier_signal_count"] == 1
    assert fusion["fusion_status"] == "SUPPORTED_WITH_QUALIFIER"


def test_canonical_event_count_stays_unknown():
    packet = build_composite_packet(candidate_with_explicit_contradiction())
    fusion = fuse_packet(packet)
    assert packet["canonical_event_count"] == "UNKNOWN"
    assert fusion["canonical_event_count"] == "UNKNOWN"


def test_no_sample_match_identity_leak():
    for path in [
        PACKET_SRC / "composite_evidence_packet_builder.py",
        FUSION_SRC / "multi_signal_evidence_fusion.py",
    ]:
        source = path.read_text(encoding="utf-8")
        for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
            assert token not in source
