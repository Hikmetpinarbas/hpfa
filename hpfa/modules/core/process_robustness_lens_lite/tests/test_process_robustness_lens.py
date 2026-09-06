from pathlib import Path

from hpfa.modules.core.process_robustness_lens_lite.src.process_robustness_lens import (
    build_process_robustness_lens,
    write_outputs,
)


def _chain(chain_id, a_ep, r_ep, a_team="ta", r_team="tb", traces=None):
    return {
        "reciprocal_process_chain_candidate_id": chain_id,
        "anchor_episode_candidate_id": a_ep,
        "response_episode_candidate_id": r_ep,
        "counter_response_visible": False,
        "anchor_team_identity_candidate_id": a_team,
        "response_team_identity_candidate_id": r_team,
        "supporting_trackable_action_trace_candidate_ids": traces or [],
    }


def _inputs(single_scope=False):
    scopes = [("e1", "e2"), ("e1", "e2")] if single_scope else [("e1", "e2"), ("e3", "e4"), ("e5", "e6")]
    chains = [
        _chain(f"c{i}", a, r, a_team="ta" if i % 2 == 0 else "tb", r_team="tb" if i % 2 == 0 else "ta", traces=[f"t{i}", "shared"])
        for i, (a, r) in enumerate(scopes)
    ]
    profile = {
        "process_variant_profile_candidate_id": "p1",
        "process_family_signature_candidate": {"anchor_action_families": ["PASS"], "response_action_families": ["PASS", "TURNOVER"]},
        "reciprocal_process_chain_candidate_ids": [row["reciprocal_process_chain_candidate_id"] for row in chains],
        "visible_outcome_profile_candidate": [
            {"visible_outcome_signature_candidate": {"x": 1}, "chain_count_candidate": max(1, len(chains) - 1)},
            {"visible_outcome_signature_candidate": {"x": 2}, "chain_count_candidate": 1},
        ] if len(chains) > 1 else [{"visible_outcome_signature_candidate": {"x": 1}, "chain_count_candidate": 1}],
    }
    reciprocal = {
        "module_id": "reciprocal_process_chain_lite_v1",
        "status": "PASS",
        "reciprocal_process_chain_candidates": chains,
        "process_variant_profiles": [profile],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    edges = []
    for i, chain in enumerate(chains):
        chain_id = chain["reciprocal_process_chain_candidate_id"]
        edges.append({
            "reciprocal_process_chain_candidate_id": chain_id,
            "roles": {
                "anchor": {"actor_identity_candidate_ids": ["p_common", f"p{i}"]},
                "response": {"actor_identity_candidate_ids": [f"q{i}"]},
            },
        })
    reconciliation = {
        "module_id": "match_reconciliation_ledger_lite_v2",
        "status": "PASS",
        "reciprocal_consistency_edges": edges,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
    }
    return reciprocal, reconciliation


def test_multi_episode_repeat_surfaces_robustness_components():
    result = build_process_robustness_lens(*_inputs())
    assert result["status"] == "PASS"
    row = result["process_robustness_rows"][0]
    assert row["visible_repeat_count_candidate"] == 3
    assert row["unique_episode_scope_count_candidate"] == 3
    assert row["segment_only_falsifier_state_candidate"] == "NOT_SINGLE_EPISODE_ONLY_VISIBLE"
    assert row["opponent_symmetry_falsifier_state_candidate"] == "VISIBLE_BOTH_ANCHOR_SIDES"
    assert row["max_anchor_actor_chain_presence_share_candidate"] == 1.0
    assert row["trace_membership_uniqueness_ratio_candidate"] < 1.0
    assert row["recurrence_surface_robustness_composite_candidate"] is not None
    assert row["recurrence_surface_robustness_is_pattern_truth"] is False


def test_single_episode_repeat_surfaces_segment_only_risk():
    result = build_process_robustness_lens(*_inputs(single_scope=True))
    row = result["process_robustness_rows"][0]
    assert row["segment_only_falsifier_state_candidate"] == "SEGMENT_ONLY_RISK_PRESENT"
    assert row["segment_concentration_share_candidate"] == 1.0
    assert row["leave_one_episode_scope_out_repeat_survives_candidate"] is False


def test_upstream_review_is_inherited():
    reciprocal, reconciliation = _inputs()
    reciprocal["status"] = "REVIEW_REQUIRED"
    result = build_process_robustness_lens(reciprocal, reconciliation)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "reciprocal_upstream_review_required" in result["review_hits"]


def test_output_claim_locks(tmp_path: Path):
    result = build_process_robustness_lens(*_inputs())
    paths = write_outputs(result, tmp_path)
    text = paths["summary"].read_text(encoding="utf-8")
    assert "composite_metric_is_calibrated=false" in text
    assert "stable_pattern_truth=false" in text
    assert "production_release=false" in text


def test_no_sample_match_identity_leak():
    root = Path(__file__).resolve().parents[1] / "src"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).casefold()
    forbidden = ("genclerbirligi", "fenerbahce", "15.08.2026", "samsunspor", "galatasaray", "besiktas")
    assert not any(token in text for token in forbidden)
