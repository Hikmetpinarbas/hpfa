import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULES = ROOT / "hpfa" / "modules" / "core"
PACKET_SRC = MODULES / "composite_evidence_packet_builder_lite" / "src"
FUSION_SRC = MODULES / "multi_signal_evidence_fusion_lite" / "src"
for src in [str(FUSION_SRC), str(PACKET_SRC)]:
    if src not in sys.path:
        sys.path.insert(0, src)

from composite_evidence_packet_builder import build_composite_packet
from multi_signal_evidence_fusion import fuse_packet


def independent_signal(signal_id, provenance_root, dependency_group, independence_group):
    return {
        "signal_id": signal_id,
        "source_surface": f"surface_{signal_id}",
        "provenance_root": provenance_root,
        "dependency_group": dependency_group,
        "independence_group": independence_group,
        "independent_support_vote": True,
    }


def packet_with_two_supports():
    candidate = {
        "packet_family": "progression",
        "input_features": [],
        "input_windows": [],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": [
            independent_signal("real-a", "root-a", "dep-a", "ind-a"),
            independent_signal("real-b", "root-b", "dep-b", "ind-b"),
        ],
        "contradicting_signals": [],
        "claim_ceiling": "composite_candidate_only",
    }
    return build_composite_packet(candidate)


def _forge_support_ledger_refs(packet, refs):
    forged = []
    ref_iter = iter(refs)
    for row in packet["dependency_ledger"]:
        clone = dict(row)
        if clone["group_name"] == "supporting_signals":
            clone["ref_id"] = next(ref_iter)
        forged.append(clone)
    packet["dependency_ledger"] = forged


def test_forged_preserved_refs_and_matching_forged_ledger_fail_closed():
    packet = packet_with_two_supports()
    forged_records = [dict(row) for row in packet["supporting_signal_records"]]
    for idx, row in enumerate(forged_records):
        row["signal_id"] = f"invented-{idx}"
        row["signal_ref"] = f"invented-{idx}"
    packet["supporting_signal_records"] = forged_records
    _forge_support_ledger_refs(packet, ["invented-0", "invented-1"])

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_preserved_signal_ref_binding_mismatch:supporting_signals" in fusion["hard_block_hits"]
    support_refs = {
        row["signal_ref"]
        for row in fusion["relation_records"]
        if row["relation_type"] == "SUPPORTS"
    }
    assert support_refs == {"real-a", "real-b"}


def test_extra_preserved_signal_record_fails_closed():
    packet = packet_with_two_supports()
    packet["supporting_signal_records"].append(
        independent_signal("extra-c", "root-c", "dep-c", "ind-c") | {"signal_ref": "extra-c"}
    )

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_preserved_signal_ref_binding_mismatch:supporting_signals" in fusion["hard_block_hits"]


def test_preserved_signal_multiplicity_mismatch_fails_closed():
    packet = packet_with_two_supports()
    first = dict(packet["supporting_signal_records"][0])
    packet["supporting_signal_records"] = [first, dict(first)]

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_preserved_signal_ref_binding_mismatch:supporting_signals" in fusion["hard_block_hits"]


def test_valid_preserved_records_enrich_lineage_without_replacing_identity():
    packet = packet_with_two_supports()
    fusion = fuse_packet(packet)

    assert fusion["decision"] == "READY_FOR_ARGUMENT_SUPPORT"
    assert fusion["hard_block_hits"] == []
    support_rows = [row for row in fusion["relation_records"] if row["relation_type"] == "SUPPORTS"]
    assert {row["signal_ref"] for row in support_rows} == {"real-a", "real-b"}
    assert {row["provenance_root"] for row in support_rows} == {"root-a", "root-b"}
    assert fusion["independent_support_count"] == 2


def test_no_sample_match_identity_leak():
    source = (FUSION_SRC / "multi_signal_evidence_fusion.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
        assert token not in source
