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


def evidence(ref_id, root, dep, ind):
    return {
        "ref_id": ref_id,
        "source_surface": f"surface_{ref_id}",
        "provenance_root": root,
        "dependency_group": dep,
        "independence_group": ind,
        "independent_support_vote": True,
    }


def signal(ref_id, root, dep, ind):
    row = evidence(ref_id, root, dep, ind)
    row["signal_id"] = row.pop("ref_id")
    return row


def test_feature_lineage_is_preserved_and_bound():
    packet = build_composite_packet({
        "packet_family": "progression",
        "claim_ceiling": "composite_candidate_only",
        "input_features": [evidence("f1", "root-f", "dep-f", "ind-f")],
        "supporting_signals": [signal("s1", "root-s", "dep-s", "ind-s")],
    })
    assert packet["input_feature_records"][0]["provenance_root"] == "root-f"
    fused = fuse_packet(packet)
    assert fused["decision"] == "READY_FOR_ARGUMENT_SUPPORT"
    assert fused["hard_block_hits"] == []


def test_unbound_feature_ledger_lineage_cannot_create_support():
    packet = build_composite_packet({
        "packet_family": "progression",
        "claim_ceiling": "composite_candidate_only",
        "input_features": [evidence("f1", "root-f", "dep-f", "ind-f")],
        "supporting_signals": [signal("s1", "root-s", "dep-s", "ind-s")],
    })
    forged = dict(packet)
    forged.pop("input_feature_records")
    forged["dependency_ledger"] = [dict(row) for row in packet["dependency_ledger"]]
    for row in forged["dependency_ledger"]:
        if row["group_name"] == "input_features":
            row["provenance_root"] = "invented-root"
            row["dependency_group"] = "invented-dep"
            row["independence_group"] = "invented-ind"
    fused = fuse_packet(forged)
    assert fused["decision"] == "BLOCK_FUSION"
    assert "upstream_dependency_ledger_lineage_unbound:input_features:f1" in fused["hard_block_hits"]


def test_duplicate_identity_conflicting_lineage_fails_closed_in_builder():
    packet = build_composite_packet({
        "packet_family": "progression",
        "claim_ceiling": "composite_candidate_only",
        "supporting_signals": [
            signal("dup", "root-a", "dep-a", "ind-a"),
            signal("dup", "root-b", "dep-b", "ind-b"),
        ],
    })
    assert packet["decision"] == "BLOCK_PACKET"
    assert "independent_support_claim_not_proven" in packet["hard_block_hits"]
    assert "conflicting_lineage_for_evidence_identity:supporting_signals:dup" in packet["invalid_independence_claims"]


def test_duplicate_identity_same_lineage_counts_once():
    row = signal("dup", "root-a", "dep-a", "ind-a")
    packet = build_composite_packet({
        "packet_family": "progression",
        "claim_ceiling": "composite_candidate_only",
        "input_windows": ["w1"],
        "supporting_signals": [row, dict(row)],
    })
    assert packet["decision"] == "READY_FOR_FUSION_CONSUMER"
    assert packet["independent_support_count"] == 1
    fused = fuse_packet(packet)
    assert fused["decision"] == "READY_FOR_ARGUMENT_SUPPORT"
    assert fused["independent_support_count"] == 1
