from __future__ import annotations

import argparse
import json
from pathlib import Path

import match_local_identity_candidates_lite as current_identity
from hpfa.modules.core.semantic_role_action_bundle_candidates_lite.src import (
    semantic_role_action_bundle_candidates as semantic,
)


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = semantic.validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    identity_payload = current_identity.runtime_write_outputs(input_dir, output)
    evidence_path = output / "evidence_atom_inventory_lite_v1.json"
    identity_path = output / "match_local_identity_candidates_lite_v1.json"

    if identity_payload.get("status") == "FAIL_CLOSED":
        return {
            "module_id": semantic.MODULE_ID,
            "status": "FAIL_CLOSED",
            "module_status": "FAIL_CLOSED",
            "runtime_evidence_status": "NOT_EVALUATED",
            "release_status": "NOT_PRODUCTION",
            "match_surface_binding_id": identity_payload.get("match_surface_binding_id"),
            "semantic_route_records": [],
            "semantic_route_record_count": 0,
            "semantic_route_review_required_count": 0,
            "semantic_route_blocked_action_anchor_count": 0,
            "action_bundle_candidates": [],
            "action_bundle_candidate_count": 0,
            "action_bundle_pass_count": 0,
            "action_bundle_review_required_count": 0,
            "cross_role_relation_candidates": [],
            "cross_role_relation_candidate_count": 0,
            "hard_block_hits": ["current_match_local_identity_fail_closed"],
            "review_hits": [],
            "active_match_evidence_pass": False,
            "action_bundle_is_canonical_event": False,
            "validated_event_identity": False,
            "physical_action_identity_truth": False,
            "base_event_admission_allowed": False,
            "event_instance_count": 0,
            "cross_role_fusion_allowed": False,
            "independent_source_vote_allowed": False,
            "comparison_allowed": False,
            "claim_allowed": False,
            "sequence_truth": False,
            "possession_truth": False,
            "phase_truth": False,
            "tactical_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": semantic.CLAIM_CEILING,
            "current_identity_status": identity_payload.get("status"),
        }

    result = semantic.write_outputs(evidence_path, identity_path, output)
    result["current_identity_status"] = identity_payload.get("status")
    result["current_identity_binding_record_count"] = identity_payload.get("identity_binding_record_count")
    result["current_identity_review_required_atom_count"] = identity_payload.get("identity_review_required_atom_count")
    result["current_evidence_atom_status"] = identity_payload.get("current_evidence_atom_status")
    result["current_content_source_role_bridge_status"] = identity_payload.get(
        "current_content_source_role_bridge_status"
    )
    result["active_match_evidence_pass"] = False

    (output / semantic.OUTPUTS["json"]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current Evidence Atom + Match-Local Identity to Semantic Role / Action Bundle migration"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "current_identity_status": payload.get("current_identity_status"),
                "semantic_route_record_count": payload.get("semantic_route_record_count"),
                "semantic_route_review_required_count": payload.get("semantic_route_review_required_count"),
                "semantic_route_blocked_action_anchor_count": payload.get("semantic_route_blocked_action_anchor_count"),
                "action_bundle_candidate_count": payload.get("action_bundle_candidate_count"),
                "action_bundle_pass_count": payload.get("action_bundle_pass_count"),
                "action_bundle_review_required_count": payload.get("action_bundle_review_required_count"),
                "cross_role_relation_candidate_count": payload.get("cross_role_relation_candidate_count"),
                "hard_block_hits": payload.get("hard_block_hits") or [],
                "review_hits": payload.get("review_hits") or [],
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
