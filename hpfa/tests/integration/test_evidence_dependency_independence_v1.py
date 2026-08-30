import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULES = ROOT / "hpfa" / "modules" / "core"
PACKET_SRC = MODULES / "composite_evidence_packet_builder_lite" / "src"
FUSION_SRC = MODULES / "multi_signal_evidence_fusion_lite" / "src"
for src in [str(FUSION_SRC), str(PACKET_SRC)]:
    if src not in sys.path:
        sys.path.insert(0, src)

from composite_evidence_packet_builder import build_composite_packet, build_report as build_packet_report
from multi_signal_evidence_fusion import build_fusion_report, fuse_packet


def independent_signal(signal_id, provenance_root, dependency_group, independence_group):
    return {
        "signal_id": signal_id,
        "source_surface": f"surface_{signal_id}",
        "provenance_root": provenance_root,
        "dependency_group": dependency_group,
        "independence_group": independence_group,
        "independent_support_vote": True,
    }


def candidate_with_supports(supporting_signals):
    return {
        "packet_family": "progression",
        "input_features": [
            {"feature_id": "feature_generic_001", "source_surface": "feature_surface"},
        ],
        "input_windows": [
            {"window_id": "window_generic_001", "source_surface": "window_surface"},
        ],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": supporting_signals,
        "contradicting_signals": [],
        "claim_ceiling": "composite_candidate_only",
    }


def minimal_candidate(supporting_signals):
    return {
        "packet_family": "progression",
        "input_features": [],
        "input_windows": [],
        "input_sequences": [],
        "input_metrics": [],
        "supporting_signals": supporting_signals,
        "contradicting_signals": [],
        "claim_ceiling": "composite_candidate_only",
    }


def test_nominal_volume_does_not_become_independent_support_downstream():
    candidate = candidate_with_supports(
        [
            {"signal_id": "support_a", "source_surface": "surface_a"},
            {"signal_id": "support_b", "source_surface": "surface_b"},
        ]
    )
    packet = build_composite_packet(candidate)
    fusion = fuse_packet(packet)

    assert packet["status"] == "SMOKE_PASS"
    assert packet["nominal_ref_count"] >= 4
    assert packet["independent_support_count"] == 0
    assert packet["nominal_ref_count_is_independent_support_count"] is False
    assert fusion["decision"] != "BLOCK_FUSION"
    assert fusion["independent_support_count"] == 0
    assert fusion["nominal_ref_count_is_independent_support_count"] is False
    assert fusion["evidence_strength_is_probability"] is False


def test_same_provenance_root_collapses_before_fusion():
    candidate = candidate_with_supports(
        [
            independent_signal("support_a", "same_upstream_fact", "same_dependency", "presentation_a"),
            independent_signal("support_b", "same_upstream_fact", "same_dependency", "presentation_b"),
        ]
    )
    packet = build_composite_packet(candidate)
    fusion = fuse_packet(packet)

    assert packet["independent_support_count"] == 1
    assert fusion["independent_support_count"] == 1
    support_rows = [row for row in fusion["relation_records"] if row["relation_type"] == "SUPPORTS"]
    assert len(support_rows) == 2
    assert {row.get("provenance_root") for row in support_rows} == {"same_upstream_fact"}


def test_same_dependency_group_collapses_distinct_roots():
    packet = build_composite_packet(
        minimal_candidate(
            [
                independent_signal("support_a", "root_a", "shared_dependency", "ind_a"),
                independent_signal("support_b", "root_b", "shared_dependency", "ind_b"),
            ]
        )
    )
    fusion = fuse_packet(packet)

    assert packet["independent_support_count"] == 1
    assert packet["independent_support_count_basis"] == "connected_components_shared_provenance_root_or_dependency_group_or_independence_group"
    assert fusion["independent_support_count"] == 1


def test_same_independence_group_collapses_distinct_roots_and_dependencies():
    packet = build_composite_packet(
        minimal_candidate(
            [
                independent_signal("support_a", "root_a", "dep_a", "shared_independence"),
                independent_signal("support_b", "root_b", "dep_b", "shared_independence"),
            ]
        )
    )
    fusion = fuse_packet(packet)

    assert packet["independent_support_count"] == 1
    assert packet["evidence_strength"] == "medium"
    assert fusion["independent_support_count"] == 1
    assert fusion["decision"] == "READY_FOR_ARGUMENT_SUPPORT"


def test_incomplete_independence_claim_fails_closed_before_argument_chain():
    candidate = candidate_with_supports(
        [
            {
                "signal_id": "support_unproven",
                "source_surface": "surface_a",
                "provenance_root": "root_a",
                "independent_support_vote": True,
            }
        ]
    )
    packet = build_composite_packet(candidate)
    fusion = fuse_packet(packet)

    assert packet["status"] == "FAIL_CLOSED"
    assert "independent_support_claim_not_proven" in packet["hard_block_hits"]
    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_packet_failed_closed" in fusion["hard_block_hits"]


def test_fusion_rejects_nominal_ref_promotion_even_if_packet_is_forged():
    packet = build_composite_packet(
        candidate_with_supports(
            [
                independent_signal("support_a", "root_a", "dep_a", "ind_a"),
            ]
        )
    )
    packet["nominal_ref_count_is_independent_support_count"] = True
    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_nominal_ref_promoted_to_independent_support" in fusion["hard_block_hits"]


def test_fusion_recomputes_support_count_from_ledger_and_rejects_forged_aggregate():
    packet = build_composite_packet(
        minimal_candidate(
            [
                independent_signal("support_a", "root_a", "dep_a", "ind_a"),
                independent_signal("support_b", "root_b", "dep_b", "ind_b"),
            ]
        )
    )
    packet["independent_support_count"] = 999
    packet["independence_state"] = "INDEPENDENCE_ADMITTED"
    packet["dependency_ledger"] = []

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert fusion["independent_support_count"] == 0
    assert "upstream_independent_support_count_mismatch" in fusion["hard_block_hits"]
    assert "upstream_dependency_ledger_evidence_ref_binding_mismatch" in fusion["hard_block_hits"]


def test_fusion_rejects_invented_ledger_refs_not_present_in_packet_evidence():
    packet = build_composite_packet(
        minimal_candidate(
            [
                independent_signal("real_a", "root_a", "dep_a", "ind_a"),
                independent_signal("real_b", "root_b", "dep_b", "ind_b"),
            ]
        )
    )
    forged = []
    for idx, row in enumerate(packet["dependency_ledger"]):
        forged_row = dict(row)
        if forged_row["group_name"] == "supporting_signals":
            forged_row["ref_id"] = f"invented_{idx}"
        forged.append(forged_row)
    packet["dependency_ledger"] = forged

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert "upstream_dependency_ledger_evidence_ref_binding_mismatch" in fusion["hard_block_hits"]


def test_fusion_rejects_ledger_lineage_mismatch_for_preserved_signal_record():
    packet = build_composite_packet(
        minimal_candidate(
            [
                independent_signal("support_a", "root_a", "dep_a", "ind_a"),
                independent_signal("support_b", "root_b", "dep_b", "ind_b"),
            ]
        )
    )
    forged = [dict(row) for row in packet["dependency_ledger"]]
    support_row = next(row for row in forged if row["group_name"] == "supporting_signals")
    support_row["provenance_root"] = "forged_root"
    packet["dependency_ledger"] = forged

    fusion = fuse_packet(packet)

    assert fusion["decision"] == "BLOCK_FUSION"
    assert any(
        hit.startswith("upstream_dependency_ledger_lineage_binding_mismatch:supporting_signals:")
        for hit in fusion["hard_block_hits"]
    )


def test_duplicate_same_root_refs_cannot_raise_evidence_strength():
    two_units = minimal_candidate(
        [
            independent_signal("support_a", "root_a", "dep_a", "ind_a"),
            independent_signal("support_b", "root_b", "dep_b", "ind_b"),
        ]
    )
    duplicated_presentations = minimal_candidate(
        [
            independent_signal("support_a", "root_a", "dep_a", "ind_a"),
            independent_signal("support_b", "root_b", "dep_b", "ind_b"),
            independent_signal("support_a_mirror", "root_a", "dep_a", "ind_a_mirror"),
            independent_signal("support_b_mirror", "root_b", "dep_b", "ind_b_mirror"),
        ]
    )

    packet_two = build_composite_packet(two_units)
    packet_four_nominal = build_composite_packet(duplicated_presentations)

    assert packet_two["independent_support_count"] == 2
    assert packet_four_nominal["independent_support_count"] == 2
    assert packet_two["evidence_strength"] == packet_four_nominal["evidence_strength"]
    assert packet_two["evidence_strength"] == "strong"


def test_report_scope_deduplicates_same_support_root_across_packets():
    candidate_a = minimal_candidate(
        [
            independent_signal("support_a", "same_root", "same_dependency", "ind_a"),
            {"signal_id": "context_a"},
        ]
    )
    candidate_b = minimal_candidate(
        [
            independent_signal("support_b", "same_root", "same_dependency", "ind_b"),
            {"signal_id": "context_b"},
        ]
    )
    packet_a = build_composite_packet(candidate_a)
    packet_b = build_composite_packet(candidate_b)

    packet_report = build_packet_report([candidate_a, candidate_b])
    fusion_report = build_fusion_report([packet_a, packet_b])

    assert packet_report["independent_support_count_total"] == 1
    assert packet_report["independent_support_provenance_roots_total"] == ["same_root"]
    assert packet_report["independent_support_count_total_is_deduplicated"] is True
    assert fusion_report["independent_support_count_total"] == 1
    assert fusion_report["independent_support_provenance_roots_total"] == ["same_root"]
    assert fusion_report["independent_support_count_total_is_deduplicated"] is True


def test_report_scope_deduplicates_same_independence_group_across_packets():
    candidate_a = minimal_candidate(
        [
            independent_signal("support_a", "root_a", "dep_a", "shared_ind"),
            {"signal_id": "context_a"},
        ]
    )
    candidate_b = minimal_candidate(
        [
            independent_signal("support_b", "root_b", "dep_b", "shared_ind"),
            {"signal_id": "context_b"},
        ]
    )
    packet_a = build_composite_packet(candidate_a)
    packet_b = build_composite_packet(candidate_b)

    packet_report = build_packet_report([candidate_a, candidate_b])
    fusion_report = build_fusion_report([packet_a, packet_b])

    assert packet_report["independent_support_count_total"] == 1
    assert fusion_report["independent_support_count_total"] == 1


def test_no_sample_match_identity_leak():
    for path in [
        PACKET_SRC / "composite_evidence_packet_builder.py",
        FUSION_SRC / "multi_signal_evidence_fusion.py",
    ]:
        source = path.read_text(encoding="utf-8")
        for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "World Cup", "13.06.2026"]:
            assert token not in source, f"{token} leaked in {path}"
